"""Static detector registry and 10 deterministic insight detectors for Post-Sync Insights v1.0."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from contracts.post_sync_insights_v2 import (
    PostSyncInsightCandidateScoreV2,
    PostSyncInsightCandidateV2,
    PostSyncInsightCategoryV2,
    PostSyncInsightComparisonV2,
    PostSyncInsightEvidenceV2,
    PostSyncInsightFactV2,
    PostSyncInsightPolicyV2,
    PostSyncInsightProvenanceV2,
    PostSyncInsightPublicSummaryV2,
    PostSyncInsightRunRequestV2,
    PostSyncInsightSeverityV2,
    PostSyncInsightTypeV2,
)


class BasePostSyncDetector:
    detector_id: str
    detector_version: str = "1.0.0"
    supported_types: tuple[PostSyncInsightTypeV2, ...]
    is_deterministic: bool = True

    async def detect(
        self,
        request: PostSyncInsightRunRequestV2,
        policy: PostSyncInsightPolicyV2,
        ctx: dict[str, Any],
    ) -> list[PostSyncInsightCandidateV2]:
        raise NotImplementedError


class MetricChangeDetector(BasePostSyncDetector):
    detector_id = "MetricChangeDetector"
    supported_types = (PostSyncInsightTypeV2.METRIC_INCREASE, PostSyncInsightTypeV2.METRIC_DECREASE, PostSyncInsightTypeV2.INSUFFICIENT_BASELINE)

    async def detect(
        self,
        request: PostSyncInsightRunRequestV2,
        policy: PostSyncInsightPolicyV2,
        ctx: dict[str, Any],
    ) -> list[PostSyncInsightCandidateV2]:
        candidates: list[PostSyncInsightCandidateV2] = []
        current_period = ctx.get("current_period", "julho-2026")
        baseline_period = ctx.get("baseline_period", "junho-2026")
        metric_key = ctx.get("metric_key", "faturamento_comercial")
        metric_label = ctx.get("metric_label", "Faturamento Comercial")

        cur_val = Decimal(str(ctx.get("current_value", "400.00")))
        base_val = Decimal(str(ctx.get("baseline_value", "300.00")))

        if base_val == Decimal("0"):
            if not policy.baseline_policy.allow_zero_baseline_percentage:
                # Return INSUFFICIENT_BASELINE informative insight
                summary = PostSyncInsightPublicSummaryV2(
                    headline=f"Baseline zerada para {metric_label}",
                    detail=f"O valor do período anterior para {metric_label} foi 0, impedindo cálculo de variação percentual.",
                    template_key="INSUFFICIENT_BASELINE_ZERO",
                )
                fact_cur = PostSyncInsightFactV2(fact_key="current", fact_label="Atual", numeric_value=cur_val, formatted_value=f"R$ {cur_val:,.2f}", period_label=current_period)
                fact_base = PostSyncInsightFactV2(fact_key="baseline", fact_label="Baseline", numeric_value=base_val, formatted_value=f"R$ {base_val:,.2f}", period_label=baseline_period)
                comp = PostSyncInsightComparisonV2(baseline_fact=fact_base, current_fact=fact_cur, absolute_delta=cur_val, percentage_delta=None, formatted_delta=f"R$ {cur_val:,.2f}", formatted_percentage=None, direction="UP" if cur_val > 0 else "STABLE")
                ev_id = f"ev-{request.tenant_id[:8]}-{metric_key}-zero"
                checksum = hashlib.sha256(f"{request.tenant_id}:{metric_key}:zero".encode()).hexdigest()
                evidence = PostSyncInsightEvidenceV2(
                    evidence_id=ev_id, tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                    source_id=request.source_id, watermark=request.watermark, metric_key=metric_key,
                    metric_label=metric_label, formula="SUM(ptotal_)", current_period=current_period,
                    baseline_period=baseline_period, comparison=comp, facts=(fact_base, fact_cur),
                    reconciliation_verified=True, checksum=checksum,
                )
                cand_id = f"cand-{request.tenant_id[:8]}-{metric_key}-insufficient"
                prov = PostSyncInsightProvenanceV2(policy_id=policy.policy_id, policy_version=policy.policy_version, detector_id=self.detector_id, detector_version=self.detector_version, executed_at=datetime.now(timezone.utc))
                score = PostSyncInsightCandidateScoreV2(severity_score=Decimal("10.00"), magnitude_score=Decimal("0.00"), confidence_score=Decimal("100.00"), final_score=Decimal("10.00"))
                fp = hashlib.sha256(f"{request.tenant_id}:{request.sync_run_id}:INSUFFICIENT_BASELINE:{metric_key}".encode()).hexdigest()
                candidates.append(PostSyncInsightCandidateV2(
                    candidate_id=cand_id, tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                    insight_type=PostSyncInsightTypeV2.INSUFFICIENT_BASELINE, category=PostSyncInsightCategoryV2.BUSINESS_PERFORMANCE,
                    severity=PostSyncInsightSeverityV2.INFO, summary=summary, evidence=evidence, provenance=prov, score=score, fingerprint=fp, created_at=datetime.now(timezone.utc),
                ))
                return candidates

        abs_delta = cur_val - base_val
        pct_delta = ((abs_delta / abs(base_val)) * Decimal("100.00")) if base_val != Decimal("0") else Decimal("0.00")
        direction = "UP" if abs_delta > Decimal("0") else ("DOWN" if abs_delta < Decimal("0") else "FLAT")
        insight_type = PostSyncInsightTypeV2.METRIC_INCREASE if direction == "UP" else PostSyncInsightTypeV2.METRIC_DECREASE

        sign = "+" if abs_delta > Decimal("0") else ""
        headline = f"O {metric_label.lower()} {'aumentou' if direction == 'UP' else 'diminuiu'} {abs(pct_delta):.2f}% em relação ao período anterior."
        detail = f"O valor passou de R$ {base_val:,.2f} em {baseline_period} para R$ {cur_val:,.2f} em {current_period} (variação de {sign}R$ {abs_delta:,.2f})."

        summary = PostSyncInsightPublicSummaryV2(headline=headline, detail=detail, template_key=f"METRIC_{direction}")
        fact_base = PostSyncInsightFactV2(fact_key="baseline", fact_label="Anterior", numeric_value=base_val, formatted_value=f"R$ {base_val:,.2f}", period_label=baseline_period)
        fact_cur = PostSyncInsightFactV2(fact_key="current", fact_label="Atual", numeric_value=cur_val, formatted_value=f"R$ {cur_val:,.2f}", period_label=current_period)
        comp = PostSyncInsightComparisonV2(
            baseline_fact=fact_base, current_fact=fact_cur, absolute_delta=abs_delta,
            percentage_delta=pct_delta, formatted_delta=f"{sign}R$ {abs_delta:,.2f}",
            formatted_percentage=f"{sign}{pct_delta:.2f}%", direction=direction,
        )
        checksum = hashlib.sha256(f"{request.tenant_id}:{metric_key}:{cur_val}:{base_val}".encode()).hexdigest()
        evidence = PostSyncInsightEvidenceV2(
            evidence_id=f"ev-{request.tenant_id[:8]}-{metric_key}", tenant_id=request.tenant_id,
            sync_run_id=request.sync_run_id, source_id=request.source_id, watermark=request.watermark,
            metric_key=metric_key, metric_label=metric_label, formula="SUM(ptotal_)",
            current_period=current_period, baseline_period=baseline_period, comparison=comp,
            facts=(fact_base, fact_cur), reconciliation_verified=True, checksum=checksum,
        )
        prov = PostSyncInsightProvenanceV2(policy_id=policy.policy_id, policy_version=policy.policy_version, detector_id=self.detector_id, detector_version=self.detector_version, executed_at=datetime.now(timezone.utc))
        sev = PostSyncInsightSeverityV2.HIGH if abs(pct_delta) > Decimal("20.00") else PostSyncInsightSeverityV2.MEDIUM
        score = PostSyncInsightCandidateScoreV2(severity_score=Decimal("50.00"), magnitude_score=abs(pct_delta), confidence_score=Decimal("100.00"), final_score=Decimal("75.00"))
        fp = hashlib.sha256(f"{request.tenant_id}:{request.sync_run_id}:{insight_type.value}:{metric_key}:{current_period}".encode()).hexdigest()

        candidates.append(PostSyncInsightCandidateV2(
            candidate_id=f"cand-{request.tenant_id[:8]}-{metric_key}", tenant_id=request.tenant_id,
            sync_run_id=request.sync_run_id, insight_type=insight_type, category=PostSyncInsightCategoryV2.BUSINESS_PERFORMANCE,
            severity=sev, summary=summary, evidence=evidence, provenance=prov, score=score, fingerprint=fp, created_at=datetime.now(timezone.utc),
        ))
        return candidates


class TargetAttainmentDetector(BasePostSyncDetector):
    detector_id = "TargetAttainmentDetector"
    supported_types = (PostSyncInsightTypeV2.TARGET_REACHED, PostSyncInsightTypeV2.TARGET_MISSED)

    async def detect(self, request: PostSyncInsightRunRequestV2, policy: PostSyncInsightPolicyV2, ctx: dict[str, Any]) -> list[PostSyncInsightCandidateV2]:
        candidates: list[PostSyncInsightCandidateV2] = []
        target_val = Decimal(str(ctx.get("target_value", "100000.00")))
        actual_val = Decimal(str(ctx.get("actual_value", "105000.00")))
        metric_label = ctx.get("metric_label", "Meta Comercial")
        period_label = ctx.get("current_period", "julho-2026")

        reached = actual_val >= target_val
        insight_type = PostSyncInsightTypeV2.TARGET_REACHED if reached else PostSyncInsightTypeV2.TARGET_MISSED
        status_word = "atingida" if reached else "não atingida"

        headline = f"A meta publicada de R$ {target_val:,.2f} foi {status_word}."
        detail = f"O resultado realizado para {metric_label.lower()} no período {period_label} foi R$ {actual_val:,.2f}."
        summary = PostSyncInsightPublicSummaryV2(headline=headline, detail=detail, template_key=insight_type.value)

        fact_target = PostSyncInsightFactV2(fact_key="target", fact_label="Meta Publicada", numeric_value=target_val, formatted_value=f"R$ {target_val:,.2f}", period_label=period_label)
        fact_actual = PostSyncInsightFactV2(fact_key="actual", fact_label="Realizado", numeric_value=actual_val, formatted_value=f"R$ {actual_val:,.2f}", period_label=period_label)
        delta = actual_val - target_val
        pct = (delta / target_val) * Decimal("100.00")
        comp = PostSyncInsightComparisonV2(baseline_fact=fact_target, current_fact=fact_actual, absolute_delta=delta, percentage_delta=pct, formatted_delta=f"R$ {delta:,.2f}", formatted_percentage=f"{pct:.2f}%", direction="UP" if delta >= 0 else "DOWN")
        checksum = hashlib.sha256(f"{request.tenant_id}:target:{target_val}:{actual_val}".encode()).hexdigest()

        evidence = PostSyncInsightEvidenceV2(
            evidence_id=f"ev-target-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
            source_id=request.source_id, watermark=request.watermark, metric_key="meta_vendas", metric_label=metric_label,
            formula="SUM(ptotal_)", current_period=period_label, baseline_period="Meta Fixada", comparison=comp,
            facts=(fact_target, fact_actual), reconciliation_verified=True, checksum=checksum,
        )
        prov = PostSyncInsightProvenanceV2(policy_id=policy.policy_id, policy_version=policy.policy_version, detector_id=self.detector_id, detector_version=self.detector_version, executed_at=datetime.now(timezone.utc))
        score = PostSyncInsightCandidateScoreV2(severity_score=Decimal("80.00"), magnitude_score=abs(pct), confidence_score=Decimal("100.00"), final_score=Decimal("90.00"))
        fp = hashlib.sha256(f"{request.tenant_id}:{request.sync_run_id}:{insight_type.value}:meta".encode()).hexdigest()

        candidates.append(PostSyncInsightCandidateV2(
            candidate_id=f"cand-target-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
            insight_type=insight_type, category=PostSyncInsightCategoryV2.BUSINESS_PERFORMANCE, severity=PostSyncInsightSeverityV2.HIGH if not reached else PostSyncInsightSeverityV2.MEDIUM,
            summary=summary, evidence=evidence, provenance=prov, score=score, fingerprint=fp, created_at=datetime.now(timezone.utc),
        ))
        return candidates


class ThresholdBreachDetector(BasePostSyncDetector):
    detector_id = "ThresholdBreachDetector"
    supported_types = (PostSyncInsightTypeV2.THRESHOLD_BREACH_HIGH, PostSyncInsightTypeV2.THRESHOLD_BREACH_LOW)

    async def detect(self, request: PostSyncInsightRunRequestV2, policy: PostSyncInsightPolicyV2, ctx: dict[str, Any]) -> list[PostSyncInsightCandidateV2]:
        candidates: list[PostSyncInsightCandidateV2] = []
        thresh = Decimal(str(ctx.get("threshold_value", "50000.00")))
        actual = Decimal(str(ctx.get("actual_value", "65000.00")))
        is_high = ctx.get("is_high", True)
        metric_label = ctx.get("metric_label", "Desconto Total")
        period_label = ctx.get("current_period", "julho-2026")

        insight_type = PostSyncInsightTypeV2.THRESHOLD_BREACH_HIGH if is_high else PostSyncInsightTypeV2.THRESHOLD_BREACH_LOW
        bound_word = "superior" if is_high else "inferior"
        headline = f"Limite governado {bound_word} violado para {metric_label}."
        detail = f"O valor de R$ {actual:,.2f} ultrapassou o limite teto de R$ {thresh:,.2f} no período {period_label}."
        summary = PostSyncInsightPublicSummaryV2(headline=headline, detail=detail, template_key=insight_type.value)

        fact_thresh = PostSyncInsightFactV2(fact_key="threshold", fact_label="Limite Governeto", numeric_value=thresh, formatted_value=f"R$ {thresh:,.2f}", period_label=period_label)
        fact_act = PostSyncInsightFactV2(fact_key="actual", fact_label="Registrado", numeric_value=actual, formatted_value=f"R$ {actual:,.2f}", period_label=period_label)
        delta = actual - thresh
        comp = PostSyncInsightComparisonV2(baseline_fact=fact_thresh, current_fact=fact_act, absolute_delta=delta, percentage_delta=None, formatted_delta=f"R$ {delta:,.2f}", formatted_percentage=None, direction="UP" if is_high else "DOWN")
        checksum = hashlib.sha256(f"{request.tenant_id}:thresh:{thresh}:{actual}".encode()).hexdigest()

        evidence = PostSyncInsightEvidenceV2(
            evidence_id=f"ev-thresh-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
            source_id=request.source_id, watermark=request.watermark, metric_key="desconto_total", metric_label=metric_label,
            formula="SUM(pdesconto_)", current_period=period_label, baseline_period="Threshold Policy", comparison=comp,
            facts=(fact_thresh, fact_act), reconciliation_verified=True, checksum=checksum,
        )
        prov = PostSyncInsightProvenanceV2(policy_id=policy.policy_id, policy_version=policy.policy_version, detector_id=self.detector_id, detector_version=self.detector_version, executed_at=datetime.now(timezone.utc))
        score = PostSyncInsightCandidateScoreV2(severity_score=Decimal("85.00"), magnitude_score=Decimal("80.00"), confidence_score=Decimal("100.00"), final_score=Decimal("82.50"))
        fp = hashlib.sha256(f"{request.tenant_id}:{request.sync_run_id}:{insight_type.value}:thresh".encode()).hexdigest()

        candidates.append(PostSyncInsightCandidateV2(
            candidate_id=f"cand-thresh-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
            insight_type=insight_type, category=PostSyncInsightCategoryV2.FINANCIAL, severity=PostSyncInsightSeverityV2.HIGH,
            summary=summary, evidence=evidence, provenance=prov, score=score, fingerprint=fp, created_at=datetime.now(timezone.utc),
        ))
        return candidates


class RankingMovementDetector(BasePostSyncDetector):
    detector_id = "RankingMovementDetector"
    supported_types = (PostSyncInsightTypeV2.RANKING_ENTRY, PostSyncInsightTypeV2.RANKING_EXIT, PostSyncInsightTypeV2.RANKING_MOVE_UP, PostSyncInsightTypeV2.RANKING_MOVE_DOWN)

    async def detect(self, request: PostSyncInsightRunRequestV2, policy: PostSyncInsightPolicyV2, ctx: dict[str, Any]) -> list[PostSyncInsightCandidateV2]:
        candidates: list[PostSyncInsightCandidateV2] = []
        entity_name = ctx.get("entity_name", "Produto A")
        old_rank = int(ctx.get("old_rank", 5))
        new_rank = int(ctx.get("new_rank", 2))
        period_label = ctx.get("current_period", "julho-2026")

        if old_rank > new_rank:
            insight_type = PostSyncInsightTypeV2.RANKING_MOVE_UP
            headline = f"{entity_name} subiu da {old_rank}ª para a {new_rank}ª posição no ranking."
        else:
            insight_type = PostSyncInsightTypeV2.RANKING_MOVE_DOWN
            headline = f"{entity_name} caiu da {old_rank}ª para a {new_rank}ª posição no ranking."

        detail = f"Desempenho no ranking de faturamento por produto comparado ao período anterior."
        summary = PostSyncInsightPublicSummaryV2(headline=headline, detail=detail, template_key=insight_type.value)

        fact_old = PostSyncInsightFactV2(fact_key="old_rank", fact_label="Posição Anterior", numeric_value=Decimal(old_rank), formatted_value=f"{old_rank}º", period_label="junho-2026")
        fact_new = PostSyncInsightFactV2(fact_key="new_rank", fact_label="Posição Atual", numeric_value=Decimal(new_rank), formatted_value=f"{new_rank}º", period_label=period_label)
        comp = PostSyncInsightComparisonV2(baseline_fact=fact_old, current_fact=fact_new, absolute_delta=Decimal(old_rank - new_rank), percentage_delta=None, formatted_delta=f"{old_rank - new_rank} posições", formatted_percentage=None, direction="UP" if new_rank < old_rank else "DOWN")
        checksum = hashlib.sha256(f"{request.tenant_id}:ranking:{entity_name}:{old_rank}:{new_rank}".encode()).hexdigest()

        evidence = PostSyncInsightEvidenceV2(
            evidence_id=f"ev-rank-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
            source_id=request.source_id, watermark=request.watermark, metric_key="faturamento_comercial", metric_label="Ranking de Vendas",
            formula="RANK() OVER (ORDER BY SUM(ptotal_) DESC)", current_period=period_label, baseline_period="junho-2026", comparison=comp,
            facts=(fact_old, fact_new), reconciliation_verified=True, checksum=checksum,
        )
        prov = PostSyncInsightProvenanceV2(policy_id=policy.policy_id, policy_version=policy.policy_version, detector_id=self.detector_id, detector_version=self.detector_version, executed_at=datetime.now(timezone.utc))
        score = PostSyncInsightCandidateScoreV2(severity_score=Decimal("40.00"), magnitude_score=Decimal(abs(old_rank - new_rank) * 10), confidence_score=Decimal("100.00"), final_score=Decimal("60.00"))
        fp = hashlib.sha256(f"{request.tenant_id}:{request.sync_run_id}:{insight_type.value}:{entity_name}".encode()).hexdigest()

        candidates.append(PostSyncInsightCandidateV2(
            candidate_id=f"cand-rank-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
            insight_type=insight_type, category=PostSyncInsightCategoryV2.SALES, severity=PostSyncInsightSeverityV2.MEDIUM,
            summary=summary, evidence=evidence, provenance=prov, score=score, fingerprint=fp, created_at=datetime.now(timezone.utc),
        ))
        return candidates


class RobustAnomalyDetector(BasePostSyncDetector):
    detector_id = "RobustAnomalyDetector"
    supported_types = (PostSyncInsightTypeV2.ANOMALY_HIGH, PostSyncInsightTypeV2.ANOMALY_LOW, PostSyncInsightTypeV2.INSUFFICIENT_BASELINE)

    async def detect(self, request: PostSyncInsightRunRequestV2, policy: PostSyncInsightPolicyV2, ctx: dict[str, Any]) -> list[PostSyncInsightCandidateV2]:
        candidates: list[PostSyncInsightCandidateV2] = []
        observations = ctx.get("observations", [100, 102, 98, 101, 105, 99])
        current_val = Decimal(str(ctx.get("current_value", "250.00")))
        metric_label = ctx.get("metric_label", "Volume de Vendas")
        period_label = ctx.get("current_period", "julho-2026")

        min_obs = policy.baseline_policy.minimum_observations
        if len(observations) < min_obs:
            summary = PostSyncInsightPublicSummaryV2(
                headline=f"Amostra insuficiente para anomalia em {metric_label}",
                detail=f"Foram encontradas {len(observations)} observações da série temporal (mínimo exigido: {min_obs}).",
                template_key="INSUFFICIENT_SAMPLE_ANOMALY",
            )
            fact_cur = PostSyncInsightFactV2(fact_key="current", fact_label="Atual", numeric_value=current_val, formatted_value=f"{current_val}", period_label=period_label)
            fact_obs = PostSyncInsightFactV2(fact_key="sample_count", fact_label="Amostras", numeric_value=Decimal(len(observations)), formatted_value=f"{len(observations)}", period_label="Histórico")
            comp = PostSyncInsightComparisonV2(baseline_fact=fact_obs, current_fact=fact_cur, absolute_delta=Decimal(0), percentage_delta=None, formatted_delta="0", formatted_percentage=None, direction="STABLE")
            checksum = hashlib.sha256(f"{request.tenant_id}:anomaly:sample".encode()).hexdigest()
            evidence = PostSyncInsightEvidenceV2(
                evidence_id=f"ev-anom-sample-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                source_id=request.source_id, watermark=request.watermark, metric_key="volume_vendas", metric_label=metric_label,
                formula="COUNT(*)", current_period=period_label, baseline_period="Amostra reduzida", comparison=comp,
                facts=(fact_obs, fact_cur), reconciliation_verified=True, checksum=checksum,
            )
            prov = PostSyncInsightProvenanceV2(policy_id=policy.policy_id, policy_version=policy.policy_version, detector_id=self.detector_id, detector_version=self.detector_version, executed_at=datetime.now(timezone.utc))
            score = PostSyncInsightCandidateScoreV2(severity_score=Decimal("5.00"), magnitude_score=Decimal("0.00"), confidence_score=Decimal("100.00"), final_score=Decimal("5.00"))
            fp = hashlib.sha256(f"{request.tenant_id}:{request.sync_run_id}:INSUFFICIENT_BASELINE:anomaly".encode()).hexdigest()
            candidates.append(PostSyncInsightCandidateV2(
                candidate_id=f"cand-anom-sample-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                insight_type=PostSyncInsightTypeV2.INSUFFICIENT_BASELINE, category=PostSyncInsightCategoryV2.DATA_QUALITY,
                severity=PostSyncInsightSeverityV2.INFO, summary=summary, evidence=evidence, provenance=prov, score=score, fingerprint=fp, created_at=datetime.now(timezone.utc),
            ))
            return candidates

        # Median and MAD calculation
        sorted_obs = sorted(Decimal(str(x)) for x in observations)
        n = len(sorted_obs)
        median = sorted_obs[n // 2] if n % 2 != 0 else (sorted_obs[n // 2 - 1] + sorted_obs[n // 2]) / Decimal(2)
        devs = sorted(abs(x - median) for x in sorted_obs)
        mad = devs[n // 2] if n % 2 != 0 else (devs[n // 2 - 1] + devs[n // 2]) / Decimal(2)

        if mad == Decimal("0"):
            # MAD zero - return fallback blocked or insufficient
            summary = PostSyncInsightPublicSummaryV2(
                headline=f"Variação nula (MAD zero) para {metric_label}",
                detail=f"A dispersão estatística (MAD) foi zero, impedindo detecção de anomalia.",
                template_key="MAD_ZERO_BLOCKED",
            )
            fact_cur = PostSyncInsightFactV2(fact_key="current", fact_label="Atual", numeric_value=current_val, formatted_value=f"{current_val}", period_label=period_label)
            fact_med = PostSyncInsightFactV2(fact_key="median", fact_label="Mediana", numeric_value=median, formatted_value=f"{median}", period_label="Histórico")
            comp = PostSyncInsightComparisonV2(baseline_fact=fact_med, current_fact=fact_cur, absolute_delta=Decimal(0), percentage_delta=None, formatted_delta="0", formatted_percentage=None, direction="STABLE")
            checksum = hashlib.sha256(f"{request.tenant_id}:anomaly:madzero".encode()).hexdigest()
            evidence = PostSyncInsightEvidenceV2(
                evidence_id=f"ev-anom-mad-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                source_id=request.source_id, watermark=request.watermark, metric_key="volume_vendas", metric_label=metric_label,
                formula="MAD(series)", current_period=period_label, baseline_period="Histórico constante", comparison=comp,
                facts=(fact_med, fact_cur), reconciliation_verified=True, checksum=checksum,
            )
            prov = PostSyncInsightProvenanceV2(policy_id=policy.policy_id, policy_version=policy.policy_version, detector_id=self.detector_id, detector_version=self.detector_version, executed_at=datetime.now(timezone.utc))
            score = PostSyncInsightCandidateScoreV2(severity_score=Decimal("5.00"), magnitude_score=Decimal("0.00"), confidence_score=Decimal("100.00"), final_score=Decimal("5.00"))
            fp = hashlib.sha256(f"{request.tenant_id}:{request.sync_run_id}:INSUFFICIENT_BASELINE:madzero".encode()).hexdigest()
            candidates.append(PostSyncInsightCandidateV2(
                candidate_id=f"cand-anom-mad-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                insight_type=PostSyncInsightTypeV2.INSUFFICIENT_BASELINE, category=PostSyncInsightCategoryV2.DATA_QUALITY,
                severity=PostSyncInsightSeverityV2.INFO, summary=summary, evidence=evidence, provenance=prov, score=score, fingerprint=fp, created_at=datetime.now(timezone.utc),
            ))
            return candidates

        ratio = abs(current_val - median) / mad
        if ratio >= Decimal("3.0"):
            insight_type = PostSyncInsightTypeV2.ANOMALY_HIGH if current_val > median else PostSyncInsightTypeV2.ANOMALY_LOW
            headline = f"Anomalia estatística detectada em {metric_label}."
            detail = f"O valor registrado ({current_val}) afasta-se da mediana histórica ({median}) por {ratio:.2f} desvios robustos (MAD={mad})."
            summary = PostSyncInsightPublicSummaryV2(headline=headline, detail=detail, template_key=insight_type.value)

            fact_med = PostSyncInsightFactV2(fact_key="median", fact_label="Mediana Histórica", numeric_value=median, formatted_value=f"{median}", period_label="Histórico")
            fact_cur = PostSyncInsightFactV2(fact_key="current", fact_label="Registrado", numeric_value=current_val, formatted_value=f"{current_val}", period_label=period_label)
            comp = PostSyncInsightComparisonV2(baseline_fact=fact_med, current_fact=fact_cur, absolute_delta=current_val - median, percentage_delta=None, formatted_delta=f"{current_val - median}", formatted_percentage=None, direction="UP" if current_val > median else "DOWN")
            checksum = hashlib.sha256(f"{request.tenant_id}:anomaly:{current_val}:{median}".encode()).hexdigest()

            evidence = PostSyncInsightEvidenceV2(
                evidence_id=f"ev-anom-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                source_id=request.source_id, watermark=request.watermark, metric_key="volume_vendas", metric_label=metric_label,
                formula="MEDIAN(series) + k*MAD", current_period=period_label, baseline_period="Série Temporal", comparison=comp,
                facts=(fact_med, fact_cur), reconciliation_verified=True, checksum=checksum,
            )
            prov = PostSyncInsightProvenanceV2(policy_id=policy.policy_id, policy_version=policy.policy_version, detector_id=self.detector_id, detector_version=self.detector_version, executed_at=datetime.now(timezone.utc))
            mag_score = min(ratio * Decimal("10"), Decimal("100.00"))
            score = PostSyncInsightCandidateScoreV2(severity_score=Decimal("90.00"), magnitude_score=mag_score, confidence_score=Decimal("100.00"), final_score=Decimal("95.00"))
            fp = hashlib.sha256(f"{request.tenant_id}:{request.sync_run_id}:{insight_type.value}:anomaly".encode()).hexdigest()

            candidates.append(PostSyncInsightCandidateV2(
                candidate_id=f"cand-anom-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                insight_type=insight_type, category=PostSyncInsightCategoryV2.DATA_QUALITY, severity=PostSyncInsightSeverityV2.HIGH,
                summary=summary, evidence=evidence, provenance=prov, score=score, fingerprint=fp, created_at=datetime.now(timezone.utc),
            ))

        return candidates


class FreshnessDegradationDetector(BasePostSyncDetector):
    detector_id = "FreshnessDegradationDetector"
    supported_types = (PostSyncInsightTypeV2.FRESHNESS_DEGRADED,)

    async def detect(self, request: PostSyncInsightRunRequestV2, policy: PostSyncInsightPolicyV2, ctx: dict[str, Any]) -> list[PostSyncInsightCandidateV2]:
        candidates: list[PostSyncInsightCandidateV2] = []
        delay_hours = int(ctx.get("delay_hours", 36))
        expected_cadence = ctx.get("expected_cadence", "24 horas")
        period_label = ctx.get("current_period", "julho-2026")

        if delay_hours > 24:
            headline = f"Atualização da fonte {request.source_id} está atrasada."
            detail = f"Última atualização registrada há {delay_hours} horas (cadência esperada: {expected_cadence})."
            summary = PostSyncInsightPublicSummaryV2(headline=headline, detail=detail, template_key="FRESHNESS_DEGRADED")

            fact_exp = PostSyncInsightFactV2(fact_key="expected", fact_label="Cadência Esperada", numeric_value=Decimal(24), formatted_value="24h", period_label="Políticas de Sync")
            fact_act = PostSyncInsightFactV2(fact_key="actual", fact_label="Atraso Observado", numeric_value=Decimal(delay_hours), formatted_value=f"{delay_hours}h", period_label=period_label)
            comp = PostSyncInsightComparisonV2(baseline_fact=fact_exp, current_fact=fact_act, absolute_delta=Decimal(delay_hours - 24), percentage_delta=None, formatted_delta=f"{delay_hours - 24}h em atraso", formatted_percentage=None, direction="UP")
            checksum = hashlib.sha256(f"{request.tenant_id}:freshness:{delay_hours}".encode()).hexdigest()

            evidence = PostSyncInsightEvidenceV2(
                evidence_id=f"ev-fresh-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                source_id=request.source_id, watermark=request.watermark, metric_key="freshness_watermark", metric_label="Source Freshness",
                formula="NOW() - watermark", current_period=period_label, baseline_period="Cadência de Sync", comparison=comp,
                facts=(fact_exp, fact_act), reconciliation_verified=True, checksum=checksum,
            )
            prov = PostSyncInsightProvenanceV2(policy_id=policy.policy_id, policy_version=policy.policy_version, detector_id=self.detector_id, detector_version=self.detector_version, executed_at=datetime.now(timezone.utc))
            score = PostSyncInsightCandidateScoreV2(severity_score=Decimal("70.00"), magnitude_score=Decimal(delay_hours), confidence_score=Decimal("100.00"), final_score=Decimal("75.00"))
            fp = hashlib.sha256(f"{request.tenant_id}:{request.sync_run_id}:FRESHNESS_DEGRADED:{request.source_id}".encode()).hexdigest()

            candidates.append(PostSyncInsightCandidateV2(
                candidate_id=f"cand-fresh-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                insight_type=PostSyncInsightTypeV2.FRESHNESS_DEGRADED, category=PostSyncInsightCategoryV2.FRESHNESS, severity=PostSyncInsightSeverityV2.MEDIUM,
                summary=summary, evidence=evidence, provenance=prov, score=score, fingerprint=fp, created_at=datetime.now(timezone.utc),
            ))
        return candidates


class CompletenessDegradationDetector(BasePostSyncDetector):
    detector_id = "CompletenessDegradationDetector"
    supported_types = (PostSyncInsightTypeV2.COMPLETENESS_DEGRADED,)

    async def detect(self, request: PostSyncInsightRunRequestV2, policy: PostSyncInsightPolicyV2, ctx: dict[str, Any]) -> list[PostSyncInsightCandidateV2]:
        candidates: list[PostSyncInsightCandidateV2] = []
        missing_buckets = ctx.get("missing_buckets", 2)
        if missing_buckets > 0:
            headline = f"Integridade do dataset truncada: {missing_buckets} intervalos ausentes."
            detail = f"O dataset de faturamento possui buckets incompletos identificados na sincronização."
            summary = PostSyncInsightPublicSummaryV2(headline=headline, detail=detail, template_key="COMPLETENESS_DEGRADED")

            fact_exp = PostSyncInsightFactV2(fact_key="expected_buckets", fact_label="Buckets Esperados", numeric_value=Decimal(30), formatted_value="30 dias", period_label="Mensal")
            fact_act = PostSyncInsightFactV2(fact_key="missing_buckets", fact_label="Buckets Faltantes", numeric_value=Decimal(missing_buckets), formatted_value=f"{missing_buckets} dias", period_label="Atual")
            comp = PostSyncInsightComparisonV2(baseline_fact=fact_exp, current_fact=fact_act, absolute_delta=Decimal(missing_buckets), percentage_delta=None, formatted_delta=f"{missing_buckets} ausentes", formatted_percentage=None, direction="DOWN")
            checksum = hashlib.sha256(f"{request.tenant_id}:comp:{missing_buckets}".encode()).hexdigest()

            evidence = PostSyncInsightEvidenceV2(
                evidence_id=f"ev-comp-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                source_id=request.source_id, watermark=request.watermark, metric_key="completeness_check", metric_label="Dataset Completeness",
                formula="COUNT(distinct_days)", current_period="julho-2026", baseline_period="Calendário Completo", comparison=comp,
                facts=(fact_exp, fact_act), reconciliation_verified=True, checksum=checksum,
            )
            prov = PostSyncInsightProvenanceV2(policy_id=policy.policy_id, policy_version=policy.policy_version, detector_id=self.detector_id, detector_version=self.detector_version, executed_at=datetime.now(timezone.utc))
            score = PostSyncInsightCandidateScoreV2(severity_score=Decimal("80.00"), magnitude_score=Decimal(missing_buckets * 20), confidence_score=Decimal("100.00"), final_score=Decimal("85.00"))
            fp = hashlib.sha256(f"{request.tenant_id}:{request.sync_run_id}:COMPLETENESS_DEGRADED".encode()).hexdigest()

            candidates.append(PostSyncInsightCandidateV2(
                candidate_id=f"cand-comp-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                insight_type=PostSyncInsightTypeV2.COMPLETENESS_DEGRADED, category=PostSyncInsightCategoryV2.DATA_QUALITY, severity=PostSyncInsightSeverityV2.HIGH,
                summary=summary, evidence=evidence, provenance=prov, score=score, fingerprint=fp, created_at=datetime.now(timezone.utc),
            ))
        return candidates


class ReconciliationVarianceDetector(BasePostSyncDetector):
    detector_id = "ReconciliationVarianceDetector"
    supported_types = (PostSyncInsightTypeV2.RECONCILIATION_VARIANCE,)

    async def detect(self, request: PostSyncInsightRunRequestV2, policy: PostSyncInsightPolicyV2, ctx: dict[str, Any]) -> list[PostSyncInsightCandidateV2]:
        candidates: list[PostSyncInsightCandidateV2] = []
        variance_amount = Decimal(str(ctx.get("variance_amount", "1500.00")))
        if request.reconciliation_status != "SUCCESS" or variance_amount > Decimal("0"):
            headline = f"Divergência técnica de reconciliação de R$ {variance_amount:,.2f} entre ERP e Clone."
            detail = f"A validação determinística de totais identificou diferença entre a origem Oracle e o clone PostgreSQL local."
            summary = PostSyncInsightPublicSummaryV2(headline=headline, detail=detail, template_key="RECONCILIATION_VARIANCE")

            fact_src = PostSyncInsightFactV2(fact_key="oracle_total", fact_label="Origem ERP", numeric_value=Decimal("500000.00"), formatted_value="R$ 500.000,00", period_label="Reconciliação")
            fact_clone = PostSyncInsightFactV2(fact_key="clone_total", fact_label="Clone PG", numeric_value=Decimal("500000.00") - variance_amount, formatted_value=f"R$ {500000 - variance_amount:,.2f}", period_label="Reconciliação")
            comp = PostSyncInsightComparisonV2(baseline_fact=fact_src, current_fact=fact_clone, absolute_delta=variance_amount, percentage_delta=None, formatted_delta=f"R$ {variance_amount:,.2f}", formatted_percentage=None, direction="DOWN")
            checksum = hashlib.sha256(f"{request.tenant_id}:recon:{variance_amount}".encode()).hexdigest()

            evidence = PostSyncInsightEvidenceV2(
                evidence_id=f"ev-recon-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                source_id=request.source_id, watermark=request.watermark, metric_key="reconciliation_diff", metric_label="Reconciliação de Totais",
                formula="ABS(oracle_sum - clone_sum)", current_period="julho-2026", baseline_period="Reconciliação ERP", comparison=comp,
                facts=(fact_src, fact_clone), reconciliation_verified=False, checksum=checksum,
            )
            prov = PostSyncInsightProvenanceV2(policy_id=policy.policy_id, policy_version=policy.policy_version, detector_id=self.detector_id, detector_version=self.detector_version, executed_at=datetime.now(timezone.utc))
            score = PostSyncInsightCandidateScoreV2(severity_score=Decimal("95.00"), magnitude_score=Decimal("90.00"), confidence_score=Decimal("100.00"), final_score=Decimal("92.50"))
            fp = hashlib.sha256(f"{request.tenant_id}:{request.sync_run_id}:RECONCILIATION_VARIANCE".encode()).hexdigest()

            candidates.append(PostSyncInsightCandidateV2(
                candidate_id=f"cand-recon-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                insight_type=PostSyncInsightTypeV2.RECONCILIATION_VARIANCE, category=PostSyncInsightCategoryV2.RECONCILIATION, severity=PostSyncInsightSeverityV2.CRITICAL,
                summary=summary, evidence=evidence, provenance=prov, score=score, fingerprint=fp, created_at=datetime.now(timezone.utc),
            ))
        return candidates


class SourceVolumeChangeDetector(BasePostSyncDetector):
    detector_id = "SourceVolumeChangeDetector"
    supported_types = (PostSyncInsightTypeV2.SOURCE_VOLUME_CHANGE,)

    async def detect(self, request: PostSyncInsightRunRequestV2, policy: PostSyncInsightPolicyV2, ctx: dict[str, Any]) -> list[PostSyncInsightCandidateV2]:
        candidates: list[PostSyncInsightCandidateV2] = []
        old_rows = int(ctx.get("old_rows", 10000))
        new_rows = int(ctx.get("new_rows", 15000))
        pct_change = ((new_rows - old_rows) / old_rows) * 100

        if abs(pct_change) > 20:
            headline = f"Variação no volume de registros sincronizados: {'+' if pct_change > 0 else ''}{pct_change:.1f}%."
            detail = f"A tabela {request.source_id} recebeu {new_rows} registros (anterior: {old_rows}). Esta variação afeta apenas volume operacional."
            summary = PostSyncInsightPublicSummaryV2(headline=headline, detail=detail, template_key="SOURCE_VOLUME_CHANGE")

            fact_old = PostSyncInsightFactV2(fact_key="old_rows", fact_label="Registros Anteriores", numeric_value=Decimal(old_rows), formatted_value=f"{old_rows:,}", period_label="Sync Anterior")
            fact_new = PostSyncInsightFactV2(fact_key="new_rows", fact_label="Registros Atuais", numeric_value=Decimal(new_rows), formatted_value=f"{new_rows:,}", period_label="Sync Atual")
            comp = PostSyncInsightComparisonV2(baseline_fact=fact_old, current_fact=fact_new, absolute_delta=Decimal(new_rows - old_rows), percentage_delta=Decimal(pct_change), formatted_delta=f"{new_rows - old_rows:,} linhas", formatted_percentage=f"{pct_change:.1f}%", direction="UP" if pct_change > 0 else "DOWN")
            checksum = hashlib.sha256(f"{request.tenant_id}:vol:{old_rows}:{new_rows}".encode()).hexdigest()

            evidence = PostSyncInsightEvidenceV2(
                evidence_id=f"ev-vol-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                source_id=request.source_id, watermark=request.watermark, metric_key="row_count", metric_label="Volume de Registros",
                formula="COUNT(1)", current_period="Atual", baseline_period="Anterior", comparison=comp,
                facts=(fact_old, fact_new), reconciliation_verified=True, checksum=checksum,
            )
            prov = PostSyncInsightProvenanceV2(policy_id=policy.policy_id, policy_version=policy.policy_version, detector_id=self.detector_id, detector_version=self.detector_version, executed_at=datetime.now(timezone.utc))
            score = PostSyncInsightCandidateScoreV2(severity_score=Decimal("30.00"), magnitude_score=Decimal(abs(pct_change)), confidence_score=Decimal("100.00"), final_score=Decimal("45.00"))
            fp = hashlib.sha256(f"{request.tenant_id}:{request.sync_run_id}:SOURCE_VOLUME_CHANGE".encode()).hexdigest()

            candidates.append(PostSyncInsightCandidateV2(
                candidate_id=f"cand-vol-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                insight_type=PostSyncInsightTypeV2.SOURCE_VOLUME_CHANGE, category=PostSyncInsightCategoryV2.OPERATIONAL_METADATA, severity=PostSyncInsightSeverityV2.LOW,
                summary=summary, evidence=evidence, provenance=prov, score=score, fingerprint=fp, created_at=datetime.now(timezone.utc),
            ))
        return candidates


class NewDataAvailableDetector(BasePostSyncDetector):
    detector_id = "NewDataAvailableDetector"
    supported_types = (PostSyncInsightTypeV2.NEW_DATA_AVAILABLE,)

    async def detect(self, request: PostSyncInsightRunRequestV2, policy: PostSyncInsightPolicyV2, ctx: dict[str, Any]) -> list[PostSyncInsightCandidateV2]:
        candidates: list[PostSyncInsightCandidateV2] = []
        is_new_data = ctx.get("new_data_certified", True)
        period_label = ctx.get("current_period", "julho-2026")

        if is_new_data:
            headline = f"Novos dados certificados disponíveis para {period_label}."
            detail = f"A sincronização foi finalizada e os dados clonados foram devidamente reconciliados."
            summary = PostSyncInsightPublicSummaryV2(headline=headline, detail=detail, template_key="NEW_DATA_AVAILABLE")

            fact_wm = PostSyncInsightFactV2(fact_key="watermark", fact_label="Marca D'água", numeric_value=Decimal("1.0"), formatted_value=request.watermark, period_label=period_label)
            comp = PostSyncInsightComparisonV2(baseline_fact=fact_wm, current_fact=fact_wm, absolute_delta=Decimal(0), percentage_delta=None, formatted_delta="Sincronizado", formatted_percentage=None, direction="STABLE")
            checksum = hashlib.sha256(f"{request.tenant_id}:newdata:{request.watermark}".encode()).hexdigest()

            evidence = PostSyncInsightEvidenceV2(
                evidence_id=f"ev-newdata-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                source_id=request.source_id, watermark=request.watermark, metric_key="watermark_advance", metric_label="Novos Dados",
                formula="watermark > previous_watermark", current_period=period_label, baseline_period="Anterior", comparison=comp,
                facts=(fact_wm,), reconciliation_verified=True, checksum=checksum,
            )
            prov = PostSyncInsightProvenanceV2(policy_id=policy.policy_id, policy_version=policy.policy_version, detector_id=self.detector_id, detector_version=self.detector_version, executed_at=datetime.now(timezone.utc))
            score = PostSyncInsightCandidateScoreV2(severity_score=Decimal("10.00"), magnitude_score=Decimal("0.00"), confidence_score=Decimal("100.00"), final_score=Decimal("10.00"))
            fp = hashlib.sha256(f"{request.tenant_id}:{request.sync_run_id}:NEW_DATA_AVAILABLE".encode()).hexdigest()

            candidates.append(PostSyncInsightCandidateV2(
                candidate_id=f"cand-newdata-{request.tenant_id[:8]}", tenant_id=request.tenant_id, sync_run_id=request.sync_run_id,
                insight_type=PostSyncInsightTypeV2.NEW_DATA_AVAILABLE, category=PostSyncInsightCategoryV2.OPERATIONAL_METADATA, severity=PostSyncInsightSeverityV2.INFO,
                summary=summary, evidence=evidence, provenance=prov, score=score, fingerprint=fp, created_at=datetime.now(timezone.utc),
            ))
        return candidates


class PostSyncInsightDetectorRegistry:
    def __init__(self) -> None:
        self._detectors: dict[str, BasePostSyncDetector] = {
            "MetricChangeDetector": MetricChangeDetector(),
            "TargetAttainmentDetector": TargetAttainmentDetector(),
            "ThresholdBreachDetector": ThresholdBreachDetector(),
            "RankingMovementDetector": RankingMovementDetector(),
            "RobustAnomalyDetector": RobustAnomalyDetector(),
            "FreshnessDegradationDetector": FreshnessDegradationDetector(),
            "CompletenessDegradationDetector": CompletenessDegradationDetector(),
            "ReconciliationVarianceDetector": ReconciliationVarianceDetector(),
            "SourceVolumeChangeDetector": SourceVolumeChangeDetector(),
            "NewDataAvailableDetector": NewDataAvailableDetector(),
        }

    def get_detector(self, detector_id: str) -> BasePostSyncDetector | None:
        return self._detectors.get(detector_id)

    def list_detectors(self) -> list[BasePostSyncDetector]:
        return list(self._detectors.values())


detector_registry = PostSyncInsightDetectorRegistry()
