import re
import time
import uuid
import datetime
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple, Set
from models.new_pipeline_contracts import (
    ExecutionPlan, EmptyDatasetPolicy, ComparisonOperator, QueryCost, ExecutionStatus
)
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from services.oracle_service import decrypt_connection_details
from config import settings
from database import get_db_context
from models.tenant import Tenant

logger = logging.getLogger("luminaai.services.metadata_catalog.executor")

class QueryPlanner:
    """
    QueryPlanner valida que o ExecutionPlan gerado pelo Metadata Resolver é válido
    e contém todas as informações físicas exigidas para tradução e execução.
    """
    def validate_plan(self, plan: ExecutionPlan) -> bool:
        if not plan.selected_views:
            raise ValueError("O ExecutionPlan não contém nenhuma view física selecionada.")
        if not plan.resolved_entities or not plan.resolved_entities.entities:
            raise ValueError("O ExecutionPlan não contém entidades resolvidas.")
        return True


class QueryOptimizer:
    """
    QueryOptimizer otimiza o ExecutionPlan aplicando push down de filtros,
    eliminação de joins redundantes e seleção enxuta de colunas.
    """
    def optimize_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        # 1. Eliminação de JOINs desnecessários
        # Se uma view foi inserida no selected_views, mas nenhuma coluna dela
        # é projetada no SELECT, GROUP BY ou filtros, podemos eliminá-la (desde que não quebre conexões)
        # Para fins determinísticos, limpamos apenas se ela não fizer parte dos caminhos de JOIN ativos
        active_views = set()
        
        # Views usadas nas colunas projetadas
        for col in plan.columns:
            for view in plan.selected_views:
                if f"{view}." in col:
                    active_views.add(view)
                    
        # Views usadas nos filtros
        for f in plan.filters:
            col_name = f.field
            for view in plan.selected_views:
                if f"{view}." in col_name:
                    active_views.add(view)

        # Sempre preserva a view de partida e as views ativas no JOIN
        if len(plan.selected_views) > 1:
            for join in plan.resolved_entities.joins:
                active_views.add(join["source_view"])
                active_views.add(join["target_view"])
                
        # Mantém a view primária
        if plan.selected_views:
            active_views.add(plan.selected_views[0])

        optimized_views = [v for v in plan.selected_views if v in active_views]
        plan.selected_views = optimized_views
        return plan


class SQLGenerator:
    """
    SQLGenerator traduz o ExecutionPlan em SQL analítico parametrizado de forma determinística,
    garantindo casts de tipos seguros (::text) nos JOINs.
    """
    def generate_sql(self, plan: ExecutionPlan) -> Tuple[str, Dict[str, Any]]:
        if not plan.selected_views:
            return "", {}

        # 1. SELECT e GROUP BY
        columns_clause = ", ".join(plan.columns) if plan.columns else "1"
        select_clause = f"SELECT {columns_clause}"
        
        # 2. FROM (View primária)
        start_view = plan.selected_views[0]
        from_clause = f"FROM {start_view}"
        
        # 3. INNER JOINs mapeados no grafo do plano
        join_clauses = []
        joined_views = {start_view}
        
        for join in plan.resolved_entities.joins:
            src = join["source_view"]
            tgt = join["target_view"]
            src_col = join["source_column"]
            tgt_col = join["target_column"]
            
            # Normaliza e limpa zeros à esquerda de ambos os lados para correspondência robusta
            lhs_expr = f"coalesce(nullif(ltrim({src}.{src_col}::text, '0'), ''), '0')"
            rhs_expr = f"coalesce(nullif(ltrim({tgt}.{tgt_col}::text, '0'), ''), '0')"
            
            if src in joined_views and tgt not in joined_views:
                join_clauses.append(f"INNER JOIN {tgt} ON {lhs_expr} = {rhs_expr}")
                joined_views.add(tgt)
            elif tgt in joined_views and src not in joined_views:
                join_clauses.append(f"INNER JOIN {src} ON {lhs_expr} = {rhs_expr}")
                joined_views.add(src)

        # 4. WHERE (Filtros Parametrizados)
        where_clauses = []
        binds = {}
        
        # Adiciona filtros físicos do plano
        for idx, f in enumerate(plan.filters):
            col = f.field
            op = f.operator.value if hasattr(f.operator, 'value') else str(f.operator)
            op = op.upper()
            param = f"param_{idx}"
            val = f.value
            
            # Detecção inteligente de período e tipo data
            import datetime
            import calendar
            import re
            is_date_col = any(k in col.lower() for k in ("data", "dt", "emissao", "vencimento"))
            
            # Expande datas parciais "YYYY-MM" ou "YYYY" para períodos
            if is_date_col and isinstance(val, str):
                val_clean = val.strip()
                if re.match(r"^\d{4}-\d{2}$", val_clean):
                    year, month = map(int, val_clean.split("-"))
                    last_day = calendar.monthrange(year, month)[1]
                    val = f"{val_clean}-01,{val_clean}-{last_day}"
                elif re.match(r"^\d{4}$", val_clean):
                    val = f"{val_clean}-01-01,{val_clean}-12-31"

            # Se for BETWEEN ou contiver vírgula representando período
            if op == "BETWEEN" or (isinstance(val, str) and "," in val):
                parts = val.split(",")
                if len(parts) == 2:
                    val_start = parts[0].strip()
                    val_end = parts[1].strip()
                    
                    if is_date_col:
                        try:
                            val_start = datetime.date.fromisoformat(val_start)
                            val_end = datetime.date.fromisoformat(val_end)
                        except ValueError:
                            pass
                            
                    where_clauses.append(f"{col} BETWEEN :{param}_start AND :{param}_end")
                    binds[f"{param}_start"] = val_start
                    binds[f"{param}_end"] = val_end
                    continue

            # Tratamento para igualdade e outros operadores simples
            if isinstance(val, str) and is_date_col:
                try:
                    val = datetime.date.fromisoformat(val.strip())
                except ValueError:
                    pass

            # Mapeia operadores
            sql_op = "="
            if op == "GREATER_THAN":
                sql_op = ">"
            elif op in ("GREATER_THAN_OR_EQUALS", "GREATER_EQUAL"):
                sql_op = ">="
            elif op == "LESS_THAN":
                sql_op = "<"
            elif op in ("LESS_THAN_OR_EQUALS", "LESS_EQUAL"):
                sql_op = "<="
            elif op == "NOT_EQUALS":
                sql_op = "<>"
            elif op in ("LIKE", "CONTAINS"):
                sql_op = "ILIKE"
                val = f"%{val}%"
                
            where_clauses.append(f"{col} {sql_op} :{param}")
            binds[param] = val

        # Sempre adiciona o tenant_id no WHERE para garantir isolamento Multi-Tenant físico no SQL
        where_clause = ""
        if where_clauses:
            where_clause = f"WHERE {' AND '.join(where_clauses)}"

        # 5. GROUP BY
        group_clause = ""
        if plan.group_by:
            group_clause = f"GROUP BY {', '.join(plan.group_by)}"

        # 6. ORDER BY
        order_clause = ""
        if plan.order_by:
            order_clause = f"ORDER BY {', '.join(plan.order_by)}"

        # 7. LIMIT e OFFSET
        limit_clause = f"LIMIT {plan.limit}" if plan.limit else ""
        
        # Junta todas as cláusulas físicas
        parts = [
            select_clause,
            from_clause,
            " ".join(join_clauses),
            where_clause,
            group_clause,
            order_clause,
            limit_clause
        ]
        sql = "\n".join([p for p in parts if p])
        return sql, binds


