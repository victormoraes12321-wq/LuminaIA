"""
Lineage Service — LuminaAI Data Platform
------------------------------------------
Registra e resolve a cadeia completa de rastreabilidade dos dados.

Cadeia oficial:
    ERP → Tabela → View Analítica → Dataset → Blueprint → Dashboard → Usuário

Permite rastrear qualquer informação até sua origem no ERP.
"""
import logging
import uuid
from typing import Any

from sqlalchemy import select
from models.metadata_catalog import MetadataCatalog
from database import get_db_context

logger = logging.getLogger("luminaai.data_platform.lineage_service")

# Tipos de nó no lineage
LINEAGE_NODE_TYPES = (
    "ERP",
    "TABELA",
    "VIEW",
    "DATASET",
    "BLUEPRINT",
    "DASHBOARD",
    "USUARIO",
)


class LineageService:
    """
    Serviço de Data Lineage — rastreabilidade completa ponta a ponta.
    Registra e resolve a cadeia de origem dos dados.
    """

    def build_lineage_entry(
        self,
        tipo: str,
        id_: str,
        nome: str,
        pai_id: str | None = None,
        pai_tipo: str | None = None,
        metadados: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Constrói um nó de lineage padronizado.

        Args:
            tipo:       Tipo do nó (ERP, TABELA, VIEW, DATASET, BLUEPRINT, DASHBOARD, USUARIO)
            id_:        Identificador único do nó
            nome:       Nome legível
            pai_id:     ID do nó pai imediato
            pai_tipo:   Tipo do nó pai
            metadados:  Informações adicionais opcionais
        """
        return {
            "tipo": tipo.upper(),
            "id": id_,
            "nome": nome,
            "pai_id": pai_id,
            "pai_tipo": pai_tipo,
            "metadados": metadados or {},
        }

    async def register_lineage(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        lineage_chain: list[dict[str, Any]],
    ) -> None:
        """
        Registra a cadeia de lineage completa para uma estrutura.

        Args:
            tenant_id:      Tenant isolado
            estrutura_id:   ID da estrutura (view, blueprint, etc.)
            lineage_chain:  Lista ordenada de nós de lineage
        """
        logger.info(
            "[LineageService] Registrando lineage | tenant=%s | estrutura=%s | nós=%d",
            str(tenant_id)[:8],
            estrutura_id,
            len(lineage_chain),
        )

        async with get_db_context() as session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res = await session.execute(stmt)
            meta = res.scalar_one_or_none()

            if not meta:
                logger.warning(
                    "[LineageService] Estrutura não encontrada no MetadataCatalog: %s", estrutura_id
                )
                return

            meta.lineage = lineage_chain
            session.add(meta)
            await session.commit()

    async def get_lineage(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> list[dict[str, Any]]:
        """
        Retorna a cadeia de lineage completa de uma estrutura.
        """
        async with get_db_context() as session:
            stmt = select(MetadataCatalog.lineage).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res = await session.execute(stmt)
            row = res.scalar_one_or_none()

        if row is None:
            return []

        return row if isinstance(row, list) else []

    async def build_view_lineage(
        self,
        tenant_id: uuid.UUID,
        view_name: str,
        erp_sistema: str = "Oracle ERP",
        tabelas: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Constrói e persiste o lineage padrão para uma View Analítica.
        Cadeia: ERP → Tabela(s) → View
        """
        tabelas = tabelas or []

        chain: list[dict[str, Any]] = [
            self.build_lineage_entry(
                tipo="ERP",
                id_=erp_sistema.lower().replace(" ", "_"),
                nome=erp_sistema,
            )
        ]

        for tabela in tabelas:
            chain.append(
                self.build_lineage_entry(
                    tipo="TABELA",
                    id_=tabela,
                    nome=tabela,
                    pai_id=erp_sistema.lower().replace(" ", "_"),
                    pai_tipo="ERP",
                )
            )

        chain.append(
            self.build_lineage_entry(
                tipo="VIEW",
                id_=view_name,
                nome=view_name,
                pai_id=tabelas[-1] if tabelas else erp_sistema.lower().replace(" ", "_"),
                pai_tipo="TABELA" if tabelas else "ERP",
            )
        )

        await self.register_lineage(tenant_id, view_name, chain)
        return chain

    async def extend_lineage(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        novo_no: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Estende a cadeia de lineage existente com um novo nó.
        Usado quando um Blueprint, Dataset ou Dashboard é associado à estrutura.
        """
        chain = await self.get_lineage(tenant_id, estrutura_id)
        chain.append(novo_no)
        await self.register_lineage(tenant_id, estrutura_id, chain)
        return chain

    async def find_origin(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> dict[str, Any] | None:
        """
        Retorna o nó de origem (tipo ERP) da cadeia de lineage.
        """
        chain = await self.get_lineage(tenant_id, estrutura_id)
        for node in chain:
            if node.get("tipo") == "ERP":
                return node
        return None


# Singleton export
lineage_service = LineageService()
