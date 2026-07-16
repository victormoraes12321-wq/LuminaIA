"""
LuminaAI — Gerenciador de Conexão e Execução no Oracle Database
------------------------------------------------------------
Este módulo é responsável por:
1. Descriptografar as credenciais do banco Oracle de produção (armazenadas
   criptografadas na base PostgreSQL) usando criptografia Fernet (AES-128).
2. Estabelecer conexões assíncronas no modo "Thin" da biblioteca python-oracledb
   (um modo nativo em Python puro que dispensa a instalação de drivers proprietários
   Oracle Instant Client).
3. Coletar metadados e colunas das views do Oracle em tempo real de forma segura.
4. Executar as views no Oracle aplicando filtros dinâmicos de forma segura contra
   SQL Injection através do uso obrigatório de Bind Variables (parâmetros nomeados).
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import re
from typing import Any
import uuid

import oracledb
from cryptography.fernet import Fernet

from config import settings

# Inicialização do logger específico deste serviço
logger = logging.getLogger("luminaai.services.oracle")


def _safe_oracle_identifier(view_name: str) -> str:
    """Valida VIEW ou OWNER.VIEW para montagem segura de SQL Oracle."""
    raw = str(view_name or "").strip().upper()
    parts = raw.split(".")
    if len(parts) not in (1, 2):
        raise ValueError(f"Nome de view invÃ¡lido ou suspeito detectado: '{view_name}'")
    for part in parts:
        if not part or not all(c.isalnum() or c in "_$#" for c in part):
            raise ValueError(f"Nome de view invÃ¡lido ou suspeito detectado: '{view_name}'")
    return ".".join(parts)


async def _close_oracle_resource(resource: Any) -> None:
    """Close Oracle resources safely across async and thin/sync driver modes."""
    if not resource:
        return
    result = resource.close()
    if inspect.isawaitable(result):
        await result


class OracleConnectionValidationError(ConnectionError):
    """Safe, user-facing Oracle connectivity error."""

    def __init__(
        self,
        code: str,
        user_message: str,
        technical_detail: str | None = None,
    ) -> None:
        self.code = code
        self.user_message = user_message
        self.technical_detail = technical_detail or user_message
        super().__init__(user_message)


async def validate_oracle_listener(host: str, port: int, timeout_seconds: float = 5.0) -> None:
    """
    Performs a short TCP preflight before invoking the Oracle driver.

    This keeps the admin screen from showing a generic Oracle error when the
    machine cannot even reach the database listener.
    """
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(str(host), int(port)),
            timeout=timeout_seconds,
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
    except TimeoutError as exc:
        raise OracleConnectionValidationError(
            "ORACLE_TCP_TIMEOUT",
            (
                "O servidor Oracle nao respondeu na porta informada. "
                "Verifique VPN/rede, firewall, listener Oracle e se o host/porta estao acessiveis a partir desta maquina."
            ),
            "TCP timeout while connecting to Oracle listener.",
        ) from exc
    except OSError as exc:
        raise OracleConnectionValidationError(
            "ORACLE_TCP_UNREACHABLE",
            (
                "Nao foi possivel abrir conexao TCP com o Oracle. "
                "Verifique se o host, a porta, a rota de rede e o listener Oracle estao ativos."
            ),
            str(exc),
        ) from exc


def classify_oracle_connection_error(
    exc: Exception,
    *,
    sid: str | None = None,
    service_name: str | None = None,
) -> OracleConnectionValidationError:
    """Maps low-level Oracle/driver exceptions to safe admin messages."""
    error_text = str(exc)
    normalized = error_text.upper()

    if "ORA-01017" in normalized:
        return OracleConnectionValidationError(
            "ORACLE_INVALID_CREDENTIALS",
            "Usuario ou senha do Oracle invalidos. Verifique as credenciais e tente novamente.",
            error_text,
        )
    if "ORA-28000" in normalized:
        return OracleConnectionValidationError(
            "ORACLE_ACCOUNT_LOCKED",
            "A conta Oracle informada esta bloqueada. Solicite desbloqueio ao DBA.",
            error_text,
        )
    if "ORA-28001" in normalized:
        return OracleConnectionValidationError(
            "ORACLE_PASSWORD_EXPIRED",
            "A senha do usuario Oracle expirou. Atualize a senha no Oracle antes de conectar.",
            error_text,
        )
    if "ORA-12505" in normalized:
        return OracleConnectionValidationError(
            "ORACLE_UNKNOWN_SID",
            "O listener Oracle respondeu, mas nao reconheceu o SID informado. Confirme o SID com o DBA.",
            error_text,
        )
    if "ORA-12514" in normalized:
        return OracleConnectionValidationError(
            "ORACLE_UNKNOWN_SERVICE",
            "O listener Oracle respondeu, mas nao reconheceu o Service Name informado. Confirme o Service Name com o DBA.",
            error_text,
        )
    if "ORA-12154" in normalized:
        return OracleConnectionValidationError(
            "ORACLE_CONNECT_IDENTIFIER_ERROR",
            "O identificador de conexao Oracle nao foi resolvido. Use SID ou Service Name valido.",
            error_text,
        )
    if "ORA-12170" in normalized or "DPY-6005" in normalized or "TIMED OUT" in normalized:
        return OracleConnectionValidationError(
            "ORACLE_CONNECT_TIMEOUT",
            "A tentativa de conexao com o Oracle expirou. Verifique rede, VPN, firewall e listener.",
            error_text,
        )
    if sid and service_name:
        return OracleConnectionValidationError(
            "ORACLE_CONNECTION_IDENTIFIER_AMBIGUOUS",
            (
                "Nao foi possivel conectar ao Oracle. SID e Service Name estao preenchidos; "
                "valide com o DBA qual identificador deve ser usado e deixe o outro campo vazio."
            ),
            error_text,
        )
    return OracleConnectionValidationError(
        "ORACLE_CONNECTION_FAILED",
        (
            "Nao foi possivel conectar ao banco Oracle. "
            "Verifique host, porta, usuario, senha e identificador SID/Service Name."
        ),
        error_text,
    )


def decrypt_connection_details(oracle_conn: dict[str, Any]) -> dict[str, Any]:
    """
    Descriptografa as credenciais de conexão do banco Oracle de um Tenant específico.

    O JSON de conexão é armazenado de forma criptografada na tabela 'tenants' do PostgreSQL
    para garantir conformidade com políticas de segurança da informação. A chave simétrica
    utilizada é definida pela variável de ambiente 'ENCRYPTION_KEY' no formato base64 da Fernet.

    Parâmetros:
    -----------
    oracle_conn : dict[str, Any]
        Dicionário contendo as chaves de controle de criptografia do tenant:
        - encrypted (bool): Indica se o payload está cifrado.
        - algorithm (str): Nome do algoritmo utilizado (ex: 'Fernet').
        - payload (str | dict): Carga contendo os dados de conexão cifrados ou planos.

    Retorno:
    --------
    dict[str, Any]
        Dicionário contendo os parâmetros de conexão descriptografados em formato plano:
        host, port, user, password, sid ou service_name.

    Exceções:
    ---------
    ValueError:
        Caso as credenciais estejam ausentes, malformadas ou o decodificador falhe.
    """
    # Valida se o dicionário com os dados de conexão existe
    if not oracle_conn:
        raise ValueError("Dados de conexão do Oracle não fornecidos ou vazios.")

    if isinstance(oracle_conn, str):
        try:
            oracle_conn = json.loads(oracle_conn)
        except Exception:
            pass

    # Se a flag 'encrypted' estiver explicitamente falsa, lê o payload direto (útil para desenvolvimento local)
    if not oracle_conn.get("encrypted", True):
        logger.warning("Alerta de Segurança: Lendo credenciais em plaintext para fins de desenvolvimento.")
        payload_data = oracle_conn.get("payload")
        if isinstance(payload_data, dict):
            return payload_data
        elif isinstance(payload_data, str):
            # Tenta decodificar a string como um JSON estruturado
            return json.loads(payload_data)
        raise ValueError("Payload de conexão não criptografado inválido ou mal estruturado.")

    # Extrai o payload criptografado
    payload = oracle_conn.get("payload")
    if not payload:
        raise ValueError("Carga criptografada (payload) ausente nas credenciais do tenant.")

    try:
        # Prepara a chave simétrica Fernet a partir das configurações do backend
        key_bytes = settings.ENCRYPTION_KEY.encode("utf-8")
        f = Fernet(key_bytes)
        
        # Descriptografa a string criptografada e converte de bytes de volta para string UTF-8
        decrypted_bytes = f.decrypt(payload.encode("utf-8"))
        decrypted_str = decrypted_bytes.decode("utf-8")
        
        # Converte a string JSON plana em um dicionário Python
        details = json.loads(decrypted_str)
        return details
    except Exception as exc:
        logger.error("Falha crítica ao descriptografar credenciais do tenant: %s", exc)
        # Oculta detalhes do erro criptográfico e lança uma exceção limpa
        raise ValueError("Chave de criptografia inválida ou payload de conexão corrompido.") from exc


import asyncio
import re

# ── Classes de Simulação do Oracle Database (Mock) ─────────────

class MockOracleCursor:
    """Simula o cursor assíncrono do driver python-oracledb Thin."""
    def __init__(self, pg_conn):
        self.pg_conn = pg_conn
        self.description = []
        self.arraysize = 100
        self._rows = []
        self._index = 0

    async def execute(self, statement, parameters=None):
        stmt_lower = statement.lower()
        logger.debug("MockOracleCursor executando instrução: %r", statement)

        # Identifica a tabela de origem na consulta (ex: FROM VW_VENDAS_MENSAIS)
        match = re.search(r"from\s+([a-zA-Z0-9_]+)", stmt_lower)
        if match:
            extracted_view = match.group(1).lower()
            
            # De-para de views do catálogo para tabelas físicas do mock_oracle
            VIEW_TO_TABLE_MAP = {
                "vw_vendas_mensais": "mock_oracle_vw_vendas_mensais",
                "vw_faturamento_mensal": "mock_oracle_vw_faturamento_mensal",
                "vw_vendas_contexto_geral": "mock_oracle_vw_vendas_mensais",
                "vw_performance_vendedores": "mock_oracle_vw_performance_vendedores",
                "vw_metas_atingimento": "mock_oracle_vw_metas_vendedores",
                "vw_metas_vendedores": "mock_oracle_vw_metas_vendedores",
                "vw_clientes_historico": "mock_oracle_vw_historico_clientes",
                "vw_historico_clientes": "mock_oracle_vw_historico_clientes",
                "vw_produtos_mais_vendidos": "mock_oracle_vw_ranking_produtos",
                "vw_ranking_produtos": "mock_oracle_vw_ranking_produtos",
                "vw_estoque_status": "mock_oracle_vw_estoque_produtos",
                "vw_estoque_produtos": "mock_oracle_vw_estoque_produtos",
                "vw_kpi_executivo": "mock_oracle_vw_kpi_executivo",
                "vw_kpi_executivo_vendas": "mock_oracle_vw_kpi_executivo",
                "vw_lojas_regioes": "mock_oracle_vw_lojas_regioes",
                
                # Mapeamento do catálogo analítico de produção
                "vw_vendas_lm": "mock_oracle_vw_vendas_mensais",
                "vw_clientes_cad_lm": "mock_oracle_vw_historico_clientes",
                "vw_vendedor_cad_lm": "mock_oracle_vw_performance_vendedores",
                "vw_produtos_cad_lm": "mock_oracle_vw_estoque_produtos",
                "vw_fornecedor_cad_lm": "mock_oracle_vw_lojas_regioes",
                "vw_financeiro_lm": "mock_oracle_vw_faturamento_mensal",
            }
            
            target_table = VIEW_TO_TABLE_MAP.get(extracted_view, f"mock_oracle_{extracted_view}")
        else:
            target_table = "mock_oracle_vw_vendas_mensais"

        # Conecta no Postgres local para ler as colunas da tabela mock_oracle_
        columns_query = f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{target_table}'
            ORDER BY ordinal_position;
        """
        try:
            cols = await self.pg_conn.fetch(columns_query)
        except Exception as exc:
            logger.warning("Falha ao consultar information_schema para '%s': %s", target_table, exc)
            cols = []

        if not cols:
            logger.warning("Tabela simulada '%s' nao cadastrada localmente no Postgres. Retornando colunas dummy.", target_table)
            self.description = [
                ("STATUS_SIMULADO", oracledb.DB_TYPE_VARCHAR),
                ("MENSAGEM", oracledb.DB_TYPE_VARCHAR)
            ]
            self._rows = [
                ("AVISO", f"Dados de simulação para {target_table} não criados no banco local.")
            ]
            self._index = 0
            return

        self.description = []
        for c in cols:
            col_name = c["column_name"].upper()
            col_type = c["data_type"].lower()
            
            if "int" in col_type or "numeric" in col_type or "double" in col_type or "real" in col_type:
                oracle_type = oracledb.DB_TYPE_NUMBER
            elif "date" in col_type or "timestamp" in col_type:
                oracle_type = oracledb.DB_TYPE_DATE
            else:
                oracle_type = oracledb.DB_TYPE_VARCHAR
                
            self.description.append((col_name, oracle_type))

        # Se não for uma query de schema ( WHERE 1=0 )
        if "1=0" not in statement:
            rows_query = f"SELECT * FROM {target_table};"
            records = await self.pg_conn.fetch(rows_query)
            # Converte registros do asyncpg (Record) em tuplas simples
            self._rows = [tuple(r.values()) for r in records]
        else:
            self._rows = []

        self._index = 0

    async def fetchone(self):
        if self._index < len(self._rows):
            row = self._rows[self._index]
            self._index += 1
            return row
        return None

    async def fetchall(self):
        chunk = self._rows[self._index:]
        self._index = len(self._rows)
        return chunk

    async def fetchmany(self, size):
        end = min(self._index + size, len(self._rows))
        chunk = self._rows[self._index:end]
        self._index = end
        return chunk

    async def close(self):
        pass


