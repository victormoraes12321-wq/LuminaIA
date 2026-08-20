"""
LuminaAI - Package Matcher Engine
---------------------------------
Finds reusable Analytical Packages for a structured Business Intent.
"""
from __future__ import annotations

import logging
import uuid
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from models.analytical_package import AnalyticalPackage
from services.ai.schemas import BusinessIntentSchema
from services.data_platform.intent_fingerprint import intent_fingerprint_generator
from services.data_platform.package_compatibility import package_compatibility_engine

logger = logging.getLogger("luminaai.ai.package_matcher")


class PackageMatcher:
    """Searches existing Analytical Packages before a new Blueprint is needed."""

    async def match_package(
        self,
        tenant_id: uuid.UUID,
        business_intent: BusinessIntentSchema,
        db: AsyncSession,
        threshold: float = 0.85,
    ) -> tuple[AnalyticalPackage | None, float]:
        """Generate a semantic fingerprint and return a compatible package if any."""
        logger.info("[CIE] Searching reusable Analytical Packages...")

        structured_plan = SimpleNamespace(
            query_type="AGGREGATION" if business_intent.agrupamentos else "SELECT",
            metrics=list(business_intent.kpis or business_intent.indicadores or []),
            group_by=list(business_intent.agrupamentos or []),
            filters=SimpleNamespace(
                date_range=business_intent.periodo or "",
                products=business_intent.filtros.get("products", []),
                customers=business_intent.filtros.get("customers", []),
                regions=business_intent.filtros.get("regions", []),
            ),
            comparisons=list(business_intent.comparacoes or []),
        )
        intent_payload = SimpleNamespace(
            operacao=business_intent.objetivo,
            entidade_alvo=business_intent.entidade,
            periodo_referencia=business_intent.periodo,
            is_comparacao=bool(business_intent.comparacoes),
            plano_estruturado=structured_plan,
        )

        fingerprint = intent_fingerprint_generator.generate(intent_payload)
        package, score = await package_compatibility_engine.find_compatible_package(
            fingerprint=fingerprint,
            tenant_id=tenant_id,
            db=db,
        )

        if package and score >= threshold:
            logger.info("[CIE] Compatible package found: id=%s score=%.2f", package.id, score)
            return package, score

        logger.info("[CIE] No compatible package found above %.2f (score=%.2f).", threshold, score)
        return None, score


package_matcher = PackageMatcher()
