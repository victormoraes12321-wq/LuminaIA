"""
LuminaAI Governed Public Provenance Summary Service
Version: lumina.validation-provenance/1.0
"""

from typing import List, Optional

from contracts.validation_provenance_v2 import (
    AnalyticalFactV2,
    PublicProvenanceSummaryV2,
    ValidationStatus,
)


class PublicProvenanceService:
    @staticmethod
    def build_public_summary(
        facts: List[AnalyticalFactV2],
        status: ValidationStatus,
        warnings: List[str],
        certification_checksum: str,
    ) -> PublicProvenanceSummaryV2:
        metric_names = sorted(list({f.canonical_metric_id for f in facts if f.canonical_metric_id}))
        if not metric_names:
            metric_names = ["Consulta Analítica Geral"]

        periods = [f"{f.period_start or ''} - {f.period_end or ''}".strip(" -") for f in facts if f.period_start or f.period_end]
        period_desc = ", ".join(sorted(list(set(periods)))) if periods else "Período Solicitado"

        truncated = any(f.completeness.value == "TRUNCATED" for f in facts) or any("truncat" in w.lower() for w in warnings)

        return PublicProvenanceSummaryV2(
            contract_version="lumina.validation-provenance/1.0",
            metric_names=metric_names,
            period_description=period_desc,
            applied_filters=[],
            data_source_description="PostgreSQL Clone Analítico Governado",
            source_last_updated=None,
            validation_status=status,
            warnings=warnings,
            truncated=truncated,
            certification_checksum=certification_checksum,
        )