class MockOracleConnection:
    """Simula a conexão assíncrona do driver python-oracledb Thin."""
    def __init__(self, pg_conn):
        self.pg_conn = pg_conn
        self.call_timeout = 60000

    def cursor(self):
        return MockOracleCursor(self.pg_conn)

    async def close(self):
        try:
            await self.pg_conn.close()
        except Exception:
            pass


# Global cache of active Oracle Connection Pools indexed by Tenant UUID
_oracle_pools: dict[str, Any] = {}
_pools_lock = asyncio.Lock()


async def close_oracle_pool(tenant_id: uuid.UUID | str) -> None:
    """
    Closes and removes the cached connection pool of a specific tenant.
    Should be called when database credentials/settings change.
    """
    global _oracle_pools
    tenant_key = str(tenant_id)
    async with _pools_lock:
        if tenant_key in _oracle_pools:
            pool = _oracle_pools[tenant_key]
            if pool == "MOCK_POOL":
                logger.info("Limpando pool simulado Oracle do tenant %s", tenant_key)
                del _oracle_pools[tenant_key]
                return
            logger.info("Fechando pool de conexões Oracle do tenant %s", tenant_key)
            try:
                await pool.close()
            except Exception as exc:
                logger.error("Erro ao fechar pool Oracle do tenant %s: %s", tenant_key, exc)
            del _oracle_pools[tenant_key]


