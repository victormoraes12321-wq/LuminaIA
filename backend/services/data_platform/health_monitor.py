"""
Health Monitor — LuminaAI Data Platform
-----------------------------------------
Calcula automaticamente os 5 scores de saúde para qualquer estrutura registrada
no Metadata Catalog e gera alertas quando qualquer score cai abaixo do limiar.

Scores (0–100):
  health_score      = média ponderada dos demais
  integrity_score   = baseado em hash, status e integridade
  performance_score = baseado em tempo_medio_execucao vs limiar
  freshness_score   = baseado em ultima_sincronizacao vs proxima_sincronizacao
  usage_score       = baseado em quantidade_consultas e quantidade_usuarios
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select
from models.metadata_catalog import MetadataCatalog
from database import get_db_context

logger = logging.getLogger("luminaai.data_platform.health_monitor")

# Limiares configuráveis (padrão corporativo)
HEALTH_ALERT_THRESHOLD = 70.0
PERFORMANCE_MAX_MS = 5000.0       # Acima de 5s = score 0
FRESHNESS_MAX_HOURS = 48.0        # Sem sync há 48h = score 0
USAGE_BENCHMARK_QUERIES = 1000.0  # 1000 consultas = score 100


class HealthMonitor:
    """
    Monitor de saúde das estruturas da Data Platform.
    Calcula scores contínuos e gera alertas automáticos.
    """

    # ── Score calculators ──────────────────────────────────────────────────

    def calc_integrity_score(self, meta: MetadataCatalog) -> float:
        """Calcula o Integrity Score baseado em status e integridade da estrutura."""
        score = 100.0
        if meta.integridade == "corrupted":
            score -= 60.0
        elif meta.integridade == "degraded":
            score -= 30.0
        if meta.status in ("error", "failed"):
            score -= 30.0
        elif meta.status in ("warning", "reconstructed"):
            score -= 10.0
        return max(0.0, score)

    def calc_performance_score(self, meta: MetadataCatalog) -> float:
        """Calcula o Performance Score baseado no tempo médio de execução."""
        t = float(meta.tempo_medio_execucao or 0.0)
        if t <= 0:
            return 100.0
        if t >= PERFORMANCE_MAX_MS:
            return 0.0
        return round(100.0 * (1.0 - t / PERFORMANCE_MAX_MS), 2)

    def calc_freshness_score(self, meta: MetadataCatalog) -> float:
        """Calcula o Freshness Score baseado na idade da última sincronização."""
        if not meta.ultima_sincronizacao:
            return 50.0  # Nunca sincronizou = score neutro
        now = datetime.now(timezone.utc)
        # Garante que ultima_sincronizacao tem timezone
        last = meta.ultima_sincronizacao
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        hours_since = (now - last).total_seconds() / 3600.0
        if hours_since >= FRESHNESS_MAX_HOURS:
            return 0.0
        return round(100.0 * (1.0 - hours_since / FRESHNESS_MAX_HOURS), 2)

    def calc_usage_score(self, meta: MetadataCatalog) -> float:
        """Calcula o Usage Score baseado na quantidade de consultas e usuários."""
        consultas = float(meta.quantidade_consultas or 0)
        usuarios = float(meta.quantidade_usuarios or 0)
        score = min(100.0, (consultas / USAGE_BENCHMARK_QUERIES) * 80.0)
        score += min(20.0, usuarios * 2.0)
        return round(score, 2)

    def calc_health_score(
        self,
        integrity: float,
        performance: float,
        freshness: float,
        usage: float,
    ) -> float:
        """Calcula o Health Score como média ponderada dos demais scores."""
        return round(
            integrity * 0.35
            + performance * 0.30
            + freshness * 0.25
            + usage * 0.10,
            2,
        )

    def generate_alerts(
        self,
        estrutura_id: str,
        scores: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Gera alertas para scores abaixo do limiar configurado."""
        alerts = []
        labels = {
            "integrity_score": "Integridade",
            "performance_score": "Performance",
            "freshness_score": "Atualização",
            "usage_score": "Utilização",
            "health_score": "Saúde Geral",
        }
        for key, value in scores.items():
            if key == "usage_score":
                continue  # usage_score baixo não é alerta — estrutura nova
            if value < HEALTH_ALERT_THRESHOLD:
                alerts.append({
                    "tipo": key.upper(),
                    "estrutura_id": estrutura_id,
                    "score": value,
                    "limiar": HEALTH_ALERT_THRESHOLD,
                    "descricao": (
                        f"Score de {labels.get(key, key)} está em {value:.1f}/100, "
                        f"abaixo do limiar de {HEALTH_ALERT_THRESHOLD:.0f}."
                    ),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        return alerts

    # ── Compute & persist ──────────────────────────────────────────────────

    async def compute_and_update(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> dict[str, float]:
        """
        Calcula todos os scores de saúde da estrutura e persiste no Metadata Catalog.
        Retorna o dicionário de scores calculados.
        """
        async with get_db_context() as session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res = await session.execute(stmt)
            meta = res.scalar_one_or_none()

            if not meta:
                logger.warning(
                    "[HealthMonitor] Estrutura não encontrada para cálculo: %s", estrutura_id
                )
                return {}

            integrity = self.calc_integrity_score(meta)
            performance = self.calc_performance_score(meta)
            freshness = self.calc_freshness_score(meta)
            usage = self.calc_usage_score(meta)
            health = self.calc_health_score(integrity, performance, freshness, usage)

            scores = {
                "integrity_score": integrity,
                "performance_score": performance,
                "freshness_score": freshness,
                "usage_score": usage,
                "health_score": health,
            }

            alerts = self.generate_alerts(estrutura_id, scores)

            meta.integrity_score = integrity
            meta.performance_score = performance
            meta.freshness_score = freshness
            meta.usage_score = usage
            meta.health_score = health
            meta.alertas = alerts

            session.add(meta)
            await session.commit()

            if alerts:
                logger.warning(
                    "[HealthMonitor] %d alerta(s) gerado(s) para estrutura %s | health=%.1f",
                    len(alerts),
                    estrutura_id,
                    health,
                )
            else:
                logger.debug(
                    "[HealthMonitor] Scores atualizados | %s | health=%.1f",
                    estrutura_id,
                    health,
                )

            return scores

    async def get_tenant_health_report(
        self,
        tenant_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Relatório consolidado de saúde de todo o tenant.
        Retorna totais por tipo, score médio, contagem de alertas ativos.
        """
        async with get_db_context() as session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
            )
            res = await session.execute(stmt)
            entities = res.scalars().all()

        if not entities:
            return {"total": 0, "alertas_ativos": 0, "health_medio": 100.0, "por_tipo": {}}

        total_alertas = sum(len(e.alertas or []) for e in entities)
        health_medio = sum(float(e.health_score or 100.0) for e in entities) / len(entities)

        por_tipo: dict[str, dict] = {}
        for e in entities:
            t = e.tipo_estrutura
            if t not in por_tipo:
                por_tipo[t] = {"total": 0, "alertas": 0, "health_medio": 0.0, "_sum": 0.0}
            por_tipo[t]["total"] += 1
            por_tipo[t]["alertas"] += len(e.alertas or [])
            por_tipo[t]["_sum"] += float(e.health_score or 100.0)

        for tipo_data in por_tipo.values():
            tipo_data["health_medio"] = round(tipo_data["_sum"] / tipo_data["total"], 2)
            del tipo_data["_sum"]

        return {
            "total": len(entities),
            "alertas_ativos": total_alertas,
            "health_medio": round(health_medio, 2),
            "por_tipo": por_tipo,
        }


# Singleton export
health_monitor = HealthMonitor()