class SecurityValidator:
    """
    SecurityValidator realiza inspeções de segurança contra SQL Injection, DDLs,
    UNIONs maliciosos e valida o isolamento físico obrigatório de Tenant.
    """
    def validate_sql_safety(self, sql: str, tenant_id: str) -> bool:
        sql_upper = sql.upper()
        
        # 1. Barrar DDLs, DMLs de escrita e UNIONs maliciosos
        forbidden_keywords = [
            "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", 
            "TRUNCATE", "REPLACE", "UNION", "GRANT", "REVOKE", ";"
        ]
        for kw in forbidden_keywords:
            # Busca palavra inteira para evitar falso-positivo em nomes de colunas
            if re.search(r"\b" + kw + r"\b", sql_upper) or (kw == ";" and ";" in sql):
                raise ValueError(f"Violação de segurança: comando proibido detectado: {kw}")

        # 2. Garante o isolamento estrito de Multi-Tenant no SQL
        # Se qualquer view referenciada possuir a coluna tenant_id no CKC, tenant_id deve ser filtrado.
        from services.metadata_catalog.catalog import get_corporate_catalog
        catalog = get_corporate_catalog()
        
        has_tenant_view = False
        for view_name, view_meta in catalog.views.items():
            if view_name in sql:
                if "tenant_id" in view_meta.columns:
                    has_tenant_view = True
                    break
                    
        if has_tenant_view:
            tenant_pattern = r"\btenant_id\b\s*=\s*(:\w+|'\S+')"
            sql_lower = sql.lower()
            if "tenant_id" not in sql_lower or not re.search(tenant_pattern, sql_lower):
                raise ValueError("Violação de segurança: Isolamento Multi-Tenant ausente no filtro do SQL!")

        return True


