import logging
import uuid
from typing import Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.blueprint import Blueprint
from models.dashboard_instance import DashboardInstance
from models.svr import SVRCompatibilityMatrix

logger = logging.getLogger("luminaai.services.svr_migration")

class SVRMigrationEngine:
    """
    Migration Engine do Semantic Version Registry (SVR).
    Responsável por auditar, prever e gerar relatórios de impacto de migração
    de versões semânticas ou físicas sobre Blueprints, Dashboards, KPIs e caches.
    """

    async def evaluate_migration_impact(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        concept_id: str,
        new_semantic_version: str,
        new_mapping_version: str,
    ) -> dict[str, Any]:
        """
        Avalia o impacto de atualizar um conceito para uma nova versão (ex: nova regra fiscal ou coluna física).
        Retorna o relatório completo de dependências afetadas.
        """
        try:
            # 1. Busca os Blueprints que usam este conceito (em métricas, group_by ou filtros)
            # Na tabela blueprint_repository:
            # - metrics é JSONB contendo lista de strings (IDs ou nomes)
            # - group_by é JSONB contendo lista de dimensões
            # - filters é JSONB contendo mapeamento de filtros
            stmt_bp = select(Blueprint).where(Blueprint.tenant_id == tenant_id)
            res_bp = await db.execute(stmt_bp)
            blueprints = res_bp.scalars().all()

            affected_blueprints = []
            for bp in blueprints:
                # Verifica se o concept_id está nas métricas ou group_by do blueprint
                # Admite tanto o ID corporativo estável (ex: MET_001) quanto o nome físico legado
                uses_metric = concept_id in (bp.metrics or [])
                uses_groupby = concept_id in (bp.group_by or [])
                uses_filter = concept_id in (bp.filters or {})

                if uses_metric or uses_groupby or uses_filter:
                    affected_blueprints.append({
                        "id": str(bp.id),
                        "nome": bp.nome_consulta,
                        "tipo_analise": bp.tipo_analise,
                        "versao_atual": bp.version,
                        "autor": bp.autor,
                        "motivo_uso": "Métrica" if uses_metric else ("Agrupamento" if uses_groupby else "Filtro")
                    })

            # 2. Busca os Dashboards que utilizam os Blueprints afetados
            # Na tabela dashboard_instances:
            # - layout ou config podem conter referências aos blueprints
            affected_dashboards = []
            if affected_blueprints:
                affected_bp_ids = {bp["id"] for bp in affected_blueprints}
                
                stmt_db = select(DashboardInstance).where(DashboardInstance.tenant_id == tenant_id)
                res_db = await db.execute(stmt_db)
                dashboards = res_db.scalars().all()

                for d in dashboards:
                    # Verifica se o dashboard possui widgets com referências aos blueprints afetados
                    layout = getattr(d, "layout_override", {}) or {}
                    widgets = layout.get("widgets", []) if isinstance(layout, dict) else []
                    has_reference = False
                    
                    for w in widgets:
                        if not isinstance(w, dict):
                            continue
                        bp_ref = w.get("blueprint_id") or w.get("blueprintId")
                        if bp_ref and str(bp_ref) in affected_bp_ids:
                            has_reference = True
                            break
                    
                    if has_reference:
                        affected_dashboards.append({
                            "id": str(d.id),
                            "nome": getattr(d, "name", "Dashboard"),
                            "autor": "Admin"
                        })

            # 3. Estatísticas de Cache estimadas que seriam invalidadas
            # O SVR isola o cache por versão, então novas versões nascerão sem cache (miss total),
            # o que evita cache indevido e preserva o cache antigo para blueprints não migrados.
            estimated_cache_entries = len(affected_blueprints) * 3

            # 4. Compila o Relatório de Impacto
            report = {
                "concept_id": concept_id,
                "target_semantic_version": new_semantic_version,
                "target_mapping_version": new_mapping_version,
                "impact_level": "ALTO" if len(affected_blueprints) > 2 else ("MEDIO" if affected_blueprints else "BAIXO"),
                "affected_blueprints_count": len(affected_blueprints),
                "affected_blueprints": affected_blueprints,
                "affected_dashboards_count": len(affected_dashboards),
                "affected_dashboards": affected_dashboards,
                "estimated_cache_invalidation_count": estimated_cache_entries,
                "requires_manual_approval": True,
                "migration_instructions": (
                    f"A migração do conceito '{concept_id}' afetará {len(affected_blueprints)} blueprints. "
                    "Recomenda-se homologar os dashboards e blueprints afetados em ambiente de staging antes "
                    "de atualizar as referências de versão de blueprint no Version Center."
                )
            }

            logger.info("[SVR Migration] Avaliação de impacto para o conceito %s concluída: nível=%s", concept_id, report["impact_level"])
            return report

        except Exception as exc:
            logger.error("[SVR Migration] Erro ao avaliar impacto de migração: %s", exc)
            return {"error": str(exc)}

# Instância Singleton do Migration Engine
svr_migration = SVRMigrationEngine()