async def get_oracle_connection(
    details: dict[str, Any],
    tenant_id: uuid.UUID | str | None = None,
    ignore_mock_global: bool = False
) -> oracledb.AsyncConnection:
    """
    Estabelece uma conexão assíncrona em modo Thin com o banco Oracle de produção.
    v3.0: Suporta simulação local transparente (host == "MOCK_ORACLE").
    """
    global _oracle_pools
    # 1. Validação de chaves obrigatórias
    required_keys = ("host", "port", "user", "password")
    for key in required_keys:
        if key not in details or details.get(key) in (None, ""):
            raise KeyError(f"Parâmetro obrigatório '{key}' ausente nas configurações de conexão do Oracle.")

    host = str(details["host"]).strip()
    
    # ── Interceptador de Simulação (MOCK_ORACLE) ──
    if host == "MOCK_ORACLE" or (settings.MOCK_ORACLE and not ignore_mock_global):
        logger.info("Modo de simulacao Oracle ativo (host=%s, MOCK_ORACLE=%s). Usando base PostgreSQL local como fonte.", host, settings.MOCK_ORACLE)
        if tenant_id is not None:
            tenant_key = str(tenant_id)
            async with _pools_lock:
                if tenant_key not in _oracle_pools:
                    _oracle_pools[tenant_key] = "MOCK_POOL"
        
        import asyncpg
        pg_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        pg_conn = await asyncpg.connect(pg_url)
        return MockOracleConnection(pg_conn)

    # 2. Conversão e normalização da porta
    try:
        port = int(details["port"])
    except ValueError as exc:
        raise ValueError("A porta de conexão do banco de dados Oracle deve ser um valor numérico.") from exc
        
    user = str(details["user"]).strip()
    password = details["password"]
    sid = str(details.get("sid") or "").strip() or None
    service_name = str(details.get("service_name") or "").strip() or None

    # 3. Garante que haja identificação do serviço (SID ou Service Name)
    if not sid and not service_name:
        raise ValueError("É necessário especificar o SID ou o Service Name para conectar ao Oracle.")

    # 4. Preflight TCP curto: se a porta nem abre, o problema nao e usuario/senha.
    await validate_oracle_listener(host, port)

    # 5. Tenta abrir a conexão de forma assíncrona (com Pool se tenant_id for informado)
    try:
        if tenant_id is not None:
            tenant_key = str(tenant_id)
            
            async with _pools_lock:
                if tenant_key not in _oracle_pools:
                    logger.info("Criando novo Pool de Conexões Oracle para o tenant %s (host=%s)", tenant_key, host)
                    pool_params = {
                        "host": host,
                        "port": port,
                        "user": user,
                        "password": password,
                        "min": 1,
                        "max": 4,
                        "increment": 1,
                        "expire_time": 2,
                    }
                    if sid:
                        pool_params["sid"] = sid
                    else:
                        pool_params["service_name"] = service_name
                    
                    _oracle_pools[tenant_key] = await oracledb.create_pool_async(**pool_params)
            
            pool = _oracle_pools[tenant_key]
            logger.info("Adquirindo conexão do Pool Oracle para o tenant %s", tenant_key)
            return await pool.acquire()
        else:
            # Standalone connection (ex: connection tests, validation)
            if sid:
                logger.info("Tentando conexão Thin assíncrona (via SID) com Oracle: %s:%d (User=%s)", host, port, user)
                conn = await oracledb.connect_async(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    sid=sid,
                    expire_time=2,
                )
            else:
                logger.info("Tentando conexão Thin assíncrona (via Service Name) com Oracle: %s:%d (User=%s)", host, port, user)
                conn = await oracledb.connect_async(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    service_name=service_name,
                    expire_time=2,
                )
            return conn
    except OracleConnectionValidationError:
        raise
    except Exception as exc:
        safe_error = classify_oracle_connection_error(exc, sid=sid, service_name=service_name)
        logger.error(
            "Falha ao conectar ao Oracle (%s:%d) | code=%s | detail=%s",
            host,
            port,
            safe_error.code,
            safe_error.technical_detail,
        )
        raise safe_error from exc


