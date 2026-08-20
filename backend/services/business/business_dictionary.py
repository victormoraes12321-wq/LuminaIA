"""
LuminaAI — Business Dictionary Service
---------------------------------------
Gerencia os conceitos e definições oficiais do Dicionário Corporativo.
Garante que não haja múltiplas definições para o mesmo conceito por tenant.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.business_concept import BusinessConcept
from services.business.business_governance import business_governance

logger = logging.getLogger("luminaai.business.dictionary")


class BusinessDictionary:
    """
    Gerencia conceitos e termos de negócio oficiais do Dicionário Corporativo.
    """

    async def get_concept(
        self,
        tenant_id: uuid.UUID,
        nome: str,
        db: AsyncSession,
    ) -> BusinessConcept | None:
        """Retorna o conceito pelo nome oficial (case-insensitive) e tenant."""
        stmt = select(BusinessConcept).where(
            and_(
                BusinessConcept.tenant_id == tenant_id,
                BusinessConcept.nome.ilike(nome.strip()),
                BusinessConcept.status == "ACTIVE",
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_concepts(
        self,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        categoria: str | None = None,
        area: str | None = None,
    ) -> list[BusinessConcept]:
        """Lista todos os conceitos ativos do tenant, com filtros opcionais."""
        conditions = [
            BusinessConcept.tenant_id == tenant_id,
            BusinessConcept.status == "ACTIVE",
        ]
        if categoria:
            conditions.append(BusinessConcept.categoria == categoria)
        if area:
            conditions.append(BusinessConcept.area == area)

        stmt = select(BusinessConcept).where(and_(*conditions)).order_by(BusinessConcept.nome.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def register_concept(
        self,
        tenant_id: uuid.UUID,
        concept_data: dict[str, Any],
        autor: str,
        db: AsyncSession,
    ) -> BusinessConcept:
        """
        Registra ou atualiza um conceito de negócio no dicionário oficial.
        Caso o conceito já exista, incrementa a versão e gera log de governança (audit trail).
        """
        nome = concept_data["nome"].strip()
        existing = await self.get_concept(tenant_id, nome, db)

        if existing:
            # Verifica se há alterações reais para evitar versões vazias
            has_changes = False
            alteracoes = {}
            for field in [
                "descricao", "categoria", "area", "departamento", "definicao_oficial",
                "unidade", "tipo", "origem", "owner", "sinonimos", "abreviacoes",
                "exemplos", "observacoes",
            ]:
                if field in concept_data:
                    val_new = concept_data[field]
                    val_old = getattr(existing, field)
                    if val_new != val_old:
                        has_changes = True
                        alteracoes[field] = {"old": val_old, "new": val_new}

            if not has_changes:
                logger.info(
                    "[BusinessDictionary] Sem alterações para o conceito '%s'. Mantendo v%d.",
                    nome, existing.versao,
                )
                return existing

            # Executa a atualização sob o BusinessGovernance (registra snapshot e gera log)
            old_snapshot = self._to_snapshot(existing)
            existing.descricao = concept_data.get("descricao", existing.descricao)
            existing.categoria = concept_data.get("categoria", existing.categoria)
            existing.area = concept_data.get("area", existing.area)
            existing.departamento = concept_data.get("departamento", existing.departamento)
            existing.definicao_oficial = concept_data.get("definicao_oficial", existing.definicao_oficial)
            existing.unidade = concept_data.get("unidade", existing.unidade)
            existing.tipo = concept_data.get("tipo", existing.tipo)
            existing.origem = concept_data.get("origem", existing.origem)
            existing.owner = concept_data.get("owner", existing.owner)
            existing.sinonimos = list(concept_data.get("sinonimos", existing.sinonimos))
            existing.abreviacoes = list(concept_data.get("abreviacoes", existing.abreviacoes))
            existing.exemplos = list(concept_data.get("exemplos", existing.exemplos))
            existing.observacoes = concept_data.get("observacoes", existing.observacoes)
            existing.versao += 1

            db.add(existing)

            # Grava no log de governança
            await business_governance.log_action(
                tenant_id=tenant_id,
                estrutura_tipo="CONCEPT",
                estrutura_nome=nome,
                versao=existing.versao,
                autor=autor,
                acao="UPDATE",
                alteracoes=alteracoes,
                snapshot=old_snapshot,
                db=db,
            )

            logger.info(
                "[BusinessDictionary] Conceito '%s' atualizado para v%d por %s.",
                nome, existing.versao, autor,
            )
            return existing

        else:
            # Criação do conceito inicial (versão 1)
            concept = BusinessConcept(
                tenant_id=tenant_id,
                nome=nome,
                descricao=concept_data["descricao"],
                categoria=concept_data.get("categoria", "Geral"),
                area=concept_data.get("area", "Geral"),
                departamento=concept_data.get("departamento", "Geral"),
                definicao_oficial=concept_data.get("definicao_oficial", concept_data["descricao"]),
                unidade=concept_data.get("unidade", ""),
                tipo=concept_data.get("tipo", "Métrica"),
                origem=concept_data.get("origem", "Manual"),
                owner=concept_data.get("owner", autor),
                versao=1,
                sinonimos=list(concept_data.get("sinonimos", [])),
                abreviacoes=list(concept_data.get("abreviacoes", [])),
                exemplos=list(concept_data.get("exemplos", [])),
                observacoes=concept_data.get("observacoes"),
                status="ACTIVE",
            )
            db.add(concept)
            await db.flush()

            # Grava no log de governança
            await business_governance.log_action(
                tenant_id=tenant_id,
                estrutura_tipo="CONCEPT",
                estrutura_nome=nome,
                versao=1,
                autor=autor,
                acao="CREATE",
                alteracoes={"criado": True},
                snapshot=self._to_snapshot(concept),
                db=db,
            )

            logger.info(
                "[BusinessDictionary] Conceito '%s' criado (v1) por %s.",
                nome, autor,
            )
            return concept

    def _to_snapshot(self, concept: BusinessConcept) -> dict[str, Any]:
        """Gera um snapshot em formato dict para auditoria e rollback."""
        return {
            "nome": concept.nome,
            "descricao": concept.descricao,
            "categoria": concept.categoria,
            "area": concept.area,
            "departamento": concept.departamento,
            "definicao_oficial": concept.definicao_oficial,
            "unidade": concept.unidade,
            "tipo": concept.tipo,
            "origem": concept.origem,
            "owner": concept.owner,
            "versao": concept.versao,
            "sinonimos": list(concept.sinonimos or []),
            "abreviacoes": list(concept.abreviacoes or []),
            "exemplos": list(concept.exemplos or []),
            "observacoes": concept.observacoes,
            "status": concept.status,
        }


# Singleton export
business_dictionary = BusinessDictionary()
