"""
Testes de Integração: View Manager & Semantic Catalog
----------------------------------------------------
Valida os fluxos ponta a ponta dos dois novos módulos da Data Platform.

Cobertura:
 1. SemanticCatalogService — registro, resolução por sinônimo, listagem
 2. ViewManager — criação, atualização, reconstrução automática
 3. Integração BusinessLayer + SemanticCatalog (cache de sinônimos)
 4. Integração DashboardBuilder — enriquecimento semântico do layout_schema
 5. sync_from_semantic_catalog — sincronização startup com _BUSINESS_DICT
"""
from __future__ import annotations

import json
import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# ─── UUIDs de teste ───────────────────────────────────────────────────────────
TENANT_ID = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")

# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_semantic_concept(
    nome: str,
    sinonimos: list[str],
    descricao: str = "Descrição de teste do conceito de negócio.",
    categoria: str = "Financeiro",
    tipo: str = "Fato",
    unidade: str = "R$",
    formato: str = "currency",
    metodo_agregacao: str = "Soma",
    versao: int = 1,
) -> MagicMock:
    obj = MagicMock()
    obj.nome_oficial = nome
    obj.descricao = descricao
    obj.sinonimos = sinonimos
    obj.categoria = categoria
    obj.tipo = tipo
    obj.unidade = unidade
    obj.formato = formato
    obj.metodo_agregacao = metodo_agregacao
    obj.versao = versao
    obj.contexto = None
    obj.kpis_relacionados = []
    obj.indicadores_derivados = []
    obj.visualizacoes_recomendadas = []
    obj.restricoes = []
    obj.permissoes = []
    return obj


def make_view_catalog(nome: str, tipo_grafico: str = "BAR") -> MagicMock:
    obj = MagicMock()
    obj.nome_view_oracle = nome
    obj.descricao_para_ia = f"Esta é a view analítica {nome} com pelo menos vinte caracteres de descrição"
    obj.tipo_grafico_padrao = MagicMock()
    obj.tipo_grafico_padrao.value = tipo_grafico
    obj.parametros_schema = {}
    obj.ativo = True
    return obj


def make_metadata_catalog(nome: str, versao: int = 1) -> MagicMock:
    obj = MagicMock()
    obj.nome_view = nome
    obj.versao = versao
    obj.status = "success"
    obj.integridade = "valid"
    obj.hash_integridade = "abc123"
    obj.tabelas_utilizadas = ["VW_VENDAS"]
    return obj