async def get_view_columns(connection: oracledb.AsyncConnection, view_name: str) -> list[tuple[str, str]]:
    """
    Inspeciona dinamicamente as colunas e os tipos de dados de uma view no banco Oracle.

    Executa uma consulta 'SELECT * FROM {view} WHERE 1=0' que obtém apenas os metadados
    do cabeçalho da view (colunas e tipos) sem carregar nenhum registro na memória do banco.

    Parâmetros:
    -----------
    connection : oracledb.AsyncConnection
        Conexão activa com o banco Oracle.
    view_name : str
        Nome da view cadastrada no catálogo.

    Retorno:
    --------
    list[tuple[str, str]]
        Lista de tuplas no formato (nome_coluna, tipo_coluna_simplificado), onde:
        - nome_coluna é a string em caixa alta.
        - tipo_coluna_simplificado pode ser 'NUMBER', 'DATE' ou 'STRING'.

    Exceções:
    ---------
    ValueError:
        Caso o nome da view contenha caracteres especiais suspeitos (AppSec/Sanitização).
    RuntimeError:
        Caso a view não exista no banco ou ocorra uma falha ao rodar a query de metadados.
    """
    # Sanitização estrita do nome da view para evitar injeção de SQL por concatenação direta
    clean_view_name = _safe_oracle_identifier(view_name)

    # Query segura para ler apenas o schema (retorno com 0 linhas)
    sql = f"SELECT * FROM {clean_view_name} WHERE 1=0"
    
    # Cria um cursor assíncrono
    cursor = connection.cursor()
    try:
        await cursor.execute(sql)
        
        columns = []
        # Analisa a propriedade 'description' do cursor contendo a tupla de metadados do Oracle
        for desc in cursor.description:
            col_name = desc[0]   # Nome da coluna
            col_type = desc[1]   # Tipo interno do driver oracledb
            
            # Mapeia tipos complexos do Oracle para categorias legíveis de tradução
            type_str = "STRING"
            if col_type == oracledb.DB_TYPE_NUMBER:
                type_str = "NUMBER"
            elif col_type in (oracledb.DB_TYPE_DATE, oracledb.DB_TYPE_TIMESTAMP, oracledb.DB_TYPE_TIMESTAMP_TZ):
                type_str = "DATE"
                
            columns.append((col_name, type_str))
            
        return columns
    except Exception as exc:
        logger.error("Erro de schema ao ler as colunas da view Oracle %s: %s", clean_view_name, exc)
        raise RuntimeError(
            f"Erro ao analisar o esquema de colunas da view '{clean_view_name}'. "
            "Verifique se o objeto existe ou se o usuário possui permissão de leitura."
        ) from exc
    finally:
        # Garante o encerramento do cursor de forma incondicional
        await _close_oracle_resource(cursor)


