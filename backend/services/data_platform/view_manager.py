import logging
import uuid
from typing import Any
from sqlalchemy import select, update, delete
from models.view_catalog import ViewCatalog, ChartType
from models.metadata_catalog import MetadataCatalog
from models.blueprint import Blueprint
from services.data_platform.history_service import history_service
from services.data_platform.integrity_service import integrity_service
from database import get_db_context

logger = logging.getLogger("luminaai.data_platform.view_manager")

# Import lazy para evitar circular imports
def _get_catalog_api():
    from services.data_platform.catalog_api import catalog_api
    return catalog_api

class ViewManager:
    """
    View Manager (Gerenciador de Views).
    Único módulo autorizado a criar, alterar, atualizar ou reconstruir Views Analíticas.
    Controla todo o ciclo de vida, versionamento, dependências e reconstruções automáticas.
    """

    async def create_analytical_view(
        self,
        tenant_id: uuid.UUID,
        view_data: dict[str, Any]
    ) -> ViewCatalog:
        """Cria e registra uma nova View Analítica no catálogo e metadados."""
        nome_view = view_data["nome_view_oracle"].upper().strip()
        logger.info(
            "[ViewManager] Criando view analítica | tenant=%s | nome=%s",
            str(tenant_id)[:8],
            nome_view
        )
        
        async with get_db_context() as session:
            # 1. Registra no ViewCatalog
            view = ViewCatalog(
                tenant_id=tenant_id,
                nome_view_oracle=nome_view,
                descricao_para_ia=view_data["descricao_para_ia"],
                tipo_grafico_padrao=ChartType(view_data.get("tipo_grafico_padrao", "BAR")),
                parametros_schema=view_data.get("parametros_schema", {}),
                ativo=view_data.get("ativo", True)
            )
            session.add(view)
            await session.flush()
            
            # Calcula hash de integridade inicial
            schema_params = view_data.get("parametros_schema", {})
            tables = view_data.get("tabelas_utilizadas", [])
            initial_hash = integrity_service.calculate_integrity_hash(nome_view, schema_params, tables)
            
            # 2. Registra no MetadataCatalog
            meta = MetadataCatalog(
                tenant_id=tenant_id,
                nome_view=nome_view,
                estrutura_id=nome_view,
                tipo_estrutura="VIEW",
                origem=view_data.get("origem", "ERP_ORACLE"),
                owner=view_data.get("owner", "ViewManager"),
                categoria=view_data.get("categoria", "Comercial"),
                tags=view_data.get("tags", []),
                tabelas_utilizadas=tables,
                campos_utilizados=view_data.get("campos_utilizados", []),
                relacionamentos=view_data.get("relacionamentos", []),
                filtros_padrao=view_data.get("filtros_padrao", {}),
                periodos_suportados=view_data.get("periodos_suportados", []),
                kpis_suportados=view_data.get("kpis_suportados", []),
                dependencias=tables,
                versao=1,
                status="success",
                integridade="valid",
                hash_integridade=initial_hash
            )
            session.add(meta)
            await session.flush()
            
            # 3. Registra Log de Histórico
            await history_service.log_change(
                tenant_id=tenant_id,
                estrutura_tipo="VIEW",
                estrutura_id=nome_view,
                acao="CREATE",
                detalhes={
                    "nome_view": nome_view,
                    "versao": 1,
                    "tabelas": tables
                }
            )

            await session.commit()

        # 4. Registra no CatalogAPI (lineage + grafo + health scores)
        try:
            api = _get_catalog_api()
            await api.register(
                tenant_id=tenant_id,
                tipo="VIEW",
                dados={
                    "nome_view": nome_view,
                    "estrutura_id": nome_view,
                    "origem": view_data.get("origem", "ERP_ORACLE"),
                    "tags": view_data.get("tags", []),
                    "categoria": view_data.get("categoria", "Comercial"),
                    "kpis_suportados": view_data.get("kpis_suportados", []),
                    "tabelas_utilizadas": tables,
                },
                lineage_tabelas=tables,
                upstream_ids=tables,
            )
        except Exception as e:
            logger.warning("[ViewManager] CatalogAPI.register falhou (não crítico): %s", e)

        return view

    async def update_analytical_view(
        self,
        tenant_id: uuid.UUID,
        nome_view: str,
        updates: dict[str, Any]
    ) -> ViewCatalog:
        """Atualiza metadados ou propriedades estruturais de uma view analítica, gerando nova versão."""
        nome_view = nome_view.upper().strip()
        logger.info("[ViewManager] Atualizando view analítica: %s", nome_view)
        
        async with get_db_context() as session:
            stmt_v = select(ViewCatalog).where(
                ViewCatalog.tenant_id == tenant_id,
                ViewCatalog.nome_view_oracle == nome_view
            )
            res_v = await session.execute(stmt_v)
            view = res_v.scalar_one()
            
            stmt_m = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.nome_view == nome_view
            )
            res_m = await session.execute(stmt_m)
            meta = res_m.scalar_one()
            
            # Aplica modificações
            if "descricao_para_ia" in updates:
                view.descricao_para_ia = updates["descricao_para_ia"]
            if "tipo_grafico_padrao" in updates:
                view.tipo_grafico_padrao = ChartType(updates["tipo_grafico_padrao"])
            if "parametros_schema" in updates:
                view.parametros_schema = updates["parametros_schema"]
            if "ativo" in updates:
                view.ativo = updates["ativo"]
                
            if "tabelas_utilizadas" in updates:
                meta.tabelas_utilizadas = updates["tabelas_utilizadas"]
            if "campos_utilizados" in updates:
                meta.campos_utilizados = updates["campos_utilizados"]
            if "relacionamentos" in updates:
                meta.relacionamentos = updates["relacionamentos"]
            if "filtros_padrao" in updates:
                meta.filtros_padrao = updates["filtros_padrao"]
            if "periodos_suportados" in updates:
                meta.periodos_suportados = updates["periodos_suportados"]
            if "kpis_suportados" in updates:
                meta.kpis_suportados = updates["kpis_suportados"]
                
            # Incrementa versão analítica
            meta.versao += 1
            
            # Recalcula hash com as novas atualizações
            meta.hash_integridade = integrity_service.calculate_integrity_hash(
                nome_view,
                view.parametros_schema,
                meta.tabelas_utilizadas
            )
            
            session.add(view)
            session.add(meta)
            await session.flush()
            
            # Log de evolução
            await history_service.log_change(
                tenant_id=tenant_id,
                estrutura_tipo="VIEW",
                estrutura_id=nome_view,
                acao="UPDATE",
                detalhes={
                    "nome_view": nome_view,
                    "versao": meta.versao,
                    "hash": meta.hash_integridade
                }
            )
            await session.commit()
            return view

    async def reconstruct_view(
        self,
        tenant_id: uuid.UUID,
        view_name: str,
        reason: str
    ) -> dict[str, Any]:
        """
        Executa a reconstrução automática de uma view em decorrência de alterações do ERP.
        Gera nova versão analítica, atualiza o Metadata Catalog, migra referências e registra logs históricos.
        """
        view_name = view_name.upper().strip()
        logger.warning(
            "[ViewManager] Iniciando RECONSTRUÇÃO AUTOMÁTICA da view %s | motivo: %s",
            view_name,
            reason
        )
        
        async with get_db_context() as session:
            stmt_m = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.nome_view == view_name
            )
            res_m = await session.execute(stmt_m)
            meta = res_m.scalar_one_or_none()
            
            if not meta:
                raise ValueError(f"MetadataCatalog não encontrado para view: {view_name}")
            
            stmt_v = select(ViewCatalog).where(
                ViewCatalog.tenant_id == tenant_id,
                ViewCatalog.nome_view_oracle == view_name
            )
            res_v = await session.execute(stmt_v)
            view = res_v.scalar_one()
            
            old_version = meta.versao
            new_version = old_version + 1
            
            # Atualiza o status nos metadados para reconstruído
            meta.versao = new_version
            meta.status = "reconstructed"
            meta.integridade = "valid"
            
            # Recalcula o hash de integridade analítico
            meta.hash_integridade = integrity_service.calculate_integrity_hash(
                view_name,
                view.parametros_schema,
                meta.tabelas_utilizadas
            )
            
            session.add(meta)
            await session.flush()
            
            # Migração de dependências: Blueprints associados devem subir versão de referência
            stmt_bp = select(Blueprint).where(
                Blueprint.tenant_id == tenant_id,
                Blueprint.view_name == view_name
            )
            res_bp = await session.execute(stmt_bp)
            blueprints = res_bp.scalars().all()
            
            migrated_blueprints = []
            for bp in blueprints:
                bp.version = new_version
                session.add(bp)
                migrated_blueprints.append(bp.intent_id)
                
            # Grava na trilha histórica imutável
            await history_service.log_change(
                tenant_id=tenant_id,
                estrutura_tipo="VIEW",
                estrutura_id=view_name,
                acao="RECONSTRUCT",
                detalhes={
                    "view_name": view_name,
                    "versao_anterior": old_version,
                    "versao_nova": new_version,
                    "motivo": reason,
                    "blueprints_migrados": migrated_blueprints
                }
            )
            
            await session.commit()
            
            return {
                "view_name": view_name,
                "status": "success",
                "versao": new_version,
                "blueprints_migrados": len(migrated_blueprints)
            }

# Singleton export
view_manager = ViewManager()
