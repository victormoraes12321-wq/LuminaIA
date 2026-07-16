"""
LuminaAI — Business Dependency & Impact Engine Service
-------------------------------------------------------
Mapeia dependências entre KPIs, fórmulas, blueprints, views, e packages.
Identifica e calcula o impacto colateral caso uma regra ou indicador de BI seja alterado.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.business_kpi import BusinessKPI
from models.business_formula import BusinessFormula
from models.analytical_package import AnalyticalPackage

logger = logging.getLogger("luminaai.business.dependency_engine")


class BusinessDependencyEngine:
    """
    Analisa impacto de alterações e gerencia dependências conceituais de BI.
    """

    async def get_impact_analysis(
        self,
        tenant_id: uuid.UUID,
        element_name: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Calcula e retorna a árvore de impactos de uma alteração no indicador `element_name`.

        Retorna:
            - kpis_impactados: KPIs cujas fórmulas dependem deste elemento.
            - formulas_impactadas: Fórmulas que dependem deste elemento.
            - packages_impactados: Analytical Packages que expõem ou dependem deste elemento.
            - blueprints_impactados: Blueprints cadastrados que utilizam este elemento.
        """
        element_clean = element_name.strip()
        logger.info(
            "[DependencyEngine] Analisando impacto para '%s' | tenant=%s",
            element_clean, tenant_id,
        )

        # 1. Busca KPIs impactados (cuja formula_oficial contém o nome do elemento)
        stmt_kpis = select(BusinessKPI).where(
            and_(
                BusinessKPI.tenant_id == tenant_id,
                BusinessKPI.status == "ACTIVE",
                or_(
                    BusinessKPI.formula_oficial.ilike(f"%{element_clean}%"),
                    BusinessKPI.nome.ilike(element_clean),  # O próprio
                ),
            )
        )
        res_kpis = await db.execute(stmt_kpis)
        kpis = res_kpis.scalars().all()
        kpis_impactados = [k.nome for k in kpis if k.nome.lower() != element_clean.lower()]

        # 2. Busca Fórmulas impactadas
        stmt_formulas = select(BusinessFormula).where(
            and_(
                BusinessFormula.tenant_id == tenant_id,
                BusinessFormula.status == "ACTIVE",
                or_(
                    BusinessFormula.formula.ilike(f"%{element_clean}%"),
                    BusinessFormula.dependencias.contains([element_clean]),
                ),
            )
        )
        res_formulas = await db.execute(stmt_formulas)
        formulas = res_formulas.scalars().all()
        formulas_impactadas = [f.nome for f in formulas]

        # 3. Busca Packages impactados
        # (Packages ativos cujo intent_fingerprint ou metrics possuem o elemento ou dependências)
        stmt_packages = select(AnalyticalPackage).where(
            and_(
                AnalyticalPackage.tenant_id == tenant_id,
                AnalyticalPackage.status.name == "ACTIVE",
            )
        )
        res_packages = await db.execute(stmt_packages)
        packages = res_packages.scalars().all()

        packages_impactados = []
        for pkg in packages:
            # Verifica se o elemento está listado nas métricas estruturais do package
            pkg_struct = pkg.analytical_structure or {}
            pkg_metrics = pkg_struct.get("metrics", [])
            if element_clean in pkg_metrics:
                packages_impactados.append({
                    "id": str(pkg.id),
                    "version": pkg.version,
                    "intent_key": pkg.intent_key,
                })

        # 4. Busca Blueprints impactados
        # Busca no blueprint_repository em memória/banco
        from services.data_platform.blueprint_repository import blueprint_repository
        all_bps = await blueprint_repository.get_all_blueprints(tenant_id, db)
        blueprints_impactados = []
        for bp in all_bps:
            bp_metrics = bp.metrics or []
            if element_clean in bp_metrics:
                blueprints_impactados.append({
                    "id": bp.intent_id,
                    "nome": bp.nome_consulta,
                    "view_name": bp.view_name,
                })

        total_impactos = (
            len(kpis_impactados) + len(formulas_impactadas) +
            len(packages_impactados) + len(blueprints_impactados)
        )

        return {
            "alvo": element_clean,
            "total_impactos": total_impactos,
            "kpis_impactados": kpis_impactados,
            "formulas_impactadas": formulas_impactadas,
            "packages_impactados": packages_impactados,
            "blueprints_impactados": blueprints_impactados,
            "grau_severidade": "ALTO" if total_impactos > 3 else "BAIXO",
        }


# Singleton export
business_dependency_engine = BusinessDependencyEngine()
