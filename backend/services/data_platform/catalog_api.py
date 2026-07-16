"""
Catalog API — LuminaAI Data Platform
--------------------------------------
Fachada única e oficial que todos os módulos internos devem usar para
interagir com o Metadata Catalog, Health Monitor, Lineage e Dependency Graph.

REGRA ARQUITETURAL:
  Nenhum módulo pode acessar diretamente o MetadataCatalog, HealthMonitor,
  LineageService ou DependencyGraph.
  Todos devem usar exclusivamente esta API.

Módulos autorizados a consultar:
  - QueryIntelligenceEngine (identificar estruturas existentes)
  - BusinessLayer (validações estruturais)
  - IntegrityService (atualizar scores de saúde)
  - ExecutionEngine (registrar acessos)
  - ViewManager (registrar views)
  - Frontend (via routers — via read-only)

A IA pode CONSULTAR mas nunca ALTERAR metadados.
"""
import logging
import uuid
from typing import Any

from services.data_platform.metadata_catalog import MetadataCatalogService
from services.data_platform.health_monitor import HealthMonitor
from services.data_platform.lineage_service import LineageService
from services.data_platform.dependency_graph import DependencyGraph
from models.metadata_catalog import MetadataCatalog
from models.metadata_catalog_version import MetadataCatalogVersion

logger = logging.getLogger("luminaai.data_platform.catalog_api")


