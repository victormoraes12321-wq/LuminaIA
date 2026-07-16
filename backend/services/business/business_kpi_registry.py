"""
LuminaAI — Business KPI Registry Service
-----------------------------------------
Gerencia o registro oficial de KPIs corporativos.
Garante que não haja KPIs duplicados e gerencia as versões via governança.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.business_kpi import BusinessKPI
from services.business.business_governance import business_governance

logger = logging.getLogger("luminaai.business.kpi_registry")


class BusinessKPIRegistry:
    """
    Gerencia o cadastro oficial de KPIs corporativos.
    """

    async def get_kpi(
        self,
        tenant_id: uuid.UUID,
        nome: str,
        db: AsyncSession,
    ) -> BusinessKPI | None:
        """Retorna o KPI pelo nome oficial (case-insensitive) e tenant."""
        stmt = select(BusinessKPI).where(
            and_(
                BusinessKPI.tenant_id == tenant_id,
                BusinessKPI.nome.ilike(nome.strip()),
                BusinessKPI.status == "ACTIVE",
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_kpis(
        self,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        categoria: str | None = None,
        area: str | None = None,
    ) -> list[BusinessKPI]:
        """Lista todos os KPIs ativos do tenant, com filtros opcionais."""
        conditions = [
            BusinessKPI.tenant_id == tenant_id,
            BusinessKPI.status == "ACTIVE",
        ]
        if categoria:
            conditions.append(BusinessKPI.categoria == categoria)
        if area:
            conditions.append(BusinessKPI.area == area)

        stmt = select(BusinessKPI).where(and_(*conditions)).order_by(BusinessKPI.nome.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def register_kpi(
        self,
        tenant_id: uuid.UUID,
        kpi_data: dict[str, Any],
        autor: str,
        db: AsyncSession,
    ) -> BusinessKPI:
        """
        Registra ou atualiza um KPI corporativo.
        Impede KPIs duplicados. Caso exista, incrementa a versão e registra log de governança.
        """
        nome = kpi_data["nome"].strip()
        existing = await self.get_kpi(tenant_id, nome, db)

        if existing:
            # Verifica se há alterações
            has_changes = False
            alteracoes = {}
            for field in [
                "descricao", "categoria", "area", "objetivo", "formula_oficial",
                "periodicidade", "formato", "precisao", "unidade", "limites",
                "faixas", "benchmark", "responsavel", "tags",
            ]:
                if field in kpi_data:
                    val_new = kpi_data[field]
                    val_old = getattr(existing, field)
                    if val_new != val_old:
                        has_changes = True
                        alteracoes[field] = {"old": val_old, "new": val_new}

            if not has_changes:
                logger.info(
                    "[BusinessKPIRegistry] KPI '%s' sem alterações. Mantendo v%d.",
                    nome, existing.versao,
                )
                return existing

            # Executa a atualização sob o BusinessGovernance
            old_snapshot = self._to_snapshot(existing)
            existing.descricao = kpi_data.get("descricao", existing.descricao)
            existing.categoria = kpi_data.get("categoria", existing.categoria)
            existing.area = kpi_data.get("area", existing.area)
            existing.objetivo = kpi_data.get("objetivo", existing.objetivo)
            existing.formula_oficial = kpi_data.get("formula_oficial", existing.formula_oficial)
            existing.periodicidade = kpi_data.get("periodicidade", existing.periodicidade)
            existing.formato = kpi_data.get("formato", existing.formato)
            existing.precisao = kpi_data.get("precisao", existing.precisao)
            existing.unidade = kpi_data.get("unidade", existing.unidade)
            existing.limites = dict(kpi_data.get("limites", existing.limites))
            existing.faixas = dict(kpi_data.get("faixas", existing.faixas))
            existing.benchmark = dict(kpi_data.get("benchmark", existing.benchmark))
            existing.responsavel = kpi_data.get("responsavel", existing.responsavel)
            existing.tags = list(kpi_data.get("tags", existing.tags))
            existing.versao += 1

            db.add(existing)

            # Grava no log de governança
            await business_governance.log_action(
                tenant_id=tenant_id,
                estrutura_tipo="KPI",
                estrutura_nome=nome,
                versao=existing.versao,
                autor=autor,
                acao="UPDATE",
                alteracoes=alteracoes,
                snapshot=old_snapshot,
                db=db,
            )

            logger.info(
                "[BusinessKPIRegistry] KPI '%s' atualizado para v%d por %s.",
                nome, existing.versao, autor,
            )
            return existing

        else:
            # Criação do KPI (versão 1)
            kpi = BusinessKPI(
                tenant_id=tenant_id,
                nome=nome,
                descricao=kpi_data["descricao"],
                categoria=kpi_data.get("categoria", "Geral"),
                area=kpi_data.get("area", "Geral"),
                objetivo=kpi_data.get("objetivo", kpi_data["descricao"]),
                formula_oficial=kpi_data["formula_oficial"],
                periodicidade=kpi_data.get("periodicidade", "Mensal"),
                formato=kpi_data.get("formato", "number"),
                precisao=kpi_data.get("precisao", 2),
                unidade=kpi_data.get("unidade", ""),
                limites=dict(kpi_data.get("limites", {})),
                faixas=dict(kpi_data.get("faixas", {})),
                benchmark=dict(kpi_data.get("benchmark", {})),
                responsavel=kpi_data.get("responsavel", autor),
                status="ACTIVE",
                versao=1,
                tags=list(kpi_data.get("tags", [])),
            )
            db.add(kpi)
            await db.flush()

            # Grava no log de governança
            await business_governance.log_action(
                tenant_id=tenant_id,
                estrutura_tipo="KPI",
                estrutura_nome=nome,
                versao=1,
                autor=autor,
                acao="CREATE",
                alteracoes={"criado": True},
                snapshot=self._to_snapshot(kpi),
                db=db,
            )

            logger.info(
                "[BusinessKPIRegistry] KPI '%s' registrado (v1) por %s.",
                nome, autor,
            )
            return kpi

    def _to_snapshot(self, kpi: BusinessKPI) -> dict[str, Any]:
        """Gera um snapshot em formato dict para auditoria e rollback."""
        return {
            "nome": kpi.nome,
            "descricao": kpi.descricao,
            "categoria": kpi.categoria,
            "area": kpi.area,
            "objetivo": kpi.objetivo,
            "formula_oficial": kpi.formula_oficial,
            "periodicidade": kpi.periodicidade,
            "formato": kpi.formato,
            "precisao": kpi.precisao,
            "unidade": kpi.unidade,
            "limites": dict(kpi.limites or {}),
            "faixas": dict(kpi.faixas or {}),
            "benchmark": dict(kpi.benchmark or {}),
            "responsavel": kpi.responsavel,
            "status": kpi.status,
            "versao": kpi.versao,
            "tags": list(kpi.tags or []),
        }


# Singleton export
business_kpi_registry = BusinessKPIRegistry()