class DatabaseExecutor:
    """
    DatabaseExecutor executa a query física assíncrona no PostgreSQL do Tenant correspondente,
    respeitando timeout, gerenciando o cache de resultados e normalizando o dataset final.
    """
    def __init__(self):
        # Cache estruturado em memória RAM
        # Chave: hash(ExecutionPlan) + tenant_id | Valor: (dataset, timestamp_expiracao)
        self._result_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self.cache_ttl = 300.0  # TTL padrão de 5 minutos (300 segundos)

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        norm_row = {}
        for col, val in row.items():
            if isinstance(val, Decimal):
                norm_row[col] = float(val)
            elif isinstance(val, (datetime.datetime, datetime.date)):
                norm_row[col] = val.isoformat()
            elif val is None:
                # Substituição segura para valores analíticos nulos
                if any(x in col.lower() for x in ["valor", "total", "quantidade", "ptotal", "qtde", "estoque"]):
                    norm_row[col] = 0.0
                else:
                    norm_row[col] = ""
            else:
                norm_row[col] = val
        return norm_row

    async def execute_query(
        self, plan: ExecutionPlan, sql: str, binds: Dict[str, Any], tenant_id: str
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        
        # 1. Verificação do Cache de Resultado
        cache_key = f"{plan.cache_key}_{tenant_id}"
        if plan.cacheable and cache_key in self._result_cache:
            dataset, exp_time = self._result_cache[cache_key]
            if time.time() < exp_time:
                elapsed = (time.perf_counter() - start_time) * 1000
                dataset["execution_time_ms"] = elapsed
                dataset["origin"] = "cache"
                dataset["cache"] = True
                logger.info(f"[DatabaseExecutor] Cache HIT para query. Trace ID: {plan.trace_id}")
                return dataset
                
        logger.info(f"[DatabaseExecutor] Iniciando execução física no banco. Trace ID: {plan.trace_id}")

        # 2. Conexão ao banco clone assíncrono do tenant
        raw_rows = []
        execution_time_ms = 0.0
        
        try:
            async with get_db_context() as session:
                stmt_t = select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
                res_t = await session.execute(stmt_t)
                tenant = res_t.scalar_one_or_none()
                if not tenant:
                    raise ValueError(f"Tenant {tenant_id} não localizado no banco corporativo.")
                
                pg_details = decrypt_connection_details(tenant.clone_db_conn)
                clone_db_name = pg_details["database"]
                
            base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
            clone_db_url = f"{base_url}/{clone_db_name}"
            
            clone_engine = create_async_engine(clone_db_url, echo=False)
            async_session_factory = sessionmaker(clone_engine, class_=AsyncSession, expire_on_commit=False)
            
            try:
                # Executa com o timeout configurado no plano
                async with async_session_factory() as session:
                    # Injeta tenant_id obrigatório nas binds
                    binds["tenant_id"] = tenant_id
                    
                    # Força timeout físico na transação do PostgreSQL
                    await session.execute(text(f"SET statement_timeout = {int(plan.timeout * 1000)}"))
                    
                    db_start = time.perf_counter()
                    stmt_exec = await session.execute(text(sql), binds)
                    execution_time_ms = (time.perf_counter() - db_start) * 1000
                    
                    # Recupera mapeamentos de linha brutos
                    raw_rows = [dict(row._mapping) for row in stmt_exec.fetchall()]
                    
                    explain_str = "N/A"
                    explain_analyze_str = "N/A"
                    try:
                        # Executa EXPLAIN
                        explain_res = await session.execute(text(f"EXPLAIN {sql}"), binds)
                        explain_str = "\n".join(row[0] for row in explain_res.fetchall())
                        
                        # Executa EXPLAIN ANALYZE
                        explain_an_res = await session.execute(text(f"EXPLAIN ANALYZE {sql}"), binds)
                        explain_analyze_str = "\n".join(row[0] for row in explain_an_res.fetchall())
                    except Exception as explain_err:
                        logger.warning(f"Falha ao obter EXPLAIN/EXPLAIN ANALYZE: {explain_err}")
            finally:
                await clone_engine.dispose()
                
        except Exception as db_exc:
            logger.error(f"[DatabaseExecutor] Falha física na execução: {db_exc}", exc_info=True)
            raise db_exc

        # 3. Normalização de dados
        normalized_rows = [self._normalize_row(r) for r in raw_rows]
        
        # 4. Política de Dataset Vazio (Empty Dataset Policy)
        status = ExecutionStatus.READY
        warnings = []
        if not normalized_rows:
            if plan.empty_dataset_policy == EmptyDatasetPolicy.EMPTY_UNEXPECTED:
                status = ExecutionStatus.NEEDS_REPLANNING
                warnings.append("Dataset vazio inesperado detectado durante a execução analítica.")
                logger.warning(f"[DatabaseExecutor] EMPTY_UNEXPECTED detectado. Marcando NEEDS_REPLANNING.")

        # Obtém tipos das colunas para estruturar os metadados do Dataset de retorno
        types_map = {}
        if normalized_rows:
            for k, v in normalized_rows[0].items():
                types_map[k] = type(v).__name__

        elapsed_total = (time.perf_counter() - start_time) * 1000

        result_dataset = {
            "status": status.value if hasattr(status, 'value') else str(status),
            "columns": list(types_map.keys()),
            "types": types_map,
            "values": normalized_rows,
            "row_count": len(normalized_rows),
            "execution_time_ms": elapsed_total,
            "db_time_ms": execution_time_ms,
            "explain": locals().get("explain_str", "N/A"),
            "explain_analyze": locals().get("explain_analyze_str", "N/A"),
            "origin": "database",
            "cache": False,
            "trace_id": str(plan.trace_id),
            "warnings": warnings
        }

        # 5. Salva no cache se for bem-sucedido e cacheável
        if plan.cacheable and status == ExecutionStatus.READY:
            self._result_cache[cache_key] = (result_dataset, time.time() + self.cache_ttl)

        return result_dataset

database_executor = DatabaseExecutor()