class CatalogAPI:
    """
    API Interna do Metadata Catalog.
    Ponto único de acesso à governança da Data Platform.
    """

    def __init__(self) -> None:
        self._catalog = MetadataCatalogService()
        self._health = HealthMonitor()
        self._lineage = LineageService()
        self._graph = DependencyGraph()

    # ── Registro ──────────────────────────────────────────────────────────

    async def register(
        self,
        tenant_id: uuid.UUID,
        tipo: str,
        dados: dict[str, Any],
        lineage_tabelas: list[str] | None = None,
        upstream_ids: list[str] | None = None,
    ) -> MetadataCatalog:
        """
        Registra uma estrutura no Metadata Catalog e inicializa lineage e grafo.

        Args:
            tenant_id:        Tenant isolado
            tipo:             Tipo da estrutura (VIEW, BLUEPRINT, DATASET, KPI, DASHBOARD)
            dados:            Dados da estrutura (deve incluir 'estrutura_id' ou 'nome_view')
            lineage_tabelas:  Tabelas ERP usadas (para montagem automática do lineage)
            upstream_ids:     IDs das estruturas upstream (para o grafo de dependências)
        """
        estrutura_id = dados.get("estrutura_id") or dados.get("nome_view", "")
        logger.info(
            "[CatalogAPI] register | tipo=%s | estrutura_id=%s", tipo, estrutura_id
        )

        # 1. Registra a entidade no catálogo
        meta = await self._catalog.register_entity(tenant_id, tipo, dados)

        # 2. Monta lineage automático para Views
        if tipo.upper() == "VIEW" and lineage_tabelas:
            await self._lineage.build_view_lineage(
                tenant_id=tenant_id,
                view_name=estrutura_id,
                tabelas=lineage_tabelas,
            )

        # 3. Registra dependências upstream no grafo
        if upstream_ids:
            await self._graph.register_dependency(
                tenant_id=tenant_id,
                estrutura_id=estrutura_id,
                depende_de=upstream_ids,
            )

        # 4. Inicializa scores de saúde
        await self._health.compute_and_update(tenant_id, estrutura_id)

        return meta

    # ── Consulta ──────────────────────────────────────────────────────────

    async def query(
        self,
        tenant_id: uuid.UUID,
        search_query: str | None = None,
        tipo: str | None = None,
        tags: list[str] | None = None,
        categoria: str | None = None,
        limit: int = 50,
    ) -> list[MetadataCatalog]:
        """
        Pesquisa estruturas no catálogo por texto, tipo, tags ou categoria.
        Usada pela IA para identificar estruturas existentes e evitar duplicações.
        """
        return await self._catalog.search(
            tenant_id=tenant_id,
            query=search_query,
            tipo=tipo,
            tags=tags,
            categoria=categoria,
            limit=limit,
        )

    async def get(
        self,
        tenant_id: uuid.UUID,
        tipo: str,
        estrutura_id: str,
    ) -> MetadataCatalog | None:
        """Busca uma estrutura específica por tipo e ID."""
        return await self._catalog.get_entity(tenant_id, tipo, estrutura_id)

    async def get_any(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> MetadataCatalog | None:
        """Busca uma estrutura por ID sem exigir que o chamador conheca o tipo."""
        return await self._catalog.get_entity_any(tenant_id, estrutura_id)

    # ── Health & Monitoring ───────────────────────────────────────────────

    async def get_health_report(
        self,
        tenant_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Relatório completo de saúde de todo o tenant."""
        return await self._health.get_tenant_health_report(tenant_id)

    async def refresh_health(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> dict[str, float]:
        """Recalcula e persiste os scores de saúde de uma estrutura."""
        return await self._health.compute_and_update(tenant_id, estrutura_id)

    # ── Lineage ───────────────────────────────────────────────────────────

    async def get_lineage(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> list[dict[str, Any]]:
        """Retorna a cadeia de lineage completa de uma estrutura."""
        return await self._lineage.get_lineage(tenant_id, estrutura_id)

    async def find_origin(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> dict[str, Any] | None:
        """Retorna o nó de origem (ERP) na cadeia de lineage."""
        return await self._lineage.find_origin(tenant_id, estrutura_id)

    # ── Dependency Graph ──────────────────────────────────────────────────

    async def get_impact(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> dict[str, Any]:
        """
        Análise de impacto de alteração: retorna todas as estruturas afetadas (diretas + transitivas).
        Deve ser chamado antes de qualquer alteração estrutural no ViewManager.
        """
        return await self._graph.get_impact(tenant_id, estrutura_id)

    async def get_dependency_graph(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> dict[str, Any]:
        """Retorna o grafo direto de dependências (upstream + downstream)."""
        return await self._graph.get_graph(tenant_id, estrutura_id)

    async def register_dependency(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        depende_de: list[str],
    ) -> None:
        """Registra dependências upstream de uma estrutura."""
        await self._graph.register_dependency(tenant_id, estrutura_id, depende_de)

    # ── Versionamento ─────────────────────────────────────────────────────

    async def snapshot(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        motivo: str | None = None,
        autor: str | None = None,
    ) -> MetadataCatalogVersion | None:
        """Cria snapshot imutável da versão atual da estrutura."""
        return await self._catalog.create_version_snapshot(
            tenant_id=tenant_id,
            estrutura_id=estrutura_id,
            motivo=motivo,
            autor=autor,
        )

    async def get_version_history(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> list[MetadataCatalogVersion]:
        """Lista o histórico completo de versões de uma estrutura."""
        return await self._catalog.get_version_history(tenant_id, estrutura_id)

    async def rollback(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        versao_alvo: int,
    ) -> MetadataCatalog | None:
        """Restaura uma estrutura para uma versão anterior."""
        return await self._catalog.rollback_to_version(tenant_id, estrutura_id, versao_alvo)

    # ── Cache ─────────────────────────────────────────────────────────────

    async def update_cache(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        ativo: bool,
        ttl_segundos: int = 3600,
        hit_rate: float | None = None,
    ) -> None:
        """Atualiza metadados de cache de uma estrutura."""
        await self._catalog.update_cache_metadata(
            tenant_id=tenant_id,
            estrutura_id=estrutura_id,
            cache_ativo=ativo,
            ttl_segundos=ttl_segundos,
            hit_rate=hit_rate,
        )

    # ── Acesso & Sync ─────────────────────────────────────────────────────

    async def register_access(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        user_id: str | None = None,
    ) -> None:
        """Registra acesso de usuário — chamado após cada consulta executada."""
        await self._catalog.register_access(tenant_id, estrutura_id, user_id)

    async def register_query(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        execution_time_ms: float,
    ) -> None:
        """Registra execucao de consulta e tempo medio via Metadata Catalog."""
        await self._catalog.register_query(tenant_id, estrutura_id, execution_time_ms)

    async def update_sync(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        resultado_sync: dict[str, Any],
    ) -> None:
        """Atualiza metadados de sincronização (duração, registros, erros)."""
        await self._catalog.update_sync_metadata(tenant_id, estrutura_id, resultado_sync)

    # ── Summary ───────────────────────────────────────────────────────────

    async def summary(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        """Resumo executivo do catálogo completo do tenant."""
        return await self._catalog.get_catalog_summary(tenant_id)


# Singleton export
catalog_api = CatalogAPI()