# ──────────────────────────────────────────────────────────────────────────────
# SemanticCatalogService Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestSemanticCatalogService:
    """Testa o SemanticCatalogService isolado."""

    @pytest.mark.asyncio
    async def test_get_concept_found(self):
        """Deve retornar o conceito pelo nome oficial."""
        from services.data_platform.semantic_catalog import SemanticCatalogService
        svc = SemanticCatalogService()

        concept = make_semantic_concept("receita_total", ["faturamento", "vendas"])
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = concept
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.data_platform.semantic_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.get_concept(TENANT_ID, "receita_total")

        assert result is not None
        assert result.nome_oficial == "receita_total"

    @pytest.mark.asyncio
    async def test_get_concept_not_found(self):
        """Deve retornar None para conceito inexistente."""
        from services.data_platform.semantic_catalog import SemanticCatalogService
        svc = SemanticCatalogService()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.data_platform.semantic_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.get_concept(TENANT_ID, "metrica_inexistente")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_by_synonym_direct(self):
        """Deve resolver o nome oficial direto sem passar por sinônimos."""
        from services.data_platform.semantic_catalog import SemanticCatalogService
        svc = SemanticCatalogService()

        mock_session = AsyncMock()
        # Busca direta retorna o nome oficial diretamente
        mock_direct_result = MagicMock()
        mock_direct_result.scalar.return_value = "receita_total"
        mock_session.execute = AsyncMock(return_value=mock_direct_result)

        with patch("services.data_platform.semantic_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.resolve_concept_by_synonym(TENANT_ID, "receita_total")

        assert result == "receita_total"

    @pytest.mark.asyncio
    async def test_resolve_by_synonym_via_list(self):
        """Deve resolver o nome oficial varrendo sinônimos quando busca direta não bater."""
        from services.data_platform.semantic_catalog import SemanticCatalogService
        svc = SemanticCatalogService()

        concept = make_semantic_concept("receita_total", ["faturamento", "vendas totais", "total de vendas"])

        mock_session = AsyncMock()
        # Primeira chamada (busca direta) — não encontra
        mock_direct = MagicMock()
        mock_direct.scalar.return_value = None
        # Segunda chamada (busca all) — retorna o conceito
        mock_all = MagicMock()
        mock_all.scalars.return_value.all.return_value = [concept]

        mock_session.execute = AsyncMock(side_effect=[mock_direct, mock_all])

        with patch("services.data_platform.semantic_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.resolve_concept_by_synonym(TENANT_ID, "faturamento")

        assert result == "receita_total"

    @pytest.mark.asyncio
    async def test_resolve_synonym_case_insensitive(self):
        """Resolução de sinônimos deve ser case-insensitive."""
        from services.data_platform.semantic_catalog import SemanticCatalogService
        svc = SemanticCatalogService()

        concept = make_semantic_concept("receita_total", ["FATURAMENTO", "Vendas Totais"])

        mock_session = AsyncMock()
        mock_direct = MagicMock()
        mock_direct.scalar.return_value = None
        mock_all = MagicMock()
        mock_all.scalars.return_value.all.return_value = [concept]
        mock_session.execute = AsyncMock(side_effect=[mock_direct, mock_all])

        with patch("services.data_platform.semantic_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.resolve_concept_by_synonym(TENANT_ID, "faturamento")

        assert result == "receita_total"

    @pytest.mark.asyncio
    async def test_list_concepts(self):
        """Deve listar todos os conceitos do tenant."""
        from services.data_platform.semantic_catalog import SemanticCatalogService
        svc = SemanticCatalogService()

        concepts = [
            make_semantic_concept("receita_total", []),
            make_semantic_concept("lucro_bruto", []),
            make_semantic_concept("ticket_medio", []),
        ]

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = concepts
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("services.data_platform.semantic_catalog.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await svc.list_concepts(TENANT_ID)

        assert len(result) == 3
        nomes = [c.nome_oficial for c in result]
        assert "receita_total" in nomes
        assert "lucro_bruto" in nomes

    @pytest.mark.asyncio
    async def test_register_concept_create(self):
        """Deve criar um novo conceito no SemanticCatalog."""
        from services.data_platform.semantic_catalog import SemanticCatalogService
        svc = SemanticCatalogService()

        concept_data = {
            "nome_oficial": "novo_kpi",
            "descricao": "KPI de teste criado no SemanticCatalog.",
            "sinonimos": ["kpi_teste", "indicador_teste"],
            "categoria": "Operacional",
            "tipo": "Indicador",
            "unidade": "un",
            "formato": "integer",
            "metodo_agregacao": "Contagem",
        }

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("services.data_platform.semantic_catalog.get_db_context") as mock_ctx, \
             patch("services.data_platform.semantic_catalog.history_service") as mock_history:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_history.log_change = AsyncMock()

            result = await svc.register_concept(TENANT_ID, concept_data)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_history.log_change.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_concept_update(self):
        """Deve incrementar versão ao atualizar um conceito existente."""
        from services.data_platform.semantic_catalog import SemanticCatalogService
        svc = SemanticCatalogService()

        existing = make_semantic_concept("receita_total", ["faturamento"], versao=2)

        concept_data = {
            "nome_oficial": "receita_total",
            "descricao": "Descrição atualizada.",
            "sinonimos": ["faturamento", "receita bruta"],
        }

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("services.data_platform.semantic_catalog.get_db_context") as mock_ctx, \
             patch("services.data_platform.semantic_catalog.history_service") as mock_history:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_history.log_change = AsyncMock()

            await svc.register_concept(TENANT_ID, concept_data)

        # Versão deve ser incrementada
        assert existing.versao == 3
        mock_session.commit.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# ViewManager Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestViewManager:
    """Testa o ViewManager isolado."""

    @pytest.mark.asyncio
    async def test_create_analytical_view(self):
        """Deve criar view analítica no ViewCatalog e MetadataCatalog."""
        from services.data_platform.view_manager import ViewManager
        vm = ViewManager()

        view_data = {
            "nome_view_oracle": "VW_TESTE_VENDAS",
            "descricao_para_ia": "Esta é a view de teste de vendas com pelo menos 20 chars",
            "tipo_grafico_padrao": "BAR",
            "parametros_schema": {"data_inicio": "string", "data_fim": "string"},
            "tabelas_utilizadas": ["PEDIDO", "ITEM_PEDIDO"],
            "campos_utilizados": ["dt_emissao", "vl_total"],
            "kpis_suportados": ["receita_total", "quantidade_pedidos"],
        }

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("services.data_platform.view_manager.get_db_context") as mock_ctx, \
             patch("services.data_platform.view_manager.history_service") as mock_hist, \
             patch("services.data_platform.view_manager.integrity_service") as mock_int:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_hist.log_change = AsyncMock()
            mock_int.calculate_integrity_hash.return_value = "hash_teste_abc"

            result = await vm.create_analytical_view(TENANT_ID, view_data)

        # Dois add: ViewCatalog + MetadataCatalog
        assert mock_session.add.call_count == 2
        mock_session.commit.assert_called_once()
        mock_hist.log_change.assert_called_once()
        call_args = mock_hist.log_change.call_args[1]
        assert call_args["acao"] == "CREATE"

    @pytest.mark.asyncio
    async def test_reconstruct_view_increments_version(self):
        """Deve incrementar versão e migrar blueprints dependentes."""
        from services.data_platform.view_manager import ViewManager
        vm = ViewManager()

        meta = make_metadata_catalog("VW_VENDAS", versao=3)
        view = make_view_catalog("VW_VENDAS")

        mock_blueprint = MagicMock()
        mock_blueprint.intent_id = "bp_vendas_dia"
        mock_blueprint.view_name = "VW_VENDAS"
        mock_blueprint.version = 3

        mock_session = AsyncMock()

        def execute_side_effect(stmt):
            r = MagicMock()
            # Detecta qual query está sendo executada pelo tipo do resultado esperado
            # Retornamos objetos diferentes baseado na ordem de chamada
            return r

        # Configura mocks de result para sequência correta
        meta_result = MagicMock()
        meta_result.scalar_one_or_none.return_value = meta
        view_result = MagicMock()
        view_result.scalar_one.return_value = view
        bp_result = MagicMock()
        bp_result.scalars.return_value.all.return_value = [mock_blueprint]

        mock_session.execute = AsyncMock(side_effect=[meta_result, view_result, bp_result])
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("services.data_platform.view_manager.get_db_context") as mock_ctx, \
             patch("services.data_platform.view_manager.history_service") as mock_hist, \
             patch("services.data_platform.view_manager.integrity_service") as mock_int:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_hist.log_change = AsyncMock()
            mock_int.calculate_integrity_hash.return_value = "hash_reconstruct"

            result = await vm.reconstruct_view(TENANT_ID, "VW_VENDAS", "Alteração de schema no ERP")

        assert result["status"] == "success"
        assert result["versao"] == 4
        assert meta.versao == 4
        assert meta.status == "reconstructed"
        assert mock_blueprint.version == 4
        mock_hist.log_change.assert_called_once()
        call_args = mock_hist.log_change.call_args[1]
        assert call_args["acao"] == "RECONSTRUCT"
        assert call_args["detalhes"]["versao_anterior"] == 3
        assert call_args["detalhes"]["versao_nova"] == 4

    @pytest.mark.asyncio
    async def test_reconstruct_view_not_found_raises(self):
        """Deve lançar ValueError se o MetadataCatalog não for encontrado."""
        from services.data_platform.view_manager import ViewManager
        vm = ViewManager()

        mock_session = AsyncMock()
        meta_result = MagicMock()
        meta_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=meta_result)

        with patch("services.data_platform.view_manager.get_db_context") as mock_ctx, \
             patch("services.data_platform.view_manager.integrity_service"):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ValueError, match="MetadataCatalog não encontrado"):
                await vm.reconstruct_view(TENANT_ID, "VW_INEXISTENTE", "teste")

    @pytest.mark.asyncio
    async def test_update_analytical_view(self):
        """Deve atualizar view e incrementar versão."""
        from services.data_platform.view_manager import ViewManager
        vm = ViewManager()

        view = make_view_catalog("VW_VENDAS")
        meta = make_metadata_catalog("VW_VENDAS", versao=1)

        view_result = MagicMock()
        view_result.scalar_one.return_value = view
        meta_result = MagicMock()
        meta_result.scalar_one.return_value = meta

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[view_result, meta_result])
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        updates = {
            "kpis_suportados": ["receita_total", "ticket_medio", "lucro_bruto"],
            "ativo": True,
        }

        with patch("services.data_platform.view_manager.get_db_context") as mock_ctx, \
             patch("services.data_platform.view_manager.history_service") as mock_hist, \
             patch("services.data_platform.view_manager.integrity_service") as mock_int:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_hist.log_change = AsyncMock()
            mock_int.calculate_integrity_hash.return_value = "hash_updated"

            await vm.update_analytical_view(TENANT_ID, "VW_VENDAS", updates)

        assert meta.versao == 2
        assert meta.kpis_suportados == ["receita_total", "ticket_medio", "lucro_bruto"]
        mock_hist.log_change.assert_called_once()
        call_args = mock_hist.log_change.call_args[1]
        assert call_args["acao"] == "UPDATE"


# ──────────────────────────────────────────────────────────────────────────────
# BusinessLayer + SemanticCatalog Integration
# ──────────────────────────────────────────────────────────────────────────────

class TestBusinessLayerSemanticIntegration:
    """Testa a resolução de sinônimos do BusinessLayer com cache do SemanticCatalog."""

    def test_resolve_synonym_static_fallback(self):
        """Deve resolver sinônimos via dicionário estático quando cache dinâmico está vazio."""
        from services.data_platform.business_layer import BusinessLayer, _SYNONYM_CACHE
        _SYNONYM_CACHE.clear()

        bl = BusinessLayer()
        assert bl._resolve_synonym_local("faturamento") == "receita_total"
        assert bl._resolve_synonym_local("faturamento_total") == "receita_total"
        assert bl._resolve_synonym_local("lucro") == "lucro_bruto"
        assert bl._resolve_synonym_local("margem") == "margem_lucro"
        assert bl._resolve_synonym_local("ticket") == "ticket_medio"
        assert bl._resolve_synonym_local("pedidos") == "quantidade_pedidos"

    def test_resolve_synonym_dynamic_cache_priority(self):
        """O cache dinâmico do SemanticCatalog deve ter prioridade sobre o fallback estático."""
        from services.data_platform.business_layer import BusinessLayer, _SYNONYM_CACHE
        _SYNONYM_CACHE.clear()

        # Simula o SemanticCatalog populando o cache
        _SYNONYM_CACHE["faturamento"] = "receita_liquida"  # Override dinâmico
        _SYNONYM_CACHE["receita bruta"] = "receita_total"

        bl = BusinessLayer()
        # Cache dinâmico deve ter prioridade
        assert bl._resolve_synonym_local("faturamento") == "receita_liquida"
        assert bl._resolve_synonym_local("receita bruta") == "receita_total"
        # Sinônimos não sobrepostos ainda usam fallback
        assert bl._resolve_synonym_local("lucro") == "lucro_bruto"

        # Limpa cache ao final
        _SYNONYM_CACHE.clear()

    @pytest.mark.asyncio
    async def test_apply_business_rules_normalizes_metrics(self):
        """apply_business_rules deve normalizar sinônimos e retornar métricas padronizadas."""
        from services.data_platform.business_layer import BusinessLayer, _SYNONYM_CACHE
        _SYNONYM_CACHE.clear()

        bl = BusinessLayer()

        plan = MagicMock()
        plan.metrics = ["faturamento", "receita_total", "lucro"]
        plan.group_by = []
        plan.filters = MagicMock()

        result = await bl.apply_business_rules(plan)
        metrics = result.metrics
        assert "receita_total" in metrics
        assert "lucro_bruto" in metrics
        assert "faturamento" not in metrics


# ──────────────────────────────────────────────────────────────────────────────
# DashboardBuilder Semantic Enrichment
# ──────────────────────────────────────────────────────────────────────────────

class TestDashboardBuilderSemanticEnrichment:
    """Testa o enriquecimento semântico do DashboardBuilder."""

    def test_build_semantic_context_soma(self):
        """Deve gerar contexto semântico para operação SOMA."""
        from services.data_platform.dashboard_builder import DashboardBuilder
        db_builder = DashboardBuilder()

        intention = MagicMock()
        intention.operacao = "SOMA"
        intention.entidade_alvo = "VENDA"

        ctx = db_builder._build_semantic_context(intention, None)

        assert ctx["metodo_agregacao"] == "Soma"
        assert ctx["formato_padrao"]["unit"] == "R$"
        assert ctx["cor_semantica"] == "#4F46E5"
        assert ctx["icone_padrao"] == "currency"

    def test_build_semantic_context_contagem(self):
        """Deve gerar contexto semântico para operação CONTAGEM."""
        from services.data_platform.dashboard_builder import DashboardBuilder
        db_builder = DashboardBuilder()

        intention = MagicMock()
        intention.operacao = "CONTAGEM"
        intention.entidade_alvo = "CLIENTE"

        ctx = db_builder._build_semantic_context(intention, None)

        assert ctx["metodo_agregacao"] == "Contagem"
        assert ctx["formato_padrao"]["decimals"] == 0
        assert ctx["cor_semantica"] == "#059669"
        assert ctx["icone_padrao"] == "users"

    def test_resolve_icon_venda(self):
        """Deve resolver ícone 'currency' para entidade VENDA."""
        from services.data_platform.dashboard_builder import DashboardBuilder
        db_builder = DashboardBuilder()
        assert db_builder._resolve_icon("VENDA") == "currency"
        assert db_builder._resolve_icon("CLIENTE") == "users"
        assert db_builder._resolve_icon("VENDEDOR") == "star"
        assert db_builder._resolve_icon("PRODUTO") == "ticket"
        assert db_builder._resolve_icon(None) == "chart"
        assert db_builder._resolve_icon("DESCONHECIDO") == "chart"


# ──────────────────────────────────────────────────────────────────────────────
# sync_from_semantic_catalog
# ──────────────────────────────────────────────────────────────────────────────

class TestSyncFromSemanticCatalog:
    """Testa a sincronização startup do SemanticCatalog com o _BUSINESS_DICT."""

    @pytest.mark.asyncio
    async def test_sync_populates_business_dict(self):
        """Deve adicionar conceitos do banco ao _BUSINESS_DICT."""
        from services import semantic_layer as sl
        from services.data_platform.business_layer import _SYNONYM_CACHE

        _SYNONYM_CACHE.clear()

        concepts = [
            make_semantic_concept(
                "receita_total",
                ["faturamento", "total vendas"],
                descricao="Receita total de vendas aprovadas."
            ),
            make_semantic_concept(
                "lucro_operacional",
                ["lucro op"],
                descricao="Lucro operacional da empresa."
            ),
        ]

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = concepts
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("database.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            count = await sl.sync_from_semantic_catalog(str(TENANT_ID))

        assert count == 2
        # Deve estar no _BUSINESS_DICT
        assert "receita_total" in sl._BUSINESS_DICT
        assert "lucro_operacional" in sl._BUSINESS_DICT
        # Deve estar no cache de sinônimos do BusinessLayer
        assert _SYNONYM_CACHE.get("faturamento") == "receita_total"
        assert _SYNONYM_CACHE.get("total vendas") == "receita_total"
        assert _SYNONYM_CACHE.get("lucro op") == "lucro_operacional"

        _SYNONYM_CACHE.clear()

    @pytest.mark.asyncio
    async def test_sync_handles_db_error_gracefully(self):
        """Deve retornar 0 sem lançar exceção quando o banco falhar."""
        from services import semantic_layer as sl

        with patch("database.get_db_context") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(side_effect=Exception("DB offline"))
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            count = await sl.sync_from_semantic_catalog(str(TENANT_ID))

        assert count == 0
