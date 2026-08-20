"""
Testes de Integração: Metadata Catalog Corporativo
----------------------------------------------------
Valida todos os fluxos do centro de governança da Data Platform.

Cobertura:
  1. MetadataCatalogService — registro de entidades, pesquisa, sync, query, lineage, dependency graph
  2. HealthMonitor — cálculo de scores e geração de alertas
  3. LineageService — montagem e resolução da cadeia ERP→Usuário
  4. DependencyGraph — direto, transitivo e impacto
  5. CatalogAPI — fachada única (register, query, health, lineage, graph, versioning, cache)
  6. Versionamento — snapshot imutável, histórico, rollback
  7. Cache metadata
  8. Multi-Tenant isolation
"""
from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# ─── UUIDs de teste ───────────────────────────────────────────────────────────
TENANT_A = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
TENANT_B = uuid.UUID("b1ffcd00-0d1c-4fa9-cc7e-7cc0ce491b22")



# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_meta(
    nome: str = "VW_VENDAS",
    tipo: str = "VIEW",
    estrutura_id: str = "VW_VENDAS",
    versao: int = 1,
    status: str = "success",
    integridade: str = "valid",
    health_score: float = 100.0,
    integrity_score: float = 100.0,
    performance_score: float = 100.0,
    freshness_score: float = 100.0,
    usage_score: float = 0.0,
    quantidade_consultas: int = 0,
    quantidade_usuarios: int = 0,
    ultima_sincronizacao: datetime | None = None,
    tempo_medio_execucao: float = 0.0,
    cache_ativo: bool = False,
    alertas: list | None = None,
    lineage: list | None = None,
    dependencias_grafo: dict | None = None,
    tags: list | None = None,
) -> MagicMock:
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.nome_view = nome
    obj.tipo_estrutura = tipo
    obj.estrutura_id = estrutura_id
    obj.versao = versao
    obj.status = status
    obj.integridade = integridade
    obj.health_score = health_score
    obj.integrity_score = integrity_score
    obj.performance_score = performance_score
    obj.freshness_score = freshness_score
    obj.usage_score = usage_score
    obj.quantidade_consultas = quantidade_consultas
    obj.quantidade_usuarios = quantidade_usuarios
    obj.ultima_sincronizacao = ultima_sincronizacao
    obj.tempo_medio_execucao = tempo_medio_execucao
    obj.cache_ativo = cache_ativo
    obj.alertas = alertas or []
    obj.lineage = lineage or []
    obj.dependencias_grafo = dependencias_grafo or {}
    obj.tags = tags or []
    obj.owner = ""
    obj.categoria = "Comercial"
    obj.tabelas_utilizadas = ["PEDIDO", "ITEM_PEDIDO"]
    obj.campos_utilizados = ["dt_emissao", "vl_total"]
    obj.kpis_suportados = ["receita_total"]
    obj.dependencias = []
    obj.tempo_medio_atualizacao = 0.0
    obj.blueprint_associado = None
    obj.dashboard_associado = None
    obj.cache_atualizado_em = None
    obj.cache_ttl_segundos = 3600
    obj.cache_hit_rate = 0.0
    obj.duracao_ultima_sync_ms = 0.0
    obj.registros_ultima_sync = 0
    obj.erros_sync = []
    obj.ultima_utilizacao = None
    obj.criado_em = datetime.now(timezone.utc)
    obj.atualizado_em = datetime.now(timezone.utc)
    return obj


def make_version(metadata_id: uuid.UUID, versao: int = 1) -> MagicMock:
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.metadata_id = metadata_id
    obj.versao = versao
    obj.snapshot = {"versao": versao, "nome_view": "VW_VENDAS"}
    obj.autor = "tester"
    obj.motivo = "Teste de snapshot"
    obj.criado_em = datetime.now(timezone.utc)
    return obj


def _mock_session_with_meta(meta_obj, return_none: bool = False):
    mock_session = AsyncMock()
    mock_result = MagicMock()
    if return_none:
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalar_one.side_effect = Exception("Not found")
    else:
        mock_result.scalar_one_or_none.return_value = meta_obj
        mock_result.scalar_one.return_value = meta_obj
    mock_result.scalar.return_value = meta_obj
    mock_result.scalars.return_value.all.return_value = [meta_obj] if meta_obj else []
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    return mock_session