async def execute_view(
    connection: oracledb.AsyncConnection,
    view_name: str,
    params: dict[str, str],
) -> list[dict[str, Any]]:
    """
    Executa a view no Oracle com parametros livres extraidos pelo Motor de Intencoes v3.0.

    Suporta mapeamento inteligente de qualquer parametro extraido de linguagem natural:
    - Datas (data_inicio, data_fim) -> filtros de intervalo temporais com TO_DATE
    - Mes/Ano numerico -> cast para INTEGER se a coluna for NUMBER
    - Nomes de vendedor/cliente/produto -> filtros LIKE case-insensitive via UPPER()
    - Status, regiao, loja -> filtros LIKE case-insensitive (tolerante a variacoes)
    - Limite -> controle do volume maximo de linhas via ROWNUM
    - Aliases semanticos -> mapeamento para colunas reais da view pelo ALIAS_MAP
    - Fuzzy matching -> busca por nome parcial de coluna como ultimo recurso

    Protecao absoluta contra SQL Injection via Bind Variables nomeadas.

    Parametros:
    -----------
    connection : oracledb.AsyncConnection
        Conexao ativa com o banco Oracle (obtida do pool do tenant).
    view_name : str
        Nome exato da view cadastrada no catalogo (ex: 'VW_VENDAS_CONTEXTO_GERAL').
    params : dict[str, str]
        Dicionario de parametros livres extraidos pela IA.
        Qualquer combinacao de vendedor_nome, cliente_nome, produto_nome, etc.

    Retorno:
    --------
    list[dict[str, Any]]
        Lista de dicionarios com as linhas resultantes.

    Excecoes:
    ---------
    RuntimeError:
        Se a query falhar ou o banco Oracle retornar erro na execucao.
    """
    # ── 1. Inspeciona colunas e tipos da view ─────────────────────────────
    columns_info = await get_view_columns(connection, view_name)
    real_columns = [col[0].upper() for col in columns_info]
    col_type_map: dict[str, str] = {col[0].upper(): col[1] for col in columns_info}

    # Localiza a primeira coluna de data/timestamp para ancorar filtros temporais
    date_column: str | None = None
    for col_name, col_type in columns_info:
        if col_type == "DATE":
            date_column = col_name.upper()
            break

    # ── 2. Mapeamento semântico: nomes de parâmetros livres → colunas típicas Oracle ──
    # Prioridade: A) match direto de coluna > B) data_inicio/data_fim >
    #             C) alias semântico > D) fuzzy por substring > ignorado
    ALIAS_MAP: dict[str, list[str]] = {
        "vendedor_nome":   ["VENDEDOR", "NOME_VENDEDOR", "NM_VENDEDOR", "VENDEDOR_NOME"],
        "cliente_nome":    ["CLIENTE", "NOME_CLIENTE", "NM_CLIENTE", "CLIENTE_NOME", "COMPRADOR"],
        "produto_nome":    ["PRODUTO", "NOME_PRODUTO", "NM_PRODUTO", "DESCRICAO_PRODUTO", "DESC_PRODUTO"],
        "regiao":          ["REGIAO", "REGIÃO", "REGIAO_LOJA", "UF", "ESTADO"],
        "loja":            ["LOJA", "FILIAL", "NOME_LOJA", "CD_LOJA", "UNIDADE"],
        "status":          ["STATUS", "STATUS_PEDIDO", "SITUACAO", "SIT_PEDIDO"],
        "status_pedido":   ["STATUS_PEDIDO", "STATUS", "SITUACAO"],
        "categoria":       ["CATEGORIA", "CATEGORIA_PRODUTO", "CATEG"],
        "tipo_alerta":     ["TIPO_ALERTA", "TIPO", "ALERTA"],
        "forma_pagamento": ["FORMA_PAGAMENTO", "PAGAMENTO", "FORMA_PGTO"],
        "periodo":         ["PERIODO", "PERIODO_REFERENCIA"],
        # Legacy aliases for backward-compatibility with v2 schemas
        "cliente_id":      ["CLIENTE", "NOME_CLIENTE", "CD_CLIENTE"],
    }

    # ── 3. Constrói cláusulas WHERE dinâmicas ──────────────────────────────
    where_clauses: list[str] = []
    bind_params: dict[str, Any] = {}
    limite: int | None = None

    for param_name, param_value in params.items():
        if not param_value:
            continue

        # Sanitiza a chave do parâmetro (já vem limpa do context_guard, mas aplicamos novamente)
        clean_param = "".join(c for c in param_name if c.isalnum() or c == "_")
        if not clean_param:
            continue

        param_upper = clean_param.upper()
        str_value = str(param_value)

        # ── A. Extrai o limite de linhas (não vira cláusula WHERE) ──
        if clean_param == "limite":
            try:
                limite = min(int(str_value), 500)
            except ValueError:
                limite = 500
            continue

        # ── B. Match direto: parâmetro coincide exatamente com uma coluna ──
        if param_upper in real_columns:
            col_type = col_type_map.get(param_upper, "STRING")
            if clean_param in ("ano", "mes"):
                # Mês e ano sempre são inteiros
                try:
                    where_clauses.append(f"{param_upper} = :{clean_param}")
                    bind_params[clean_param] = int(str_value)
                except ValueError:
                    where_clauses.append(f"{param_upper} = :{clean_param}")
                    bind_params[clean_param] = str_value
            elif col_type == "NUMBER":
                try:
                    where_clauses.append(f"{param_upper} = :{clean_param}")
                    bind_params[clean_param] = float(str_value)
                except ValueError:
                    # Fallback: tratar como string com LIKE
                    where_clauses.append(
                        f"UPPER({param_upper}) LIKE UPPER(:{clean_param})"
                    )
                    bind_params[clean_param] = f"%{str_value}%"
            else:
                # STRING / DATE armazenada como VARCHAR → LIKE case-insensitive
                where_clauses.append(
                    f"UPPER({param_upper}) LIKE UPPER(:{clean_param})"
                )
                bind_params[clean_param] = f"%{str_value}%"

        # ── C. Filtros de data com TO_DATE ──
        elif clean_param == "data_inicio" and date_column:
            where_clauses.append(
                f"{date_column} >= TO_DATE(:data_inicio, 'YYYY-MM-DD')"
            )
            bind_params["data_inicio"] = str_value

        elif clean_param == "data_fim" and date_column:
            where_clauses.append(
                f"{date_column} <= TO_DATE(:data_fim, 'YYYY-MM-DD')"
            )
            bind_params["data_fim"] = str_value

        # ── D. Mapeamento semântico via ALIAS_MAP ──
        elif clean_param in ALIAS_MAP:
            candidate_cols = ALIAS_MAP[clean_param]
            matched_col = next(
                (c for c in candidate_cols if c in real_columns), None
            )
            if matched_col:
                bind_key = f"alias_{clean_param}"
                where_clauses.append(
                    f"UPPER({matched_col}) LIKE UPPER(:{bind_key})"
                )
                bind_params[bind_key] = f"%{str_value}%"
            else:
                logger.debug(
                    "Nenhuma coluna encontrada no ALIAS_MAP para '%s' na view '%s'",
                    clean_param, view_name,
                )

        # ── E. Fuzzy matching: substring do parâmetro presente no nome da coluna ──
        else:
            fuzzy_col = next(
                (
                    col for col in real_columns
                    if param_upper in col or col in param_upper
                ),
                None,
            )
            if fuzzy_col:
                bind_key = f"fuzzy_{clean_param}"
                col_type = col_type_map.get(fuzzy_col, "STRING")
                if col_type == "NUMBER":
                    try:
                        where_clauses.append(f"{fuzzy_col} = :{bind_key}")
                        bind_params[bind_key] = float(str_value)
                    except ValueError:
                        pass  # Ignora — não conseguimos mapear tipo numérico com valor não numérico
                else:
                    where_clauses.append(
                        f"UPPER({fuzzy_col}) LIKE UPPER(:{bind_key})"
                    )
                    bind_params[bind_key] = f"%{str_value}%"
            else:
                logger.debug(
                    "Parâmetro '%s' não mapeado para nenhuma coluna da view '%s' — ignorado",
                    clean_param, view_name,
                )

    # ── 4. Monta SQL final com ROWNUM sempre presente ──────────────────────
    clean_view_name = _safe_oracle_identifier(view_name)
    effective_limit = limite if limite else 500
    bind_params["row_limit"] = effective_limit

    sql = f"SELECT * FROM {clean_view_name}"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
        sql += " AND ROWNUM <= :row_limit"
    else:
        sql += " WHERE ROWNUM <= :row_limit"

    logger.info(
        "Execute view Oracle: %s | Bind keys: %s | row_limit=%d",
        sql[:200],
        list(bind_params.keys()),
        effective_limit,
    )

    # ── 5. Executa via cursor assíncrono ───────────────────────────────────
    cursor = connection.cursor()
    try:
        await cursor.execute(sql, bind_params)
        col_names = [desc[0] for desc in cursor.description]
        rows = await cursor.fetchall()
        return [dict(zip(col_names, row)) for row in rows]
    except Exception as exc:
        logger.error("Erro ao executar query Oracle '%s': %s", view_name, exc)
        raise RuntimeError(
            f"Falha na base de dados ao processar a análise: {exc}"
        ) from exc
    finally:
        await _close_oracle_resource(cursor)
