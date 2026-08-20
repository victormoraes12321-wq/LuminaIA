"""
LuminaAI — Business Governance & Version Service
-------------------------------------------------
Orquestra o log de auditoria corporativo e implementa o Rollback de regras,
fórmulas, conceitos e KPIs para versões anteriores de forma atômica.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.business_governance_log import BusinessGovernanceLog

logger = logging.getLogger("luminaai.business.governance")


class BusinessGovernance:
    """
    Controla auditoria, aprovação e suporte a rollback na Business Layer.
    """

    async def log_action(
        self,
        tenant_id: uuid.UUID,
        estrutura_tipo: str,
        estrutura_nome: str,
        versao: int,
        autor: str,
        acao: str,
        alteracoes: dict[str, Any],
        snapshot: dict[str, Any],
        db: AsyncSession,
    ) -> BusinessGovernanceLog:
        """Cria e persiste um log de governança contendo snapshot para rollback."""
        log = BusinessGovernanceLog(
            tenant_id=tenant_id,
            estrutura_tipo=estrutura_tipo.upper(),
            estrutura_nome=estrutura_nome.strip(),
            versao=versao,
            autor=autor,
            acao=acao.upper(),
            alteracoes=alteracoes,
            status_aprovacao="APPROVED",  # Por padrão aprovado automaticamente na API
            snapshot=snapshot,
        )
        db.add(log)
        await db.flush()
        return log

    async def rollback(
        self,
        tenant_id: uuid.UUID,
        estrutura_tipo: str,
        estrutura_nome: str,
        target_version: int,
        autor: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Restaura um elemento (Concept, KPI ou Formula) para a versão especificada.

        Processo:
          1. Localiza o log de governança correspondente à versão pretendida.
          2. Recupera o snapshot daquela versão.
          3. Localiza a entidade atual correspondente.
          4. Sobrescreve as propriedades atuais com as propriedades salvas no snapshot.
          5. Incrementa a versão atual e registra a ação de ROLLBACK na governança.
        """
        estrutura_tipo = estrutura_tipo.upper().strip()
        estrutura_name_clean = estrutura_nome.strip()

        # 1. Localiza o log contendo a versão pretendida
        stmt_log = select(BusinessGovernanceLog).where(
            and_(
                BusinessGovernanceLog.tenant_id == tenant_id,
                BusinessGovernanceLog.estrutura_tipo == estrutura_tipo,
                BusinessGovernanceLog.estrutura_nome.ilike(estrutura_name_clean),
                BusinessGovernanceLog.versao == target_version,
            )
        )
        result_log = await db.execute(stmt_log)
        log_entry = result_log.scalar_one_or_none()

        if not log_entry:
            raise ValueError(
                f"Log de governança não encontrado para {estrutura_tipo} '{estrutura_nome}' v{target_version}."
            )

        snapshot = log_entry.snapshot
        if not snapshot:
            raise ValueError("O snapshot da versão selecionada está vazio ou indisponível.")

        # 2. Localiza a entidade atual correspondente para efetuar a restauração
        if estrutura_tipo == "CONCEPT":
            from models.business_concept import BusinessConcept
            stmt_ent = select(BusinessConcept).where(
                and_(
                    BusinessConcept.tenant_id == tenant_id,
                    BusinessConcept.nome.ilike(estrutura_name_clean),
                )
            )
            res_ent = await db.execute(stmt_ent)
            entidade = res_ent.scalar_one_or_none()
            if not entidade:
                raise ValueError(f"Conceito '{estrutura_nome}' não foi localizado para restauração.")

            # Aplica snapshot
            old_snapshot = {
                "nome": entidade.nome,
                "descricao": entidade.descricao,
                "categoria": entidade.categoria,
                "area": entidade.area,
                "departamento": entidade.departamento,
                "definicao_oficial": entidade.definicao_oficial,
                "unidade": entidade.unidade,
                "tipo": entidade.tipo,
                "origem": entidade.origem,
                "owner": entidade.owner,
                "versao": entidade.versao,
                "sinonimos": list(entidade.sinonimos or []),
                "abreviacoes": list(entidade.abreviacoes or []),
                "exemplos": list(entidade.exemplos or []),
                "observacoes": entidade.observacoes,
                "status": entidade.status,
            }

            entidade.descricao = snapshot.get("descricao", entidade.descricao)
            entidade.categoria = snapshot.get("categoria", entidade.categoria)
            entidade.area = snapshot.get("area", entidade.area)
            entidade.departamento = snapshot.get("departamento", entidade.departamento)
            entidade.definicao_oficial = snapshot.get("definicao_oficial", entidade.definicao_oficial)
            entidade.unidade = snapshot.get("unidade", entidade.unidade)
            entidade.tipo = snapshot.get("tipo", entidade.tipo)
            entidade.origem = snapshot.get("origem", entidade.origem)
            entidade.owner = snapshot.get("owner", entidade.owner)
            entidade.sinonimos = list(snapshot.get("sinonimos", entidade.sinonimos))
            entidade.abreviacoes = list(snapshot.get("abreviacoes", entidade.abreviacoes))
            entidade.exemplos = list(snapshot.get("exemplos", entidade.exemplos))
            entidade.observacoes = snapshot.get("observacoes", entidade.observacoes)
            entidade.status = snapshot.get("status", "ACTIVE")
            entidade.versao += 1
            db.add(entidade)

        elif estrutura_tipo == "KPI":
            from models.business_kpi import BusinessKPI
            stmt_ent = select(BusinessKPI).where(
                and_(
                    BusinessKPI.tenant_id == tenant_id,
                    BusinessKPI.nome.ilike(estrutura_name_clean),
                )
            )
            res_ent = await db.execute(stmt_ent)
            entidade = res_ent.scalar_one_or_none()
            if not entidade:
                raise ValueError(f"KPI '{estrutura_nome}' não foi localizado para restauração.")

            old_snapshot = {
                "nome": entidade.nome,
                "descricao": entidade.descricao,
                "categoria": entidade.categoria,
                "area": entidade.area,
                "objetivo": entidade.objetivo,
                "formula_oficial": entidade.formula_oficial,
                "periodicidade": entidade.periodicidade,
                "formato": entidade.formato,
                "precisao": entidade.precisao,
                "unidade": entidade.unidade,
                "limites": dict(entidade.limites or {}),
                "faixas": dict(entidade.faixas or {}),
                "benchmark": dict(entidade.benchmark or {}),
                "responsavel": entidade.responsavel,
                "status": entidade.status,
                "versao": entidade.versao,
                "tags": list(entidade.tags or []),
            }

            entidade.descricao = snapshot.get("descricao", entidade.descricao)
            entidade.categoria = snapshot.get("categoria", entidade.categoria)
            entidade.area = snapshot.get("area", entidade.area)
            entidade.objetivo = snapshot.get("objetivo", entidade.objetivo)
            entidade.formula_oficial = snapshot.get("formula_oficial", entidade.formula_oficial)
            entidade.periodicidade = snapshot.get("periodicidade", entidade.periodicidade)
            entidade.formato = snapshot.get("formato", entidade.formato)
            entidade.precisao = snapshot.get("precisao", entidade.precisao)
            entidade.unidade = snapshot.get("unidade", entidade.unidade)
            entidade.limites = dict(snapshot.get("limites", entidade.limites))
            entidade.faixas = dict(snapshot.get("faixas", entidade.faixas))
            entidade.benchmark = dict(snapshot.get("benchmark", entidade.benchmark))
            entidade.responsavel = snapshot.get("responsavel", entidade.responsavel)
            entidade.status = snapshot.get("status", "ACTIVE")
            entidade.tags = list(snapshot.get("tags", entidade.tags))
            entidade.versao += 1
            db.add(entidade)

        elif estrutura_tipo == "FORMULA":
            from models.business_formula import BusinessFormula
            stmt_ent = select(BusinessFormula).where(
                and_(
                    BusinessFormula.tenant_id == tenant_id,
                    BusinessFormula.nome.ilike(estrutura_name_clean),
                )
            )
            res_ent = await db.execute(stmt_ent)
            entidade = res_ent.scalar_one_or_none()
            if not entidade:
                raise ValueError(f"Fórmula '{estrutura_nome}' não foi localizada para restauração.")

            old_snapshot = {
                "nome": entidade.nome,
                "formula": entidade.formula,
                "entradas": list(entidade.entradas or []),
                "saidas": list(entidade.saidas or []),
                "pre_requisitos": list(entidade.pre_requisitos or []),
                "dependencias": list(entidade.dependencias or []),
                "validacoes": list(entidade.validacoes or []),
                "status": entidade.status,
                "versao": entidade.versao,
            }

            entidade.formula = snapshot.get("formula", entidade.formula)
            entidade.entradas = list(snapshot.get("entradas", entidade.entradas))
            entidade.saidas = list(snapshot.get("saidas", entidade.saidas))
            entidade.pre_requisitos = list(snapshot.get("pre_requisitos", entidade.pre_requisitos))
            entidade.dependencias = list(snapshot.get("dependencias", entidade.dependencias))
            entidade.validacoes = list(snapshot.get("validacoes", entidade.validacoes))
            entidade.status = snapshot.get("status", "ACTIVE")
            entidade.versao += 1
            db.add(entidade)

        else:
            raise ValueError(f"Tipo de estrutura inválida para rollback: {estrutura_tipo}")

        # 3. Registra a ação de ROLLBACK na auditoria
        await self.log_action(
            tenant_id=tenant_id,
            estrutura_tipo=estrutura_tipo,
            estrutura_nome=estrutura_name_clean,
            versao=entidade.versao,
            autor=autor,
            acao="ROLLBACK",
            alteracoes={"rollback_to_version": target_version},
            snapshot=old_snapshot,
            db=db,
        )

        logger.warning(
            "[BusinessGovernance] Rollback executado com sucesso | %s '%s' revertido v%d → v%d por %s.",
            estrutura_tipo, estrutura_name_clean, old_snapshot["versao"], entidade.versao, autor,
        )

        return {
            "success": True,
            "estrutura_tipo": estrutura_tipo,
            "estrutura_nome": estrutura_name_clean,
            "versao_anterior": old_snapshot["versao"],
            "versao_atual": entidade.versao,
            "revertido_para_versao": target_version,
            "autor": autor,
        }

    async def get_history(
        self,
        tenant_id: uuid.UUID,
        estrutura_tipo: str,
        estrutura_nome: str,
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        """Retorna a lista completa de alterações e histórico (audit trail) da estrutura."""
        stmt = select(BusinessGovernanceLog).where(
            and_(
                BusinessGovernanceLog.tenant_id == tenant_id,
                BusinessGovernanceLog.estrutura_tipo == estrutura_tipo.upper().strip(),
                BusinessGovernanceLog.estrutura_nome.ilike(estrutura_nome.strip()),
            )
        ).order_by(BusinessGovernanceLog.criado_em.desc())

        result = await db.execute(stmt)
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "versao": log.versao,
                "autor": log.autor,
                "acao": log.acao,
                "alteracoes": log.alteracoes,
                "status_aprovacao": log.status_aprovacao,
                "criado_em": log.criado_em.isoformat() if log.criado_em else None,
            }
            for log in logs
        ]


# Singleton export
business_governance = BusinessGovernance()
