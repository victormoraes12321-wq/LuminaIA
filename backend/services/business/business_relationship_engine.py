"""
LuminaAI — Business Relationship Engine Service
------------------------------------------------
Mapeia os relacionamentos de causa e efeito entre os indicadores corporativos.
Garante que a IA consiga diagnosticar dependências e influências de BI.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.business_relationship import BusinessRelationship

logger = logging.getLogger("luminaai.business.relationship_engine")


class BusinessRelationshipEngine:
    """
    Controla relacionamentos de causa/efeito entre métricas e KPIs.
    """

    async def get_relationships(
        self,
        tenant_id: uuid.UUID,
        nome: str,
        db: AsyncSession,
    ) -> list[BusinessRelationship]:
        """Busca todas as relações (entrada ou saída) associadas ao nome da métrica/KPI."""
        stmt = select(BusinessRelationship).where(
            and_(
                BusinessRelationship.tenant_id == tenant_id,
                (BusinessRelationship.origem_nome.ilike(nome.strip()) |
                 BusinessRelationship.destino_nome.ilike(nome.strip())),
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def register_relationship(
        self,
        tenant_id: uuid.UUID,
        origem: str,
        destino: str,
        tipo: str,
        descricao: str,
        db: AsyncSession,
    ) -> BusinessRelationship:
        """Registra um relacionamento entre dois indicadores."""
        stmt = select(BusinessRelationship).where(
            and_(
                BusinessRelationship.tenant_id == tenant_id,
                BusinessRelationship.origem_nome.ilike(origem.strip()),
                BusinessRelationship.destino_nome.ilike(destino.strip()),
                BusinessRelationship.tipo_relacao == tipo.upper().strip(),
            )
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.descricao = descricao
            db.add(existing)
            return existing

        relationship = BusinessRelationship(
            tenant_id=tenant_id,
            origem_nome=origem.strip(),
            destino_nome=destino.strip(),
            tipo_relacao=tipo.upper().strip(),
            descricao=descricao.strip(),
        )
        db.add(relationship)
        return relationship

    async def seed_relationships(self, tenant_id: uuid.UUID, db: AsyncSession) -> int:
        """Popula os 6 relacionamentos de causa e efeito padrão no banco do tenant."""
        defaults = [
            ("receita_total", "lucro_bruto", "INFLUENCIA", "Receita total influencia diretamente o Lucro bruto."),
            ("lucro_bruto", "margem_lucro", "INFLUENCIA", "Lucro bruto influencia o cálculo e comportamento da Margem."),
            ("cmv", "rentabilidade", "INFLUENCIA", "O CMV (Custo de Mercadorias Vendidas) impacta a Rentabilidade final."),
            ("ticket_medio", "receita_total", "INFLUENCIA", "O aumento no Ticket Médio eleva a Receita Total."),
            ("quantidade_pedidos", "receita_total", "INFLUENCIA", "O aumento no volume de Pedidos eleva a Receita Total."),
            ("clientes", "taxa_conversao", "INFLUENCIA", "O volume de Clientes ativos influencia a taxa de Conversão."),
        ]

        count = 0
        for orig, dest, tipo, desc in defaults:
            stmt = select(BusinessRelationship).where(
                and_(
                    BusinessRelationship.tenant_id == tenant_id,
                    BusinessRelationship.origem_nome == orig,
                    BusinessRelationship.destino_nome == dest,
                )
            )
            res = await db.execute(stmt)
            if not res.scalar_one_or_none():
                await self.register_relationship(tenant_id, orig, dest, tipo, desc, db)
                count += 1
        return count


# Singleton export
business_relationship_engine = BusinessRelationshipEngine()
