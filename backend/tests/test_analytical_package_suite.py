"""
LuminaAI — Test Suite: Analytical Package Layer
-------------------------------------------------
Cobertura completa dos componentes do Analytical Package Layer.

Testa:
- IntentFingerprintGenerator: geração e compatibilidade de fingerprints
- PackageCompatibilityEngine: detecção de Packages compatíveis
- AnalyticalPackageService: lifecycle completo (criação, reuso, scores)
- PackageVersionManager: versionamento e breaking changes
- PackageCacheIntelligence: cache L1 (hit/miss/expire/invalidate)
- Integração: MISS cria Package, HIT reutiliza Package

Premissas:
- Fingerprint NUNCA usa texto literal — sempre conceitos semânticos
- Período temporal é variável — não quebra compatibilidade
- Etapa 0 no QIE é não-bloqueante
- Isolamento por tenant é obrigatório
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def other_tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def package_id() -> uuid.UUID:
    return uuid.uuid4()


def _make_mock_intention(
    operacao: str = "SOMA",
    entidade: str = "VENDA",
    confianca: float = 0.95,
    is_comparacao: bool = False,
    visualizacao: str = "KPI",
    periodo: str = "mes",
) -> MagicMock:
    intention = MagicMock()
    intention.operacao = operacao
    intention.entidade_alvo = entidade
    intention.confianca = confianca
    intention.is_comparacao = is_comparacao
    intention.visualizacao_preferida = visualizacao
    intention.periodo_referencia = periodo
    intention.justificativa = "Análise de teste"
    intention.parametros = {}

    structured = MagicMock()
    structured.query_type = "AGGREGATION"
    structured.metrics = ["receita_total", "quantidade"]
    structured.group_by = []
    filters = MagicMock()
    filters.date_range = "2026-07-01 to 2026-07-31"
    filters.products = []
    filters.customers = []
    filters.regions = []
    structured.filters = filters
    vis = MagicMock()
    vis.type = visualizacao
    vis.layout_priority = "ALTA"
    structured.visualization = vis
    intention.plano_estruturado = structured

    return intention


def _make_mock_plan(view_name: str = "VW_VENDAS") -> MagicMock:
    plan = MagicMock()
    principal = MagicMock()
    principal.view_name = view_name
    principal.view_catalog_id = None
    principal.parametros = {}
    plan.consulta_principal = principal
    plan.items_secundarios = []
    return plan


def _make_mock_package(
    tenant_id: uuid.UUID,
    intent_key: str = "abc123",
    domain: str = "VENDAS",
    operation: str = "AGGREGATION",
    entity: str = "GERAL",
    status_str: str = "ACTIVE",
    usage_count: int = 5,
) -> MagicMock:
    """Cria um mock de AnalyticalPackage para testes."""
    from models.analytical_package import PackageStatus

    pkg = MagicMock()
    pkg.id = uuid.uuid4()
    pkg.tenant_id = tenant_id
    pkg.intent_key = intent_key
    pkg.intent_fingerprint = {
        "intent_key": intent_key,
        "domain": domain,
        "operation": operation,
        "entity": entity,
        "granularity": "MENSAL",
        "metrics": ["receita_total"],
        "group_by": [],
        "analysis_type": "AGGREGATION",
    }
    pkg.semantic_context = {"domain": domain, "operation": operation}
    pkg.visual_strategy = {"primary_chart_type": "KPI", "layout_order": ["kpi_cards"]}
    pkg.interaction_strategy = {}
    pkg.analytical_structure = {"metrics": ["receita_total"], "group_by": [], "query_type": "AGGREGATION"}
    pkg.blueprint_id = "bp_test_v1"
    pkg.blueprint_snapshot = {}
    pkg.view_names = ["VW_VENDAS"]
    pkg.status = PackageStatus.ACTIVE if status_str == "ACTIVE" else PackageStatus.DEPRECATED
    pkg.version = 1
    pkg.quality_score = 0.9
    pkg.health_score = 0.95
    pkg.usage_count = usage_count
    pkg.last_used_at = None
    pkg.avg_execution_time_ms = 250.0
    pkg.error_count = 0
    pkg.dependencies = {"view_names": ["VW_VENDAS"]}
    pkg.compatible_fingerprints = [intent_key]
    pkg.created_by = "AI_PIPELINE"
    pkg.deprecation_reason = None
    pkg.criado_em = datetime.now(timezone.utc)
    pkg.atualizado_em = datetime.now(timezone.utc)
    return pkg


# ── Tests: IntentFingerprintGenerator ─────────────────────────────────────────

class TestIntentFingerprintGenerator:
    """Testes do gerador de fingerprints semânticos."""

    def setup_method(self):
        from services.data_platform.intent_fingerprint import IntentFingerprintGenerator
        self.gen = IntentFingerprintGenerator()

    def test_generate_returns_required_fields(self):
        """Fingerprint deve conter todos os campos obrigatórios."""
        intention = _make_mock_intention()
        plan = _make_mock_plan()

        fp = self.gen.generate(intention, plan, pergunta="Quanto vendemos este mês?")

        assert "intent_key" in fp
        assert "domain" in fp
        assert "operation" in fp
        assert "entity" in fp
        assert "granularity" in fp
        assert "metrics" in fp
        assert "group_by" in fp
        assert "analysis_type" in fp
        assert "time_scope_type" in fp

    def test_intent_key_is_sha256_hex(self):
        """intent_key deve ser um hash SHA-256 de 64 caracteres hexadecimais."""
        intention = _make_mock_intention()
        fp = self.gen.generate(intention, None)
        assert len(fp["intent_key"]) == 64
        assert all(c in "0123456789abcdef" for c in fp["intent_key"])

    def test_domain_mapping_vendas(self):
        """Perguntas de vendas devem mapear para domínio VENDAS."""
        intention = _make_mock_intention(entidade="VENDA")
        plan = _make_mock_plan("VW_VENDAS")
        fp = self.gen.generate(intention, plan, "quanto vendemos")
        assert fp["domain"] == "VENDAS"

    def test_domain_mapping_produtos(self):
        """Perguntas de produtos devem mapear para domínio PRODUTOS."""
        intention = _make_mock_intention(entidade="produto")
        plan = _make_mock_plan("VW_PRODUTOS")
        fp = self.gen.generate(intention, plan, "ranking de produtos")
        assert fp["domain"] == "PRODUTOS"

    def test_operation_ranking(self):
        """Operação RANKING deve ser detectada."""
        intention = _make_mock_intention(operacao="RANKING")
        intention.plano_estruturado.query_type = "RANKING"
        fp = self.gen.generate(intention)
        assert fp["operation"] == "RANKING"

    def test_same_intent_different_period_same_key(self):
        """
        REGRA FUNDAMENTAL: Mesma análise em períodos diferentes deve gerar
        o mesmo intent_key (período é variável, não entra no hash).
        """
        intention_hoje = _make_mock_intention(periodo="hoje")
        intention_ontem = _make_mock_intention(periodo="ontem")
        intention_mes = _make_mock_intention(periodo="mes")

        fp_hoje = self.gen.generate(intention_hoje, None, "vendas hoje")
        fp_ontem = self.gen.generate(intention_ontem, None, "vendas ontem")
        fp_mes = self.gen.generate(intention_mes, None, "vendas do mes")

        # intent_key é o mesmo (mesma análise) — só time_scope_type difere
        assert fp_hoje["intent_key"] == fp_ontem["intent_key"] == fp_mes["intent_key"]
        assert fp_hoje["time_scope_type"] != fp_ontem["time_scope_type"]

    def test_fingerprint_never_contains_literal_query_text(self):
        """
        REGRA FUNDAMENTAL: Fingerprint nunca deve conter o texto literal da pergunta.
        Todos os campos devem ser conceitos normalizados.
        """
        pergunta = "Quanto faturamos nos últimos 30 dias na região sul?"
        intention = _make_mock_intention()
        fp = self.gen.generate(intention, None, pergunta=pergunta)

        # Verifica que nenhum campo contém o texto literal
        fp_str = json.dumps(fp, ensure_ascii=False).lower()
        assert "quanto" not in fp_str
        assert "últimos" not in fp_str
        assert "últimos".lower() not in fp_str
        assert "nos" not in fp_str.split('"intent_key"')[0]  # Exceto no hash

    def test_metrics_normalized(self):
        """Métricas devem ser normalizadas para nomes canônicos."""
        intention = _make_mock_intention()
        intention.plano_estruturado.metrics = ["faturamento", "receita", "qtd_pedidos"]
        fp = self.gen.generate(intention)

        # Faturamento e receita devem ser normalizados para receita_total
        assert "receita_total" in fp["metrics"]
        # Duplicatas devem ser removidas
        assert fp["metrics"].count("receita_total") == 1

    def test_compatibility_score_same_fingerprints(self):
        """Fingerprints idênticos devem ter score de compatibilidade 1.0."""
        intention = _make_mock_intention()
        fp = self.gen.generate(intention)
        score = self.gen.compute_compatibility_score(fp, fp)
        assert score == 1.0

    def test_compatibility_score_different_domain(self):
        """Domínios diferentes devem resultar em score baixo."""
        fp_vendas = {"domain": "VENDAS", "operation": "AGGREGATION", "entity": "GERAL", "granularity": "MENSAL", "metrics": [], "group_by": []}
        fp_estoque = {"domain": "ESTOQUE", "operation": "AGGREGATION", "entity": "GERAL", "granularity": "MENSAL", "metrics": [], "group_by": []}
        score = self.gen.compute_compatibility_score(fp_vendas, fp_estoque)
        assert score < 0.85  # Não deve atingir threshold de reuso

    def test_compatibility_score_same_domain_operation_entity(self):
        """Mesmo domínio + operação + entidade deve atingir threshold de reuso."""
        fp_a = {"domain": "VENDAS", "operation": "AGGREGATION", "entity": "PRODUTO", "granularity": "MENSAL", "metrics": ["receita_total"], "group_by": ["produto"]}
        fp_b = {"domain": "VENDAS", "operation": "AGGREGATION", "entity": "PRODUTO", "granularity": "DIARIA", "metrics": ["receita_total"], "group_by": ["produto"]}
        score = self.gen.compute_compatibility_score(fp_a, fp_b)
        assert score >= 0.85

    def test_comparison_detected(self):
        """Intenção de comparação deve gerar operation=COMPARISON."""
        intention = _make_mock_intention(is_comparacao=True)
        intention.plano_estruturado = None  # Força uso da heurística
        fp = self.gen.generate(intention)
        assert fp["operation"] == "COMPARISON"


# ── Tests: PackageCacheIntelligence ──────────────────────────────────────────

class TestPackageCacheIntelligence:
    """Testes do cache L1 de Packages."""

    def setup_method(self):
        from services.data_platform.package_cache import PackageCacheIntelligence
        self.cache = PackageCacheIntelligence()
        self.tenant_id = uuid.uuid4()

    def test_l1_miss_initially_empty(self):
        """Cache começa vazio — qualquer key é MISS."""
        result = self.cache.l1_get(self.tenant_id, "any_key")
        assert result is None

    def test_l1_set_and_get(self):
        """Dados armazenados devem ser recuperáveis."""
        data = {"domain": "VENDAS", "status": "ACTIVE"}
        self.cache.l1_set(self.tenant_id, "key1", data, ttl=60)
        result = self.cache.l1_get(self.tenant_id, "key1")
        assert result == data

    def test_l1_expire(self):
        """Entradas com TTL expirado devem retornar None."""
        from services.data_platform.package_cache import _CacheEntry
        # Cria entrada já expirada
        entry = _CacheEntry({"data": "old"}, ttl=-1)
        assert entry.is_expired is True

        self.cache._l1[str(self.tenant_id)] = {"key_expired": entry}
        result = self.cache.l1_get(self.tenant_id, "key_expired")
        assert result is None

    def test_l1_invalidate_by_key(self):
        """Invalidação por key deve remover apenas aquela entrada."""
        self.cache.l1_set(self.tenant_id, "key1", {"a": 1}, ttl=60)
        self.cache.l1_set(self.tenant_id, "key2", {"b": 2}, ttl=60)

        self.cache.l1_invalidate(self.tenant_id, "key1")

        assert self.cache.l1_get(self.tenant_id, "key1") is None
        assert self.cache.l1_get(self.tenant_id, "key2") is not None

    def test_l1_invalidate_all_tenant(self):
        """Invalidação sem key deve limpar todo o cache do tenant."""
        self.cache.l1_set(self.tenant_id, "k1", {}, ttl=60)
        self.cache.l1_set(self.tenant_id, "k2", {}, ttl=60)

        self.cache.l1_invalidate(self.tenant_id)

        assert self.cache.l1_get(self.tenant_id, "k1") is None
        assert self.cache.l1_get(self.tenant_id, "k2") is None

    def test_l1_invalidate_by_view(self):
        """Invalidação por view deve remover apenas Packages que dependem dela."""
        pkg_vendas = {"domain": "VENDAS", "view_names": ["VW_VENDAS", "VW_CLIENTES"]}
        pkg_estoque = {"domain": "ESTOQUE", "view_names": ["VW_ESTOQUE"]}

        self.cache.l1_set(self.tenant_id, "key_vendas", pkg_vendas, ttl=60)
        self.cache.l1_set(self.tenant_id, "key_estoque", pkg_estoque, ttl=60)

        # Invalida apenas Packages que dependem de VW_VENDAS
        self.cache.l1_invalidate_by_view(self.tenant_id, "VW_VENDAS")

        assert self.cache.l1_get(self.tenant_id, "key_vendas") is None  # Removido
        assert self.cache.l1_get(self.tenant_id, "key_estoque") is not None  # Mantido

    def test_l1_tenant_isolation(self):
        """Cache de um tenant não deve ser acessível por outro."""
        other_tenant = uuid.uuid4()
        self.cache.l1_set(self.tenant_id, "shared_key", {"secret": True}, ttl=60)

        result = self.cache.l1_get(other_tenant, "shared_key")
        assert result is None

    def test_get_stats(self):
        """Estatísticas devem refletir o estado atual do cache."""
        self.cache.l1_set(self.tenant_id, "k1", {}, ttl=60)
        self.cache.l1_set(self.tenant_id, "k2", {}, ttl=60)

        stats = self.cache.get_stats()

        assert stats["l1_active_entries"] >= 2
        assert stats["l1_tenants"] >= 1
        assert stats["l1_ttl_seconds"] == 300


# ── Tests: PackageVersionManager ─────────────────────────────────────────────

class TestPackageVersionManager:
    """Testes do gerenciador de versões de Packages."""

    def setup_method(self):
        from services.data_platform.package_version_manager import PackageVersionManager
        self.vm = PackageVersionManager()

    def test_detect_no_breaking_changes(self):
        """Blueprints idênticos não devem ter breaking changes."""
        bp = {"view_name": "VW_VENDAS", "metrics": ["receita"], "group_by": [], "tipo_analise": "AGGREGATION"}
        has_breaking, changes = self.vm.detect_breaking_changes(bp, bp)
        assert has_breaking is False
        assert len(changes) == 0

    def test_detect_breaking_change_view_name(self):
        """Mudança de view_name é um breaking change."""
        old_bp = {"view_name": "VW_VENDAS", "metrics": ["receita"], "group_by": []}
        new_bp = {"view_name": "VW_FATURAMENTO", "metrics": ["receita"], "group_by": []}
        has_breaking, changes = self.vm.detect_breaking_changes(old_bp, new_bp)
        assert has_breaking is True
        assert any("view_name" in c for c in changes)

    def test_detect_breaking_change_metric_removed(self):
        """Remoção de métrica é um breaking change."""
        old_bp = {"view_name": "VW_VENDAS", "metrics": ["receita", "custo"], "group_by": []}
        new_bp = {"view_name": "VW_VENDAS", "metrics": ["receita"], "group_by": []}
        has_breaking, changes = self.vm.detect_breaking_changes(old_bp, new_bp)
        assert has_breaking is True
        assert any("métricas" in c or "removidas" in c for c in changes)

    def test_detect_non_breaking_metric_added(self):
        """Adição de nova métrica não é breaking change."""
        old_bp = {"view_name": "VW_VENDAS", "metrics": ["receita"], "group_by": []}
        new_bp = {"view_name": "VW_VENDAS", "metrics": ["receita", "custo"], "group_by": []}
        has_breaking, changes = self.vm.detect_breaking_changes(old_bp, new_bp)
        assert has_breaking is False

    def test_detect_breaking_change_analysis_type(self):
        """Mudança de tipo de análise é um breaking change."""
        old_bp = {"view_name": "VW_VENDAS", "metrics": [], "group_by": [], "tipo_analise": "AGGREGATION"}
        new_bp = {"view_name": "VW_VENDAS", "metrics": [], "group_by": [], "tipo_analise": "SELECT"}
        has_breaking, changes = self.vm.detect_breaking_changes(old_bp, new_bp)
        assert has_breaking is True


# ── Tests: AnalyticalPackageService (Unit) ───────────────────────────────────

class TestAnalyticalPackageServiceUnit:
    """Testes unitários do AnalyticalPackageService (sem banco de dados)."""

    def setup_method(self):
        from services.data_platform.analytical_package_service import AnalyticalPackageService
        self.svc = AnalyticalPackageService()
        self.tenant_id = uuid.uuid4()

    def test_build_semantic_context(self):
        """_build_semantic_context deve extrair campos corretos do fingerprint."""
        intention = _make_mock_intention()
        plan = _make_mock_plan()
        fp = {"domain": "VENDAS", "operation": "AGGREGATION", "entity": "GERAL", "granularity": "MENSAL", "analysis_type": "AGGREGATION"}

        ctx = self.svc._build_semantic_context(intention, plan, fp)

        assert ctx["domain"] == "VENDAS"
        assert ctx["operation"] == "AGGREGATION"
        assert "ia_confianca" in ctx

    def test_build_visual_strategy(self):
        """_build_visual_strategy deve extrair tipo de visualização corretamente."""
        intention = _make_mock_intention(visualizacao="BAR")
        plan = _make_mock_plan()

        vs = self.svc._build_visual_strategy(intention, plan)

        assert vs["primary_chart_type"] == "BAR"
        assert "layout_order" in vs

    def test_build_analytical_structure(self):
        """_build_analytical_structure deve extrair métricas e group_by."""
        intention = _make_mock_intention()
        plan = _make_mock_plan()
        structured = intention.plano_estruturado
        structured.metrics = ["receita_total", "quantidade"]
        structured.group_by = ["produto"]

        structure = self.svc._build_analytical_structure(intention, structured, plan)

        assert "receita_total" in structure["metrics"]
        assert "quantidade" in structure["metrics"]
        assert "produto" in structure["group_by"]

    def test_extract_view_names(self):
        """_extract_view_names deve coletar nomes de views do plano."""
        plan = _make_mock_plan("VW_VENDAS")
        pipeline_result = {
            "datasets": {
                "q1": {"metadata": {"view_name": "VW_CLIENTES"}, "data": []}
            }
        }

        view_names = self.svc._extract_view_names(plan, pipeline_result)

        assert "VW_VENDAS" in view_names
        assert "VW_CLIENTES" in view_names

    def test_serialize_package(self):
        """serialize_package deve retornar dict com todos os campos necessários."""
        pkg = _make_mock_package(self.tenant_id)
        serialized = self.svc.serialize_package(pkg)

        required_fields = ["id", "status", "version", "intent_fingerprint",
                           "quality_score", "health_score", "usage_count",
                           "view_names", "blueprint_id"]
        for field in required_fields:
            assert field in serialized, f"Campo '{field}' ausente no serialize_package"


# ── Tests: AnalyticalPackage ORM Model ───────────────────────────────────────

class TestAnalyticalPackageModel:
    """Testes do modelo ORM AnalyticalPackage."""

    def test_compute_quality_score_high_usage(self):
        """Package muito utilizado e sem erros deve ter quality_score alto."""
        from models.analytical_package import AnalyticalPackage
        pkg = AnalyticalPackage()
        pkg.health_score = 1.0
        pkg.error_count = 0

        score = pkg.compute_quality_score(
            recent_usage=10,
            total_usage=50,
            error_rate=0.0,
            freshness_days=0,
        )

        assert score >= 0.90

    def test_compute_quality_score_stale_data(self):
        """Package com dados muito antigos deve ter quality_score reduzido."""
        from models.analytical_package import AnalyticalPackage
        pkg = AnalyticalPackage()
        pkg.health_score = 0.8
        pkg.error_count = 0

        score_fresh = pkg.compute_quality_score(recent_usage=5, total_usage=10, error_rate=0.0, freshness_days=0)
        score_stale = pkg.compute_quality_score(recent_usage=5, total_usage=10, error_rate=0.0, freshness_days=30)

        assert score_fresh > score_stale

    def test_compute_quality_score_high_errors(self):
        """Package com muitos erros deve ter quality_score reduzido."""
        from models.analytical_package import AnalyticalPackage
        pkg = AnalyticalPackage()
        pkg.health_score = 0.9
        pkg.error_count = 10

        score = pkg.compute_quality_score(
            recent_usage=1,
            total_usage=5,
            error_rate=0.8,  # 80% de taxa de erro
            freshness_days=1,
        )

        assert score < 0.60

    def test_compute_health_score_all_ok(self):
        """Package com todas as verificações positivas deve ter health_score alto."""
        from models.analytical_package import AnalyticalPackage
        pkg = AnalyticalPackage()
        pkg.avg_execution_time_ms = 200.0

        score = pkg.compute_health_score(
            schema_valid=True,
            views_available=True,
            no_breaking_changes=True,
            avg_time_ms=200.0,
        )

        assert score >= 0.90

    def test_compute_health_score_view_unavailable(self):
        """View indisponível deve reduzir significativamente o health_score."""
        from models.analytical_package import AnalyticalPackage
        pkg = AnalyticalPackage()

        score_ok = pkg.compute_health_score(True, True, True, 200.0)
        score_view_down = pkg.compute_health_score(True, False, True, 200.0)

        assert score_ok > score_view_down
        assert score_view_down <= 0.70

    def test_compute_health_score_schema_invalid(self):
        """Schema inválido deve reduzir o health_score abaixo de 0.5."""
        from models.analytical_package import AnalyticalPackage
        pkg = AnalyticalPackage()

        score = pkg.compute_health_score(
            schema_valid=False,
            views_available=False,
            no_breaking_changes=False,
            avg_time_ms=10000.0,
        )

        assert score < 0.20

    def test_package_status_enum_values(self):
        """PackageStatus deve ter todos os valores esperados."""
        from models.analytical_package import PackageStatus

        assert PackageStatus.DRAFT.value == "DRAFT"
        assert PackageStatus.ACTIVE.value == "ACTIVE"
        assert PackageStatus.DEPRECATED.value == "DEPRECATED"
        assert PackageStatus.ARCHIVED.value == "ARCHIVED"


# ── Tests: Integration (MISS → HIT Flow) ─────────────────────────────────────

class TestPackageIntegrationFlow:
    """
    Testes de integração simulando o fluxo completo:
    MISS (primeira execução → cria Package) → HIT (reuso).
    """

    def test_fingerprint_determinism(self):
        """
        Mesma intenção deve sempre gerar o mesmo fingerprint (determinismo).
        Garantia: consultas idênticas → mesmo Package.
        """
        from services.data_platform.intent_fingerprint import IntentFingerprintGenerator
        gen = IntentFingerprintGenerator()

        intention = _make_mock_intention()
        plan = _make_mock_plan()

        fp1 = gen.generate(intention, plan, "vendas do mês")
        fp2 = gen.generate(intention, plan, "vendas do mês")

        assert fp1["intent_key"] == fp2["intent_key"]

    def test_different_analysis_different_fingerprint(self):
        """
        Análises distintas (domínio, operação ou entidade diferente) devem
        gerar fingerprints incompatíveis (score < 0.85).
        """
        from services.data_platform.intent_fingerprint import IntentFingerprintGenerator
        gen = IntentFingerprintGenerator()

        # Análise 1: Ranking de produtos
        intention_ranking = _make_mock_intention(operacao="RANKING", entidade="produto")
        intention_ranking.plano_estruturado.query_type = "RANKING"
        fp_ranking = gen.generate(intention_ranking, _make_mock_plan("VW_PRODUTOS"))

        # Análise 2: Total de vendas por período
        intention_soma = _make_mock_intention(operacao="SOMA", entidade="VENDA")
        intention_soma.plano_estruturado.query_type = "AGGREGATION"
        fp_soma = gen.generate(intention_soma, _make_mock_plan("VW_VENDAS"))

        score = gen.compute_compatibility_score(fp_ranking, fp_soma)
        assert score < 0.85  # Incompatíveis — não devem compartilhar Package

    def test_same_analysis_different_period_compatible(self):
        """
        REGRA FUNDAMENTAL: Mesma análise, período diferente → compatível.
        "Vendas de hoje" e "Vendas do mês" devem compartilhar Package.
        """
        from services.data_platform.intent_fingerprint import IntentFingerprintGenerator
        gen = IntentFingerprintGenerator()

        fp_hoje = gen.generate(_make_mock_intention(periodo="hoje"), _make_mock_plan(), "vendas hoje")
        fp_mes = gen.generate(_make_mock_intention(periodo="mes"), _make_mock_plan(), "vendas do mes")

        # intent_key idêntico (períodos são variáveis)
        assert fp_hoje["intent_key"] == fp_mes["intent_key"]

        # Compatibility score deve atingir threshold
        score = gen.compute_compatibility_score(fp_hoje, fp_mes)
        assert score >= 0.85

    @pytest.mark.asyncio
    async def test_package_service_create_and_serialize(self):
        """AnalyticalPackageService deve criar Package e serializá-lo corretamente."""
        from services.data_platform.analytical_package_service import AnalyticalPackageService
        from services.data_platform.intent_fingerprint import IntentFingerprintGenerator

        svc = AnalyticalPackageService()
        gen = IntentFingerprintGenerator()
        tenant_id = uuid.uuid4()

        intention = _make_mock_intention()
        plan = _make_mock_plan()
        fingerprint = gen.generate(intention, plan)

        pipeline_result = {
            "dashboard_payload": {"kpis": []},
            "datasets": {},
            "analytics_results": {"kpis": {}},
            "bi_intelligence": {},
            "query_params": {},
            "pergunta_original": "vendas do mês",
            "execution_time_ms": 350,
            "blueprint_id": "bp_test_v1",
            "blueprint_snapshot": {"view_name": "VW_VENDAS"},
        }

        # Mock do banco de dados
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        # Cria Package diretamente (sem banco real)
        with patch.object(svc, '_create_instance', return_value=MagicMock()):
            pkg = await svc.create_package(
                tenant_id=tenant_id,
                fingerprint=fingerprint,
                intention=intention,
                plan=plan,
                pipeline_result=pipeline_result,
                db=mock_db,
            )

        assert pkg is not None
        assert pkg.tenant_id == tenant_id
        assert pkg.intent_key == fingerprint["intent_key"]
        assert pkg.status.value == "ACTIVE"
        assert pkg.version == 1

        # Serialização
        serialized = svc.serialize_package(pkg)
        assert serialized["status"] == "ACTIVE"
        assert serialized["version"] == 1

    @pytest.mark.asyncio
    async def test_compatibility_engine_exact_key_hit(self):
        """Lookup exato por intent_key deve retornar Package imediatamente."""
        from services.data_platform.package_compatibility import PackageCompatibilityEngine
        engine = PackageCompatibilityEngine()

        tenant_id = uuid.uuid4()
        intent_key = "deadbeef" * 8  # 64 chars hex

        mock_package = _make_mock_package(tenant_id, intent_key)

        fingerprint = {"intent_key": intent_key}

        # Mock do banco
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_package)

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        package, score = await engine.find_compatible_package(fingerprint, tenant_id, mock_db)

        assert package == mock_package
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_compatibility_engine_miss_returns_none(self):
        """Quando não há Package compatível, deve retornar (None, low_score)."""
        from services.data_platform.package_compatibility import PackageCompatibilityEngine
        engine = PackageCompatibilityEngine()

        tenant_id = uuid.uuid4()
        fingerprint = {
            "intent_key": "a" * 64,
            "domain": "FINANCEIRO",
            "operation": "AGGREGATION",
            "entity": "GERAL",
            "granularity": "MENSAL",
            "metrics": ["caixa"],
            "group_by": [],
        }

        # Mock do banco retornando vazio
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        package, score = await engine.find_compatible_package(fingerprint, tenant_id, mock_db)

        assert package is None
        assert score == 0.0

    def test_cache_l1_is_per_tenant(self):
        """Cache L1 é estritamente por tenant — dados não vazam entre tenants."""
        from services.data_platform.package_cache import PackageCacheIntelligence
        cache = PackageCacheIntelligence()

        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        cache.l1_set(tenant_a, "shared_key", {"tenant": "A"}, ttl=60)

        result_a = cache.l1_get(tenant_a, "shared_key")
        result_b = cache.l1_get(tenant_b, "shared_key")

        assert result_a is not None  # Tenant A tem acesso
        assert result_b is None       # Tenant B não tem acesso — ISOLAMENTO GARANTIDO

    def test_version_manager_breaking_vs_nonbreaking(self):
        """PackageVersionManager deve distinguir corretamente breaking de non-breaking changes."""
        from services.data_platform.package_version_manager import PackageVersionManager
        vm = PackageVersionManager()

        # Non-breaking: adiciona métrica
        old = {"view_name": "VW_VENDAS", "metrics": ["receita"], "group_by": [], "tipo_analise": "AGGREGATION"}
        new = {"view_name": "VW_VENDAS", "metrics": ["receita", "custo"], "group_by": [], "tipo_analise": "AGGREGATION"}
        has_breaking, _ = vm.detect_breaking_changes(old, new)
        assert has_breaking is False

        # Breaking: remove view_name
        old2 = {"view_name": "VW_VENDAS", "metrics": ["receita"], "group_by": []}
        new2 = {"view_name": "VW_VENDAS_NOVO", "metrics": ["receita"], "group_by": []}
        has_breaking2, changes2 = vm.detect_breaking_changes(old2, new2)
        assert has_breaking2 is True
        assert len(changes2) > 0


# ── Tests: QueryResponse Schema ───────────────────────────────────────────────

class TestQueryResponsePackageFields:
    """Testa que o QueryResponse aceita os novos campos do Analytical Package."""

    def test_query_response_with_package_fields(self):
        """QueryResponse deve aceitar campos do Package sem erro."""
        from schemas.query import QueryResponse

        response = QueryResponse(
            query_id=uuid.uuid4(),
            view_name="VW_VENDAS",
            pergunta_original="quanto vendemos",
            analytical_package_id="pkg-123",
            package_reused=True,
            package_compatibility_score=0.95,
        )

        assert response.package_reused is True
        assert response.analytical_package_id == "pkg-123"
        assert response.package_compatibility_score == 0.95

    def test_query_response_defaults_no_package(self):
        """QueryResponse sem package deve ter package_reused=False por padrão."""
        from schemas.query import QueryResponse

        response = QueryResponse(
            query_id=uuid.uuid4(),
            view_name="VW_VENDAS",
            pergunta_original="quanto vendemos",
        )

        assert response.package_reused is False
        assert response.analytical_package_id is None
        assert response.package_compatibility_score is None