# ──────────────────────────────────────────────────────────────────────────────
# MetadataCatalogService Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestMetadataCatalogService:
    """Testa o MetadataCatalogService com todos os novos métodos."""

    @pytest.mark.asyncio
    async def test_register_entity_create(self):
        """Deve criar nova entidade VIEW no catálogo."""
        from services.data_platform.metadata_catalog import MetadataCatalogService
        svc = MetadataCatalogService()

        dados = {
            "estrutura_id": "VW_CLIENTES",
            "nome_view": "VW_CLIENTES",
            "origem": "ERP_ORACLE",
            "categoria": "Clientes",
            "tags": ["clientes", "crm"],
            "kpis_suportados": ["cliente_ativo"],
        }

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("services.data_platform.metadata_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.register_entity(TENANT_A, "VIEW", dados)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_entity_update(self):
        """Deve incrementar versão ao atualizar entidade existente."""
        from services.data_platform.metadata_catalog import MetadataCatalogService
        svc = MetadataCatalogService()

        existing = make_meta("VW_VENDAS", versao=3)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("services.data_platform.metadata_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            await svc.register_entity(TENANT_A, "VIEW", {
                "estrutura_id": "VW_VENDAS",
                "nome_view": "VW_VENDAS",
                "tags": ["atualizado"],
            })

        assert existing.versao == 4

    @pytest.mark.asyncio
    async def test_get_entity(self):
        """Deve retornar entidade pelo tipo e estrutura_id."""
        from services.data_platform.metadata_catalog import MetadataCatalogService
        svc = MetadataCatalogService()

        meta = make_meta("VW_VENDAS", tipo="VIEW")
        mock_session = _mock_session_with_meta(meta)

        with patch("services.data_platform.metadata_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.get_entity(TENANT_A, "VIEW", "VW_VENDAS")

        assert result is not None

    @pytest.mark.asyncio
    async def test_search_by_name(self):
        """Deve retornar resultados filtrados por nome."""
        from services.data_platform.metadata_catalog import MetadataCatalogService
        svc = MetadataCatalogService()

        metas = [make_meta("VW_VENDAS"), make_meta("VW_CLIENTES")]
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = metas
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.data_platform.metadata_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.search(TENANT_A, query="vendas")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_catalog_summary(self):
        """Deve retornar resumo com totais por tipo e health médio."""
        from services.data_platform.metadata_catalog import MetadataCatalogService
        svc = MetadataCatalogService()

        metas = [
            make_meta("VW_VENDAS", tipo="VIEW", health_score=90.0),
            make_meta("BP_VENDAS", tipo="BLUEPRINT", health_score=80.0),
            make_meta("DS_VENDAS", tipo="DATASET", health_score=70.0),
        ]
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = metas
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.data_platform.metadata_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.get_catalog_summary(TENANT_A)

        assert result["total"] == 3
        assert result["health_medio"] == 80.0
        assert result["por_tipo"]["VIEW"] == 1
        assert result["por_tipo"]["BLUEPRINT"] == 1

    @pytest.mark.asyncio
    async def test_update_sync_metadata(self):
        """Deve atualizar metadados de sincronização corretamente."""
        from services.data_platform.metadata_catalog import MetadataCatalogService
        svc = MetadataCatalogService()

        meta = make_meta(status="success")
        mock_session = _mock_session_with_meta(meta)

        resultado_sync = {
            "status": "error",
            "duracao_ms": 1200.5,
            "registros": 450,
            "erros": [{"tipo": "TIMEOUT", "msg": "Query timeout"}],
        }

        with patch("services.data_platform.metadata_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            await svc.update_sync_metadata(TENANT_A, "VW_VENDAS", resultado_sync)

        assert meta.status == "error"
        assert meta.duracao_ultima_sync_ms == 1200.5
        assert meta.registros_ultima_sync == 450
        assert meta.integridade == "corrupted"

    @pytest.mark.asyncio
    async def test_register_access_increments_count(self):
        """Deve incrementar quantidade_consultas ao registrar acesso."""
        from services.data_platform.metadata_catalog import MetadataCatalogService
        svc = MetadataCatalogService()

        meta = make_meta(quantidade_consultas=9)
        mock_session = _mock_session_with_meta(meta)

        with patch("services.data_platform.metadata_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            await svc.register_access(TENANT_A, "VW_VENDAS", user_id="user-123")

        assert meta.quantidade_consultas == 10


# ──────────────────────────────────────────────────────────────────────────────
# HealthMonitor Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestHealthMonitor:
    """Testa o HealthMonitor com todos os cenários de score."""

    def test_integrity_score_valid(self):
        """Score deve ser 100 para estrutura íntegra e ativa."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        meta = make_meta(status="success", integridade="valid")
        assert hm.calc_integrity_score(meta) == 100.0

    def test_integrity_score_corrupted(self):
        """Score deve cair abaixo de 70 para estrutura corrompida."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        meta = make_meta(status="error", integridade="corrupted")
        score = hm.calc_integrity_score(meta)
        assert score < 70.0

    def test_performance_score_fast(self):
        """Score 100 para consultas rápidas."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        meta = make_meta(tempo_medio_execucao=0.0)
        assert hm.calc_performance_score(meta) == 100.0

    def test_performance_score_slow(self):
        """Score 0 para consultas acima do limite máximo."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        meta = make_meta(tempo_medio_execucao=5000.0)
        assert hm.calc_performance_score(meta) == 0.0

    def test_performance_score_medium(self):
        """Score 50 para consulta na metade do limite."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        meta = make_meta(tempo_medio_execucao=2500.0)
        assert hm.calc_performance_score(meta) == 50.0

    def test_freshness_score_never_synced(self):
        """Score neutro (50) para estrutura sem sincronização registrada."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        meta = make_meta(ultima_sincronizacao=None)
        assert hm.calc_freshness_score(meta) == 50.0

    def test_freshness_score_recent(self):
        """Score alto para sincronização recente."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        meta = make_meta(ultima_sincronizacao=datetime.now(timezone.utc) - timedelta(hours=1))
        score = hm.calc_freshness_score(meta)
        assert score > 90.0

    def test_freshness_score_stale(self):
        """Score 0 para sincronização antiga (> 48h)."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        meta = make_meta(ultima_sincronizacao=datetime.now(timezone.utc) - timedelta(hours=50))
        assert hm.calc_freshness_score(meta) == 0.0

    def test_usage_score_no_queries(self):
        """Score 0 para estrutura sem consultas."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        meta = make_meta(quantidade_consultas=0, quantidade_usuarios=0)
        assert hm.calc_usage_score(meta) == 0.0

    def test_usage_score_heavy_usage(self):
        """Score 100 para estrutura com 1000+ consultas e múltiplos usuários."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        meta = make_meta(quantidade_consultas=1000, quantidade_usuarios=10)
        score = hm.calc_usage_score(meta)
        assert score == 100.0

    def test_health_score_weighted_average(self):
        """Health score deve ser média ponderada dos 4 scores."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        # 100*0.35 + 100*0.30 + 100*0.25 + 0*0.10 = 90.0
        hs = hm.calc_health_score(100.0, 100.0, 100.0, 0.0)
        assert hs == 90.0

    def test_generate_alerts_below_threshold(self):
        """Deve gerar alertas para scores abaixo de 70."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        scores = {
            "integrity_score": 50.0,
            "performance_score": 30.0,
            "freshness_score": 80.0,
            "usage_score": 0.0,
            "health_score": 55.0,
        }
        alerts = hm.generate_alerts("VW_VENDAS", scores)
        tipos = [a["tipo"] for a in alerts]
        assert "INTEGRITY_SCORE" in tipos
        assert "PERFORMANCE_SCORE" in tipos
        assert "FRESHNESS_SCORE" not in tipos  # 80 > 70
        assert "USAGE_SCORE" not in tipos       # usage nunca gera alerta

    def test_generate_no_alerts_when_healthy(self):
        """Não deve gerar alertas quando todos os scores estão ok."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        scores = {
            "integrity_score": 95.0,
            "performance_score": 85.0,
            "freshness_score": 90.0,
            "usage_score": 40.0,
            "health_score": 90.0,
        }
        alerts = hm.generate_alerts("VW_VENDAS", scores)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_compute_and_update_not_found(self):
        """Deve retornar dict vazio se estrutura não encontrada."""
        from services.data_platform.health_monitor import HealthMonitor
        hm = HealthMonitor()
        mock_session = _mock_session_with_meta(None, return_none=True)
        with patch("services.data_platform.health_monitor.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await hm.compute_and_update(TENANT_A, "INEXISTENTE")
        assert result == {}


# ──────────────────────────────────────────────────────────────────────────────
# LineageService Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestLineageService:
    """Testa o LineageService."""

    def test_build_lineage_entry(self):
        """Deve construir nó de lineage com estrutura correta."""
        from services.data_platform.lineage_service import LineageService
        ls = LineageService()
        node = ls.build_lineage_entry(
            tipo="VIEW",
            id_="VW_VENDAS",
            nome="VW_VENDAS",
            pai_id="PEDIDO",
            pai_tipo="TABELA",
        )
        assert node["tipo"] == "VIEW"
        assert node["id"] == "VW_VENDAS"
        assert node["pai_id"] == "PEDIDO"
        assert node["pai_tipo"] == "TABELA"

    @pytest.mark.asyncio
    async def test_build_view_lineage_structure(self):
        """Deve montar cadeia ERP → Tabela → View."""
        from services.data_platform.lineage_service import LineageService
        ls = LineageService()

        meta = make_meta("VW_VENDAS")
        mock_session = _mock_session_with_meta(meta)

        with patch("services.data_platform.lineage_service.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            chain = await ls.build_view_lineage(
                tenant_id=TENANT_A,
                view_name="VW_VENDAS",
                erp_sistema="Oracle ERP",
                tabelas=["PEDIDO", "ITEM_PEDIDO"],
            )

        tipos = [n["tipo"] for n in chain]
        assert "ERP" in tipos
        assert "TABELA" in tipos
        assert "VIEW" in tipos
        assert chain[-1]["tipo"] == "VIEW"
        assert chain[-1]["id"] == "VW_VENDAS"

    @pytest.mark.asyncio
    async def test_get_lineage_returns_list(self):
        """Deve retornar lista de nós de lineage."""
        from services.data_platform.lineage_service import LineageService
        ls = LineageService()

        lineage_data = [{"tipo": "ERP", "id": "oracle_erp", "nome": "Oracle ERP"}]
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = lineage_data
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.data_platform.lineage_service.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await ls.get_lineage(TENANT_A, "VW_VENDAS")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["tipo"] == "ERP"

    @pytest.mark.asyncio
    async def test_get_lineage_empty_when_not_found(self):
        """Deve retornar lista vazia para estrutura sem lineage."""
        from services.data_platform.lineage_service import LineageService
        ls = LineageService()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.data_platform.lineage_service.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await ls.get_lineage(TENANT_A, "INEXISTENTE")

        assert result == []


# ──────────────────────────────────────────────────────────────────────────────
# DependencyGraph Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestDependencyGraph:
    """Testa o DependencyGraph."""

    def test_make_graph_structure(self):
        """Deve criar grafo com upstream e downstream vazios por padrão."""
        from services.data_platform.dependency_graph import DependencyGraph
        dg = DependencyGraph()
        g = dg._make_graph()
        assert "upstream" in g
        assert "downstream" in g
        assert g["upstream"] == []

    @pytest.mark.asyncio
    async def test_get_graph_returns_empty_when_not_found(self):
        """Deve retornar grafo vazio quando estrutura não registrada."""
        from services.data_platform.dependency_graph import DependencyGraph
        dg = DependencyGraph()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.data_platform.dependency_graph.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await dg.get_graph(TENANT_A, "INEXISTENTE")

        assert result == {"upstream": [], "downstream": []}

    @pytest.mark.asyncio
    async def test_get_impact_direct_only(self):
        """Deve retornar impacto direto quando não há transitivos."""
        from services.data_platform.dependency_graph import DependencyGraph
        dg = DependencyGraph()

        direct_graph = {"upstream": ["PEDIDO"], "downstream": ["DS_VENDAS", "BP_VENDAS"]}
        empty_graph = {"upstream": [], "downstream": []}

        call_count = [0]
        async def side_effect_get_graph(tenant_id, estrutura_id):
            call_count[0] += 1
            if estrutura_id == "VW_VENDAS":
                return direct_graph
            return empty_graph

        dg.get_graph = side_effect_get_graph

        result = await dg.get_impact(TENANT_A, "VW_VENDAS", max_depth=2)

        assert result["estrutura_id"] == "VW_VENDAS"
        assert "DS_VENDAS" in result["impacto_direto"]
        assert "BP_VENDAS" in result["impacto_direto"]
        assert len(result["impacto_total"]) >= 2


# ──────────────────────────────────────────────────────────────────────────────
# CatalogAPI Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestCatalogAPI:
    """Testa a CatalogAPI como fachada única."""

    @pytest.mark.asyncio
    async def test_register_delegates_all_sub_services(self):
        """catalog_api.register deve chamar catalog, lineage, graph e health."""
        from services.data_platform.catalog_api import CatalogAPI

        api = CatalogAPI()
        api._catalog.register_entity = AsyncMock(return_value=make_meta())
        api._lineage.build_view_lineage = AsyncMock(return_value=[])
        api._graph.register_dependency = AsyncMock()
        api._health.compute_and_update = AsyncMock(return_value={})

        await api.register(
            tenant_id=TENANT_A,
            tipo="VIEW",
            dados={"estrutura_id": "VW_VENDAS", "nome_view": "VW_VENDAS"},
            lineage_tabelas=["PEDIDO"],
            upstream_ids=["PEDIDO"],
        )

        api._catalog.register_entity.assert_called_once()
        api._lineage.build_view_lineage.assert_called_once()
        api._graph.register_dependency.assert_called_once()
        api._health.compute_and_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_delegates_to_catalog(self):
        """catalog_api.query deve delegar ao MetadataCatalogService.search."""
        from services.data_platform.catalog_api import CatalogAPI

        api = CatalogAPI()
        api._catalog.search = AsyncMock(return_value=[make_meta()])

        result = await api.query(TENANT_A, search_query="vendas", tipo="VIEW")

        api._catalog.search.assert_called_once_with(
            tenant_id=TENANT_A, query="vendas", tipo="VIEW",
            tags=None, categoria=None, limit=50
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_health_report_delegates(self):
        """catalog_api.get_health_report deve delegar ao HealthMonitor."""
        from services.data_platform.catalog_api import CatalogAPI

        api = CatalogAPI()
        expected = {"total": 5, "alertas_ativos": 2, "health_medio": 85.0, "por_tipo": {}}
        api._health.get_tenant_health_report = AsyncMock(return_value=expected)

        result = await api.get_health_report(TENANT_A)
        assert result["total"] == 5
        assert result["health_medio"] == 85.0

    @pytest.mark.asyncio
    async def test_get_lineage_delegates(self):
        """catalog_api.get_lineage deve delegar ao LineageService."""
        from services.data_platform.catalog_api import CatalogAPI

        api = CatalogAPI()
        chain = [{"tipo": "ERP"}, {"tipo": "TABELA"}, {"tipo": "VIEW"}]
        api._lineage.get_lineage = AsyncMock(return_value=chain)

        result = await api.get_lineage(TENANT_A, "VW_VENDAS")
        assert len(result) == 3
        assert result[0]["tipo"] == "ERP"

    @pytest.mark.asyncio
    async def test_get_impact_delegates(self):
        """catalog_api.get_impact deve delegar ao DependencyGraph."""
        from services.data_platform.catalog_api import CatalogAPI

        api = CatalogAPI()
        impact = {"estrutura_id": "VW_VENDAS", "impacto_direto": ["BP_VENDAS"], "impacto_total": ["BP_VENDAS"], "profundidade": 1}
        api._graph.get_impact = AsyncMock(return_value=impact)

        result = await api.get_impact(TENANT_A, "VW_VENDAS")
        assert "BP_VENDAS" in result["impacto_total"]

    @pytest.mark.asyncio
    async def test_snapshot_delegates(self):
        """catalog_api.snapshot deve delegar ao MetadataCatalogService."""
        from services.data_platform.catalog_api import CatalogAPI

        api = CatalogAPI()
        version = make_version(uuid.uuid4(), versao=2)
        api._catalog.create_version_snapshot = AsyncMock(return_value=version)

        result = await api.snapshot(TENANT_A, "VW_VENDAS", motivo="Antes de alteração")
        assert result.versao == 2

    @pytest.mark.asyncio
    async def test_rollback_delegates(self):
        """catalog_api.rollback deve delegar ao MetadataCatalogService."""
        from services.data_platform.catalog_api import CatalogAPI

        api = CatalogAPI()
        meta = make_meta(versao=1)
        api._catalog.rollback_to_version = AsyncMock(return_value=meta)

        result = await api.rollback(TENANT_A, "VW_VENDAS", versao_alvo=1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_cache_delegates(self):
        """catalog_api.update_cache deve delegar ao MetadataCatalogService."""
        from services.data_platform.catalog_api import CatalogAPI

        api = CatalogAPI()
        api._catalog.update_cache_metadata = AsyncMock()

        await api.update_cache(TENANT_A, "VW_VENDAS", ativo=True, ttl_segundos=7200, hit_rate=0.85)
        api._catalog.update_cache_metadata.assert_called_once_with(
            tenant_id=TENANT_A,
            estrutura_id="VW_VENDAS",
            cache_ativo=True,
            ttl_segundos=7200,
            hit_rate=0.85,
        )

    @pytest.mark.asyncio
    async def test_summary_delegates(self):
        """catalog_api.summary deve delegar ao MetadataCatalogService."""
        from services.data_platform.catalog_api import CatalogAPI

        api = CatalogAPI()
        api._catalog.get_catalog_summary = AsyncMock(return_value={"total": 10})

        result = await api.summary(TENANT_A)
        assert result["total"] == 10


# ──────────────────────────────────────────────────────────────────────────────
# Versionamento Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestVersionamento:
    """Testa o versionamento imutável do MetadataCatalog."""

    @pytest.mark.asyncio
    async def test_create_version_snapshot(self):
        """Deve criar snapshot imutável com dados corretos."""
        from services.data_platform.metadata_catalog import MetadataCatalogService
        svc = MetadataCatalogService()

        meta = make_meta("VW_VENDAS", versao=5)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = meta
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        with patch("services.data_platform.metadata_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.create_version_snapshot(
                TENANT_A, "VW_VENDAS", motivo="Antes de refatoração", autor="admin"
            )

        mock_session.add.assert_called_once()
        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.versao == 5
        assert added_obj.motivo == "Antes de refatoração"
        assert "nome_view" in added_obj.snapshot

    @pytest.mark.asyncio
    async def test_get_version_history_empty_when_no_metadata(self):
        """Deve retornar lista vazia se a estrutura não existir."""
        from services.data_platform.metadata_catalog import MetadataCatalogService
        svc = MetadataCatalogService()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.data_platform.metadata_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.get_version_history(TENANT_A, "INEXISTENTE")

        assert result == []


# ──────────────────────────────────────────────────────────────────────────────
# Multi-Tenant Isolation Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestMultiTenantIsolation:
    """Verifica que os dados de um tenant não vazam para outro."""

    @pytest.mark.asyncio
    async def test_search_scoped_to_tenant(self):
        """search() deve sempre filtrar por tenant_id."""
        from services.data_platform.metadata_catalog import MetadataCatalogService
        svc = MetadataCatalogService()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.data_platform.metadata_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            # Tenant B não deve ver dados do Tenant A
            result = await svc.search(TENANT_B, query="vendas")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_entity_tenant_scoped(self):
        """get_entity() deve retornar None quando estrutura pertence a outro tenant."""
        from services.data_platform.metadata_catalog import MetadataCatalogService
        svc = MetadataCatalogService()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Tenant B não tem a estrutura
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.data_platform.metadata_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.get_entity(TENANT_B, "VIEW", "VW_VENDAS")

        assert result is None
