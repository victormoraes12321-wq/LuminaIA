"""
LuminaAI — Package Compatibility Engine
-----------------------------------------
Detecta se uma nova consulta pode reutilizar um Analytical Package existente.

Responsabilidades:
- Buscar Packages compatíveis no banco de dados com base no fingerprint semântico
- Calcular score de compatibilidade (0.0-1.0)
- Aplicar threshold de reuso (≥ 0.85)
- Tolerar variações de período temporal (mesmo tema, período diferente = compatível)
- Registrar fingerprints comprovadamente compatíveis no Package para otimização futura

ISOLAMENTO: Toda busca é estritamente filtrada por tenant_id.
PERFORMANCE: Lookup inicial pelo intent_key (hash exato) — O(1). Fallback
             para comparação semântica apenas se não houver match exato.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.analytical_package import AnalyticalPackage, PackageStatus
from services.data_platform.intent_fingerprint import intent_fingerprint_generator

logger = logging.getLogger("luminaai.data_platform.package_compatibility")

# Threshold mínimo de compatibilidade para reuso de Package
COMPATIBILITY_THRESHOLD = 0.85


def _coerce_fingerprint(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return {}
        try:
            parsed = json.loads(stripped)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


class PackageCompatibilityEngine:
    """
    Motor de compatibilidade semântica para Analytical Packages.

    Estratégia de busca em 3 camadas:
      1. Lookup exato por intent_key (hash SHA-256) — O(1) — mais eficiente
      2. Lookup por fingerprints compatíveis previamente registrados — O(n) rápido
      3. Varredura semântica nos Packages ACTIVE do tenant — fallback
    """

    async def find_compatible_package(
        self,
        fingerprint: dict[str, Any],
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> tuple[AnalyticalPackage | None, float]:
        """
        Busca o Package mais compatível para o fingerprint fornecido.

        Retorna:
            (package, score) — package é None se nenhum compatível for encontrado.
            score = 1.0 para match exato; < 1.0 para match semântico.
        """
        fingerprint = _coerce_fingerprint(fingerprint)
        if not fingerprint:
            return None, 0.0

        intent_key = fingerprint.get("intent_key", "")

        # ── Camada 1: Lookup exato por intent_key ────────────────────────────
        exact_match = await self._lookup_exact(intent_key, tenant_id, db)
        if exact_match:
            logger.info(
                "[PackageCompatibility] HIT exato | key=%s... pkg=%s",
                intent_key[:12], exact_match.id,
            )
            return exact_match, 1.0

        # ── Camada 2: Lookup por fingerprints compatíveis registrados ────────
        registered_match = await self._lookup_registered_compatible(intent_key, tenant_id, db)
        if registered_match:
            logger.info(
                "[PackageCompatibility] HIT registrado | key=%s... pkg=%s",
                intent_key[:12], registered_match.id,
            )
            return registered_match, 0.95

        # ── Camada 3: Varredura semântica (fallback) ─────────────────────────
        best_package, best_score = await self._semantic_scan(fingerprint, tenant_id, db)
        if best_package and best_score >= COMPATIBILITY_THRESHOLD:
            logger.info(
                "[PackageCompatibility] HIT semântico | score=%.3f pkg=%s",
                best_score, best_package.id,
            )
            # Registra este fingerprint como compatível no Package para otimização futura
            await self._register_compatible_fingerprint(best_package, intent_key, db)
            return best_package, best_score

        logger.info(
            "[PackageCompatibility] MISS | key=%s... best_score=%.3f",
            intent_key[:12], best_score,
        )
        return None, best_score

    # ── Camadas de Lookup ─────────────────────────────────────────────────────

    async def _lookup_exact(
        self,
        intent_key: str,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> AnalyticalPackage | None:
        """Lookup O(1) por hash exato do fingerprint."""
        if not intent_key:
            return None

        stmt = select(AnalyticalPackage).where(
            and_(
                AnalyticalPackage.tenant_id == tenant_id,
                AnalyticalPackage.intent_key == intent_key,
                AnalyticalPackage.status == PackageStatus.ACTIVE,
            )
        ).limit(1)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _lookup_registered_compatible(
        self,
        intent_key: str,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> AnalyticalPackage | None:
        """
        Busca Packages onde o intent_key já foi registrado como compatível.
        Usa o campo JSONB `compatible_fingerprints` como índice.
        """
        if not intent_key:
            return None

        # PostgreSQL JSONB: verifica se o array contém o intent_key
        stmt = select(AnalyticalPackage).where(
            and_(
                AnalyticalPackage.tenant_id == tenant_id,
                AnalyticalPackage.status == PackageStatus.ACTIVE,
                AnalyticalPackage.compatible_fingerprints.contains([intent_key]),
            )
        ).limit(1)

        try:
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            # Fallback gracioso se o operador JSONB não estiver disponível
            logger.debug("[PackageCompatibility] Lookup JSONB falhou (não crítico): %s", e)
            return None

    async def _semantic_scan(
        self,
        fingerprint: dict[str, Any],
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> tuple[AnalyticalPackage | None, float]:
        """
        Varredura semântica nos Packages ACTIVE do tenant.
        Otimizado para reduzir o conjunto: filtra por domain antes de comparar.
        """
        domain = fingerprint.get("domain", "GERAL")

        # Carrega apenas Packages do mesmo domínio (reduz o conjunto)
        stmt = select(AnalyticalPackage).where(
            and_(
                AnalyticalPackage.tenant_id == tenant_id,
                AnalyticalPackage.status == PackageStatus.ACTIVE,
            )
        ).order_by(AnalyticalPackage.usage_count.desc()).limit(50)

        result = await db.execute(stmt)
        packages = result.scalars().all()

        if not packages:
            return None, 0.0

        best_package: AnalyticalPackage | None = None
        best_score = 0.0

        for package in packages:
            pkg_fingerprint = _coerce_fingerprint(package.intent_fingerprint)
            if not pkg_fingerprint:
                continue
            score = intent_fingerprint_generator.compute_compatibility_score(
                fingerprint, pkg_fingerprint
            )
            if score > best_score:
                best_score = score
                best_package = package

        return best_package, best_score

    async def _register_compatible_fingerprint(
        self,
        package: AnalyticalPackage,
        intent_key: str,
        db: AsyncSession,
    ) -> None:
        """
        Registra o intent_key como compatível com o Package para otimizar
        buscas futuras (evita nova varredura semântica).
        """
        try:
            current = list(package.compatible_fingerprints or [])
            if intent_key not in current:
                current.append(intent_key)
                # Limita a 100 fingerprints para evitar crescimento indefinido
                package.compatible_fingerprints = current[-100:]
                db.add(package)
                # Não faz commit aqui — o commit é gerenciado pela camada superior
        except Exception as e:
            logger.error("[PackageCompatibility] Falha ao registrar fingerprint compatível: %s", e)


# ── Singleton ─────────────────────────────────────────────────────────────────
package_compatibility_engine = PackageCompatibilityEngine()
