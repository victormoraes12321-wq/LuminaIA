"""
LuminaAI — Package Version Manager
-------------------------------------
Controla o versionamento e a evolução dos Analytical Packages.

Responsabilidades:
- Criar nova versão quando o blueprint-fonte é atualizado
- Manter histórico de versões (via snapshots)
- Deprecar versões antigas automaticamente
- Verificar retrocompatibilidade entre versões
- Detectar breaking changes que exigem novo Package

FILOSOFIA: Um Package não é deletado quando evolui — ele é versionado.
O Package anterior é marcado como DEPRECATED, e um novo Package
ACTIVE é criado com a versão incrementada. O histórico é preservado.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.analytical_package import AnalyticalPackage, PackageStatus

logger = logging.getLogger("luminaai.data_platform.package_version_manager")


class PackageVersionManager:
    """
    Gerencia o ciclo de versões dos Analytical Packages.
    """

    async def bump_version(
        self,
        package: AnalyticalPackage,
        reason: str,
        new_blueprint_snapshot: dict[str, Any],
        db: AsyncSession,
    ) -> AnalyticalPackage:
        """
        Cria uma nova versão de um Package existente.

        Fluxo:
          1. Depreca o Package atual com o motivo fornecido.
          2. Cria um novo Package com versão incrementada.
          3. Copia fingerprint, contexto e estratégias do Package atual.
          4. Atualiza o blueprint_snapshot com a nova versão.

        Parâmetros:
            package               — Package a ser versionado
            reason                — Motivo da nova versão (para auditoria)
            new_blueprint_snapshot — Blueprint atualizado
            db                    — Sessão de banco de dados

        Retorna:
            Novo AnalyticalPackage ACTIVE com versão incrementada.
        """
        # 1. Depreca o Package atual
        package.status = PackageStatus.DEPRECATED
        package.deprecation_reason = reason
        db.add(package)

        # 2. Cria novo Package com versão incrementada
        new_package = AnalyticalPackage(
            tenant_id=package.tenant_id,
            intent_fingerprint=dict(package.intent_fingerprint or {}),
            intent_key=package.intent_key,
            semantic_context=dict(package.semantic_context or {}),
            visual_strategy=dict(package.visual_strategy or {}),
            interaction_strategy=dict(package.interaction_strategy or {}),
            analytical_structure=dict(package.analytical_structure or {}),
            blueprint_id=package.blueprint_id,
            blueprint_snapshot=new_blueprint_snapshot,
            view_names=list(package.view_names or []),
            status=PackageStatus.ACTIVE,
            version=package.version + 1,
            quality_score=package.quality_score,
            health_score=1.0,  # Reset health score na nova versão
            usage_count=0,     # Reset usage count na nova versão
            dependencies=dict(package.dependencies or {}),
            compatible_fingerprints=list(package.compatible_fingerprints or []),
            created_by="AI_PIPELINE",
        )

        db.add(new_package)

        logger.info(
            "[PackageVersionManager] Nova versão criada | pkg=%s v%d → v%d | motivo=%s",
            package.id, package.version, new_package.version, reason,
        )

        return new_package

    async def get_version_history(
        self,
        intent_key: str,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        """
        Retorna o histórico de versões de um Package identificado pelo intent_key.

        Inclui Packages ACTIVE, DEPRECATED e ARCHIVED com o mesmo intent_key.
        """
        stmt = select(AnalyticalPackage).where(
            and_(
                AnalyticalPackage.tenant_id == tenant_id,
                AnalyticalPackage.intent_key == intent_key,
            )
        ).order_by(AnalyticalPackage.version.asc())

        result = await db.execute(stmt)
        packages = result.scalars().all()

        history = []
        for pkg in packages:
            history.append({
                "id": str(pkg.id),
                "version": pkg.version,
                "status": pkg.status.value,
                "quality_score": pkg.quality_score,
                "health_score": pkg.health_score,
                "usage_count": pkg.usage_count,
                "blueprint_id": pkg.blueprint_id,
                "deprecation_reason": pkg.deprecation_reason,
                "criado_em": pkg.criado_em.isoformat() if pkg.criado_em else None,
            })

        return history

    def detect_breaking_changes(
        self,
        old_blueprint: dict[str, Any],
        new_blueprint: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """
        Detecta breaking changes entre duas versões de um blueprint.

        Um breaking change exige nova versão do Package. Mudanças não-breaking
        (ex: adição de nova métrica opcional) apenas atualizam o snapshot.

        Retorna:
            (has_breaking_changes, list_of_changes)
        """
        changes = []

        # Verifica mudança de view_name (breaking — fonte de dados diferente)
        old_view = old_blueprint.get("view_name", "")
        new_view = new_blueprint.get("view_name", "")
        if old_view != new_view:
            changes.append(f"view_name alterado: {old_view!r} → {new_view!r}")

        # Verifica remoção de métricas obrigatórias (breaking)
        old_metrics = set(old_blueprint.get("metrics", []))
        new_metrics = set(new_blueprint.get("metrics", []))
        removed = old_metrics - new_metrics
        if removed:
            changes.append(f"métricas removidas: {sorted(removed)}")

        # Verifica mudança de tipo de análise (breaking)
        old_type = old_blueprint.get("tipo_analise", "")
        new_type = new_blueprint.get("tipo_analise", "")
        if old_type and new_type and old_type != new_type:
            changes.append(f"tipo_analise alterado: {old_type!r} → {new_type!r}")

        # Verifica remoção de group_by estrutural (breaking)
        old_gb = set(old_blueprint.get("group_by", []))
        new_gb = set(new_blueprint.get("group_by", []))
        removed_gb = old_gb - new_gb
        if removed_gb:
            changes.append(f"group_by removidos: {sorted(removed_gb)}")

        has_breaking = len(changes) > 0

        if has_breaking:
            logger.warning(
                "[PackageVersionManager] Breaking changes detectados: %s",
                "; ".join(changes),
            )

        return has_breaking, changes

    async def deprecate_packages_by_view(
        self,
        view_name: str,
        tenant_id: uuid.UUID,
        reason: str,
        db: AsyncSession,
    ) -> int:
        """
        Depreca todos os Packages ACTIVE que dependem de uma view específica.

        Usado pelo Sync Engine quando detecta mudança de schema em uma view.
        Retorna o número de Packages deprecados.
        """
        stmt = select(AnalyticalPackage).where(
            and_(
                AnalyticalPackage.tenant_id == tenant_id,
                AnalyticalPackage.status == PackageStatus.ACTIVE,
                AnalyticalPackage.view_names.contains([view_name]),
            )
        )

        result = await db.execute(stmt)
        packages = result.scalars().all()

        count = 0
        for pkg in packages:
            pkg.status = PackageStatus.DEPRECATED
            pkg.deprecation_reason = reason
            db.add(pkg)
            count += 1

        if count > 0:
            logger.warning(
                "[PackageVersionManager] %d Packages deprecados por mudança na view %r | motivo=%s",
                count, view_name, reason,
            )

        return count


# ── Singleton ─────────────────────────────────────────────────────────────────
package_version_manager = PackageVersionManager()
