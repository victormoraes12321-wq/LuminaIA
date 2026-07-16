import logging
import uuid
import json
from typing import Any
from sqlalchemy import select
from models.semantic_catalog import SemanticCatalog
from services.data_platform.history_service import history_service
from database import get_db_context

logger = logging.getLogger("luminaai.data_platform.semantic_catalog_service")

class SemanticCatalogService:
    """
    Serviço centralizado para gerenciamento de conceitos, métricas e sinônimos corporativos.
    Toda a IA, Business Layer, Dashboard Builder e Validadores devem usar este catálogo.
    """

    async def get_concept(self, tenant_id: uuid.UUID, nome_oficial: str) -> SemanticCatalog | None:
        """Busca a definição de um conceito pelo seu nome oficial."""
        async with get_db_context() as session:
            stmt = select(SemanticCatalog).where(
                SemanticCatalog.tenant_id == tenant_id,
                SemanticCatalog.nome_oficial == nome_oficial
            )
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    async def resolve_concept_by_synonym(self, tenant_id: uuid.UUID, name_or_synonym: str) -> str | None:
        """
        Varre os conceitos cadastrados no tenant para encontrar match
        pelo nome oficial ou por algum dos sinônimos associados.
        """
        clean_name = name_or_synonym.lower().strip()
        
        async with get_db_context() as session:
            # 1. Busca direta por nome oficial
            stmt_direct = select(SemanticCatalog.nome_oficial).where(
                SemanticCatalog.tenant_id == tenant_id,
                SemanticCatalog.nome_oficial == name_or_synonym
            )
            res_direct = await session.execute(stmt_direct)
            direct_match = res_direct.scalar()
            if direct_match:
                return direct_match
            
            # 2. Busca sequencial varrendo os sinônimos
            stmt_all = select(SemanticCatalog).where(SemanticCatalog.tenant_id == tenant_id)
            res_all = await session.execute(stmt_all)
            concepts = res_all.scalars().all()
            
            for c in concepts:
                # Compara nome oficial de forma case-insensitive
                if c.nome_oficial.lower() == clean_name:
                    return c.nome_oficial
                    
                sinonimos_list = c.sinonimos
                if isinstance(sinonimos_list, str):
                    sinonimos_list = json.loads(sinonimos_list)
                
                # Compara cada sinônimo cadastrado
                for syn in sinonimos_list:
                    if syn.lower().strip() == clean_name:
                        return c.nome_oficial
                        
        return None

    async def register_concept(self, tenant_id: uuid.UUID, concept_data: dict[str, Any]) -> SemanticCatalog:
        """
        Registra ou atualiza um conceito de negócio.
        Versão incrementada automaticamente e logado na trilha de histórico.
        """
        nome_oficial = concept_data["nome_oficial"]
        logger.info(
            "[SemanticCatalogService] Registrando conceito | tenant=%s | nome=%s",
            str(tenant_id)[:8],
            nome_oficial
        )
        
        async with get_db_context() as session:
            stmt = select(SemanticCatalog).where(
                SemanticCatalog.tenant_id == tenant_id,
                SemanticCatalog.nome_oficial == nome_oficial
            )
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()
            
            if existing:
                # Atualização / Evolução estrutural do conceito
                existing.descricao = concept_data.get("descricao", existing.descricao)
                existing.sinonimos = concept_data.get("sinonimos", existing.sinonimos)
                existing.categoria = concept_data.get("categoria", existing.categoria)
                existing.tipo = concept_data.get("tipo", existing.tipo)
                existing.unidade = concept_data.get("unidade", existing.unidade)
                existing.formato = concept_data.get("formato", existing.formato)
                existing.metodo_agregacao = concept_data.get("metodo_agregacao", existing.metodo_agregacao)
                existing.contexto = concept_data.get("contexto", existing.contexto)
                existing.kpis_relacionados = concept_data.get("kpis_relacionados", existing.kpis_relacionados)
                existing.indicadores_derivados = concept_data.get("indicadores_derivados", existing.indicadores_derivados)
                existing.visualizacoes_recomendadas = concept_data.get("visualizacoes_recomendadas", existing.visualizacoes_recomendadas)
                existing.restricoes = concept_data.get("restricoes", existing.restricoes)
                existing.permissoes = concept_data.get("permissoes", existing.permissoes)
                existing.versao += 1
                
                concept = existing
                acao = "UPDATE"
            else:
                # Criação
                concept = SemanticCatalog(
                    tenant_id=tenant_id,
                    nome_oficial=nome_oficial,
                    descricao=concept_data["descricao"],
                    sinonimos=concept_data.get("sinonimos", []),
                    categoria=concept_data.get("categoria", "Geral"),
                    tipo=concept_data.get("tipo", "Fato"),
                    unidade=concept_data.get("unidade", ""),
                    formato=concept_data.get("formato", "number"),
                    metodo_agregacao=concept_data.get("metodo_agregacao", "Soma"),
                    contexto=concept_data.get("contexto"),
                    kpis_relacionados=concept_data.get("kpis_relacionados", []),
                    indicadores_derivados=concept_data.get("indicadores_derivados", []),
                    visualizacoes_recomendadas=concept_data.get("visualizacoes_recomendadas", []),
                    restricoes=concept_data.get("restricoes", []),
                    permissoes=concept_data.get("permissoes", []),
                    versao=1
                )
                session.add(concept)
                acao = "CREATE"
            
            await session.flush()
            
            # Registra no log de histórico
            await history_service.log_change(
                tenant_id=tenant_id,
                estrutura_tipo="SEMANTIC_CONCEPT",
                estrutura_id=nome_oficial,
                acao=acao,
                detalhes={
                    "nome_oficial": nome_oficial,
                    "versao": concept.versao,
                    "categoria": concept.categoria
                }
            )
            
            await session.commit()
            return concept

    async def list_concepts(self, tenant_id: uuid.UUID) -> list[SemanticCatalog]:
        """Lista todos os conceitos registrados no tenant."""
        async with get_db_context() as session:
            stmt = select(SemanticCatalog).where(SemanticCatalog.tenant_id == tenant_id)
            res = await session.execute(stmt)
            return list(res.scalars().all())

# Singleton export
semantic_catalog = SemanticCatalogService()
