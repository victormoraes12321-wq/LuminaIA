import hashlib
import json
import logging
import uuid
from typing import Any
from sqlalchemy import select
from models.view_catalog import ViewCatalog
from models.metadata_catalog import MetadataCatalog
from models.blueprint import Blueprint
from database import get_db_context

logger = logging.getLogger("luminaai.data_platform.integrity_service")

def _get_catalog_api():
    from services.data_platform.catalog_api import catalog_api
    return catalog_api


class IntegrityService:
    """
    Serviço responsável por validar a integridade estrutural, versionamento,
    sincronização e relacionamentos de dados na Data Platform.
    """

    def calculate_integrity_hash(self, view_name: str, schema: dict, tables: list[str]) -> str:
        """Calcula hash criptográfico SHA-256 da estrutura para auditoria."""
        serialized = f"name:{view_name}|schema:{json.dumps(schema, sort_keys=True)}|tables:{','.join(sorted(tables))}"
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    async def validate_tenant_integrity(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        """
        Executa uma auditoria completa de integridade estrutural para um tenant.
        Retorna um relatório detalhado com inconsistências encontradas.
        """
        logger.info("[IntegrityService] Iniciando auditoria de integridade | tenant=%s", str(tenant_id)[:8])
        inconsistencies = []
        is_valid = True
        
        async with get_db_context() as session:
            # 1. Recupera catálogo de views e catálogo de metadados
            stmt_views = select(ViewCatalog).where(ViewCatalog.tenant_id == tenant_id)
            res_views = await session.execute(stmt_views)
            views = res_views.scalars().all()
            views_dict = {v.nome_view_oracle: v for v in views}
            
            stmt_meta = select(MetadataCatalog).where(MetadataCatalog.tenant_id == tenant_id)
            res_meta = await session.execute(stmt_meta)
            metas = res_meta.scalars().all()
            metas_dict = {m.nome_view: m for m in metas}
            
            # 2. Valida compatibilidade ViewCatalog <=> MetadataCatalog
            for view_name, view_obj in views_dict.items():
                meta_obj = metas_dict.get(view_name)
                if not meta_obj:
                    is_valid = False
                    inconsistencies.append({
                        "tipo": "METADATA_MISSING",
                        "alvo": view_name,
                        "descricao": f"A view '{view_name}' está no catálogo ativo mas não possui registro correspondente no Metadata Catalog."
                    })
                    continue
                
                # Valida hash de integridade
                expected_hash = self.calculate_integrity_hash(
                    view_name=view_name,
                    schema=view_obj.parametros_schema or {},
                    tables=meta_obj.tabelas_utilizadas or []
                )
                
                if meta_obj.hash_integridade and meta_obj.hash_integridade != expected_hash:
                    is_valid = False
                    inconsistencies.append({
                        "tipo": "HASH_MISMATCH",
                        "alvo": view_name,
                        "descricao": f"O hash de integridade da view '{view_name}' não confere. Possível modificação estrutural não registrada."
                    })
                elif not meta_obj.hash_integridade:
                    # Registra hash se ausente
                    meta_obj.hash_integridade = expected_hash
                    session.add(meta_obj)
                    logger.info("[IntegrityService] Gravado hash de integridade ausente para view: %s", view_name)
            
            # 3. Valida sincronização e status de integridade nos metadados
            for view_name, meta_obj in metas_dict.items():
                if view_name not in views_dict:
                    is_valid = False
                    inconsistencies.append({
                        "tipo": "VIEW_MISSING_IN_CATALOG",
                        "alvo": view_name,
                        "descricao": f"Metadados existem para a view '{view_name}' mas ela não está no ViewCatalog."
                    })
                    
                if meta_obj.integridade == "corrupted":
                    is_valid = False
                    inconsistencies.append({
                        "tipo": "METADATA_CORRUPTED",
                        "alvo": view_name,
                        "descricao": f"A view '{view_name}' está explicitamente marcada como corrompida por falha operacional de sincronização."
                    })

            # 4. Valida consistência de Blueprints em relação ao catálogo
            stmt_bp = select(Blueprint).where(Blueprint.tenant_id == tenant_id)
            res_bp = await session.execute(stmt_bp)
            bps = res_bp.scalars().all()
            
            for bp in bps:
                if bp.view_name not in views_dict:
                    is_valid = False
                    inconsistencies.append({
                        "tipo": "BLUEPRINT_VIEW_ORPHAN",
                        "alvo": f"blueprint:{bp.intent_id}",
                        "descricao": f"O Blueprint '{bp.intent_id}' faz referência à view '{bp.view_name}' que não existe no ViewCatalog."
                    })
                
                # Valida versionamento
                # O blueprint deve ter versão compatível com a view (blueprint.version <= view.version se houver)
                meta_obj = metas_dict.get(bp.view_name)
                if meta_obj and bp.version > meta_obj.versao:
                    is_valid = False
                    inconsistencies.append({
                        "tipo": "VERSION_INCONSISTENCY",
                        "alvo": f"blueprint:{bp.intent_id}",
                        "descricao": f"Inconsistência de versão: Blueprint versão {bp.version} é mais recente que a View correspondente versão {meta_obj.versao}."
                    })
            
            # 5. Salva mudanças (como gravação de hashes ausentes)
            await session.commit()
            
        logger.info(
            "[IntegrityService] Auditoria finalizada. Valido=%s | Inconsistências=%d",
            is_valid,
            len(inconsistencies)
        )

        # 6. Atualiza health scores via CatalogAPI após auditoria
        try:
            api = _get_catalog_api()
            for view_name in views_dict:
                await api.refresh_health(tenant_id, view_name)
        except Exception as e:
            logger.debug("[IntegrityService] Atualização de health scores ignorada: %s", e)

        return {
            "valid": is_valid,
            "inconsistencies": inconsistencies
        }

# Singleton export
integrity_service = IntegrityService()
