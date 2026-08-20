import logging
import uuid
import json
from datetime import datetime
from typing import Any, Final
from sqlalchemy import select, and_, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.svr import SVRConcept, SVRVersion, SVRCompatibilityMatrix, SVRAuditLog

logger = logging.getLogger("luminaai.services.svr")

class SemanticVersionRegistryService:
    """
    Serviço central de Governança do Semantic Version Registry (SVR).
    Gerencia o ciclo de vida e a resolução de versões semânticas, físicas e de blueprints.
    """

    async def resolve_concept(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        concept_id: str,
        semantic_version: str | None = None,
        mapping_version: str | None = None,
        blueprint_version: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Resolve a definição / snapshot de um conceito corporativo para as versões informadas.
        Se nenhuma versão for informada, busca a versão com status 'ACTIVE' na matriz de compatibilidade.
        Auto-inicializa mapeamentos padrões (bootstrap) para retrocompatibilidade.
        """
        try:
            # 1. Se nenhuma versão for fornecida, busca na Matriz de Compatibilidade a versão ACTIVE
            if not semantic_version and not mapping_version and not blueprint_version:
                stmt = select(SVRCompatibilityMatrix).where(
                    and_(
                        SVRCompatibilityMatrix.tenant_id == tenant_id,
                        SVRCompatibilityMatrix.concept_id == concept_id,
                        SVRCompatibilityMatrix.status == "ACTIVE"
                    )
                ).limit(1)
                res = await db.execute(stmt)
                matrix = res.scalar_one_or_none()
                if matrix:
                    semantic_version = matrix.semantic_version
                    mapping_version = matrix.mapping_version
                    blueprint_version = matrix.blueprint_version
                else:
                    # Matriz vazia -> auto-inicializa (bootstrap)
                    await self._bootstrap_default_concept(db, tenant_id, concept_id)
                    semantic_version = "1.0"
                    mapping_version = "1"
                    blueprint_version = None

            # 2. Busca a snapshot na tabela de SVRVersion
            conditions = [
                SVRVersion.tenant_id == tenant_id,
                SVRVersion.concept_id == concept_id,
                SVRVersion.semantic_version == (semantic_version or "1.0"),
                SVRVersion.mapping_version == (mapping_version or "1")
            ]
            if blueprint_version:
                conditions.append(SVRVersion.blueprint_version == blueprint_version)

            stmt_v = select(SVRVersion).where(and_(*conditions)).limit(1)
            res_v = await db.execute(stmt_v)
            version_record = res_v.scalar_one_or_none()

            if version_record:
                snap = version_record.snapshot
                if isinstance(snap, str):
                    snap = json.loads(snap)
                return snap

            # Se não encontrou snapshot mas tentou buscar por padrão, cria o bootstrap
            if semantic_version == "1.0" and mapping_version == "1":
                snap = await self._bootstrap_default_concept(db, tenant_id, concept_id)
                return snap

            return None
        except Exception as exc:
            logger.error("[SVR] Erro ao resolver conceito %s: %s", concept_id, exc)
            return None

    async def register_concept_version(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        concept_id: str,
        concept_type: str,
        semantic_version: str,
        mapping_version: str,
        snapshot: dict[str, Any],
        autor: str = "SYSTEM",
        motivo: str | None = None,
        impacto: str | None = None,
        blueprint_version: str | None = None,
    ) -> SVRVersion:
        """
        Registra uma nova versão imutável de um conceito corporativo.
        Atualiza a Matriz de Compatibilidade e grava logs de auditoria.
        """
        # Garante que o SVRConcept existe
        stmt_c = select(SVRConcept).where(
            and_(
                SVRConcept.tenant_id == tenant_id,
                SVRConcept.concept_id == concept_id
            )
        ).limit(1)
        res_c = await db.execute(stmt_c)
        concept = res_c.scalar_one_or_none()
        if not concept:
            concept = SVRConcept(
                tenant_id=tenant_id,
                concept_id=concept_id,
                concept_type=concept_type.upper(),
                status="ACTIVE"
            )
            db.add(concept)

        # Desativa a versão ativa anterior na matriz
        stmt_deact = update(SVRCompatibilityMatrix).where(
            and_(
                SVRCompatibilityMatrix.tenant_id == tenant_id,
                SVRCompatibilityMatrix.concept_id == concept_id,
                SVRCompatibilityMatrix.status == "ACTIVE"
            )
        ).values(
            status="LEGACY",
            data_expiracao=func.now()
        )
        await db.execute(stmt_deact)

        # Insere a nova versão
        new_version = SVRVersion(
            tenant_id=tenant_id,
            concept_id=concept_id,
            semantic_version=semantic_version,
            mapping_version=mapping_version,
            blueprint_version=blueprint_version,
            snapshot=snapshot,
            autor=autor,
            motivo=motivo,
            impacto=impacto
        )
        db.add(new_version)

        # Insere na Matriz de Compatibilidade como ACTIVE
        new_matrix = SVRCompatibilityMatrix(
            tenant_id=tenant_id,
            concept_id=concept_id,
            semantic_version=semantic_version,
            mapping_version=mapping_version,
            blueprint_version=blueprint_version,
            status="ACTIVE",
            data_vigencia=func.now(),
            motivo_alteracao=motivo,
            impacto=impacto
        )
        db.add(new_matrix)

        # Registra auditoria
        audit = SVRAuditLog(
            tenant_id=tenant_id,
            concept_id=concept_id,
            action_type="REGISTER",
            versao_anterior=None,
            versao_nova=f"S:{semantic_version}|M:{mapping_version}",
            motivo=motivo,
            usuario=autor,
            detalhes={"snapshot_keys": list(snapshot.keys())}
        )
        db.add(audit)

        try:
            await db.commit()
        except Exception:
            await db.flush()
        logger.info("[SVR] Novo conceito %s registrado: Semântico=%s | Físico=%s", concept_id, semantic_version, mapping_version)
        return new_version

    async def set_version_status(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        concept_id: str,
        semantic_version: str,
        mapping_version: str,
        status: str,  # ACTIVE, LEGACY, DEPRECATED, OBSOLETE
        autor: str = "SYSTEM",
        motivo: str | None = None,
    ) -> bool:
        """
        Altera o status de uma versão de conceito na Matriz de Compatibilidade de forma auditada.
        """
        try:
            stmt = select(SVRCompatibilityMatrix).where(
                and_(
                    SVRCompatibilityMatrix.tenant_id == tenant_id,
                    SVRCompatibilityMatrix.concept_id == concept_id,
                    SVRCompatibilityMatrix.semantic_version == semantic_version,
                    SVRCompatibilityMatrix.mapping_version == mapping_version
                )
            ).limit(1)
            res = await db.execute(stmt)
            record = res.scalar_one_or_none()

            if not record:
                return False

            old_status = record.status
            record.status = status.upper()
            if status.upper() == "ACTIVE":
                # Desativa qualquer outra versão ativa para este conceito
                stmt_deact = update(SVRCompatibilityMatrix).where(
                    and_(
                        SVRCompatibilityMatrix.tenant_id == tenant_id,
                        SVRCompatibilityMatrix.concept_id == concept_id,
                        SVRCompatibilityMatrix.status == "ACTIVE",
                        SVRCompatibilityMatrix.id != record.id
                    )
                ).values(
                    status="LEGACY",
                    data_expiracao=func.now()
                )
                await db.execute(stmt_deact)
                record.data_expiracao = None

            db.add(record)

            # Registra auditoria
            audit = SVRAuditLog(
                tenant_id=tenant_id,
                concept_id=concept_id,
                action_type="STATUS_CHANGE",
                versao_anterior=old_status,
                versao_nova=status.upper(),
                motivo=motivo,
                usuario=autor,
                detalhes={"version": f"S:{semantic_version}|M:{mapping_version}"}
            )
            db.add(audit)
            try:
                await db.commit()
            except Exception:
                await db.flush()
            return True
        except Exception as exc:
            logger.error("[SVR] Erro ao alterar status da versão: %s", exc)
            return False

    async def get_version_center_summary(self, db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
        """
        Compila informações e estatísticas gerais para o Version Center Dashboard.
        """
        try:
            # Conta conceitos
            stmt_total = select(SVRConcept).where(SVRConcept.tenant_id == tenant_id)
            res_total = await db.execute(stmt_total)
            concepts = res_total.scalars().all()

            # Conta status de versões na matriz
            stmt_matrix = select(SVRCompatibilityMatrix).where(SVRCompatibilityMatrix.tenant_id == tenant_id)
            res_matrix = await db.execute(stmt_matrix)
            matrix_records = res_matrix.scalars().all()

            # Conta audit logs
            stmt_audit = select(SVRAuditLog).where(SVRAuditLog.tenant_id == tenant_id).order_by(SVRAuditLog.criado_em.desc()).limit(10)
            res_audit = await db.execute(stmt_audit)
            recent_audits = res_audit.scalars().all()

            summary = {
                "total_concepts": len(concepts),
                "by_type": {},
                "by_status": {
                    "ACTIVE": 0,
                    "LEGACY": 0,
                    "DEPRECATED": 0,
                    "OBSOLETE": 0
                },
                "recent_activities": []
            }

            for c in concepts:
                t = c.concept_type
                summary["by_type"][t] = summary["by_type"].get(t, 0) + 1

            for m in matrix_records:
                s = m.status.upper()
                if s in summary["by_status"]:
                    summary["by_status"][s] += 1

            for a in recent_audits:
                summary["recent_activities"].append({
                    "id": str(a.id),
                    "concept_id": a.concept_id,
                    "action": a.action_type,
                    "user": a.usuario,
                    "time": a.criado_em.isoformat(),
                    "reason": a.motivo,
                    "details": a.detalhes
                })

            return summary
        except Exception as exc:
            logger.error("[SVR] Erro ao obter sumário do Version Center: %s", exc)
            return {"error": str(exc)}

    async def _bootstrap_default_concept(self, db: AsyncSession, tenant_id: uuid.UUID, concept_id: str) -> dict[str, Any]:
        """
        Popula a versão padrão 1.0 (bootstrap) para um conceito caso ele não exista no SVR.
        Garante retrocompatibilidade imediata com as tabelas estáticas da camada CSIE e NLU.
        """
        from services.ai.csie import STABLE_METRICS, STABLE_DIMENSIONS, STABLE_PERIODS

        concept_type = "METRIC"
        snapshot = {}

        if concept_id in STABLE_METRICS:
            concept_type = "METRIC"
            snapshot = STABLE_METRICS[concept_id]
        elif concept_id in STABLE_DIMENSIONS:
            concept_type = "DIMENSION"
            snapshot = STABLE_DIMENSIONS[concept_id]
        elif concept_id in STABLE_PERIODS:
            concept_type = "PERIOD"
            snapshot = STABLE_PERIODS[concept_id]
        else:
            # Fallback seguro
            concept_type = "METRIC"
            snapshot = {"name": concept_id, "label": concept_id, "physical_col": concept_id.lower(), "aliases": []}

        # Registra sem comitar a transação de forma isolada, para que herde a transação principal
        stmt_c = select(SVRConcept).where(
            and_(
                SVRConcept.tenant_id == tenant_id,
                SVRConcept.concept_id == concept_id
            )
        ).limit(1)
        res_c = await db.execute(stmt_c)
        concept = res_c.scalar_one_or_none()
        if not concept:
            concept = SVRConcept(
                tenant_id=tenant_id,
                concept_id=concept_id,
                concept_type=concept_type,
                status="ACTIVE"
            )
            db.add(concept)

        new_version = SVRVersion(
            tenant_id=tenant_id,
            concept_id=concept_id,
            semantic_version="1.0",
            mapping_version="1",
            snapshot=snapshot,
            autor="SYSTEM",
            motivo="Auto-inicialização de compatibilidade SVR (Bootstrap)"
        )
        db.add(new_version)

        new_matrix = SVRCompatibilityMatrix(
            tenant_id=tenant_id,
            concept_id=concept_id,
            semantic_version="1.0",
            mapping_version="1",
            status="ACTIVE",
            data_vigencia=func.now(),
            motivo_alteracao="Bootstrap inicial"
        )
        db.add(new_matrix)
        try:
            await db.commit()
        except Exception:
            await db.flush()

        logger.info("[SVR] Auto-inicialização (Bootstrap) realizada com sucesso para: %s", concept_id)
        return snapshot

# Instância Singleton do Serviço SVR
svr_service = SemanticVersionRegistryService()
