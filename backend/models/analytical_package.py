"""
LuminaAI — Analytical Package ORM Model
----------------------------------------
Representa a unidade central de conhecimento reutilizável da plataforma.

Um Analytical Package encapsula todo o conhecimento gerado pela primeira
execução completa de uma análise: fingerprint semântico, estratégia visual,
estrutura analítica, blueprint de origem, scores de qualidade e saúde.

Consultas subsequentes com intenção compatível reutilizam este Package,
evitando a reconstrução completa do pipeline NLU → Planner → Validator →
Business → Execution → Analytics → Dashboard.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Integer, Float, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant
    from models.package_dashboard_instance import PackageDashboardInstance


class PackageStatus(str, enum.Enum):
    """
    Ciclo de vida de um Analytical Package.

    DRAFT       — Em construção, não disponível para reuso.
    ACTIVE      — Disponível para reuso. Estado padrão após criação.
    DEPRECATED  — Obsoleto (blueprint-fonte atualizado ou schema incompatível).
    ARCHIVED    — Arquivado manualmente. Preservado para auditoria.
    """
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class AnalyticalPackage(Base):
    """
    Unidade central de conhecimento reutilizável do LuminaAI.

    Criado automaticamente na primeira execução de uma análise inédita.
    Reutilizado em análises com intenção semanticamente compatível.

    O Package armazena:
    - Intent Fingerprint: DNA semântico da análise (nunca texto literal)
    - Semantic Context: contexto rico de domínio, entidades e operações
    - Visual Strategy: estratégia visual determinística (tipo de gráfico, layout)
    - Analytical Structure: métricas, agrupamentos e filtros estruturais
    - Blueprint Snapshot: captura do blueprint no momento da criação
    - Scores: qualidade (quality_score) e saúde técnica (health_score)
    """

    __tablename__ = "analytical_packages"

    # ── Identidade ─────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único do Analytical Package.",
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Isolamento por tenant — obrigatório em toda operação.",
    )

    # ── Fingerprint e Contexto Semântico ───────────────────────────
    intent_fingerprint: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "DNA semântico da análise. Nunca usa texto literal. "
            "Campos: intent_key (SHA-256), domain, operation, entity, "
            "granularity, metrics, group_by, analysis_type."
        ),
    )

    intent_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Chave SHA-256 do fingerprint para lookup eficiente.",
    )

    semantic_context: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Contexto semântico rico: domínio de negócio, entidades envolvidas, "
            "operações executadas, nível de confiança da IA."
        ),
    )

    # ── Estratégias ─────────────────────────────────────────────────
    visual_strategy: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Estratégia visual determinística: tipo de gráfico, layout, "
            "ordem dos componentes, configurações de exibição."
        ),
    )

    interaction_strategy: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Como o usuário deve interagir com esta análise: "
            "filtros disponíveis, drill-downs, ações permitidas."
        ),
    )

    analytical_structure: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Estrutura analítica: métricas normalizadas, agrupamentos, "
            "filtros estruturais, operações de cálculo aplicadas."
        ),
    )

    # ── Snapshot do Blueprint de Origem ─────────────────────────────
    blueprint_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="ID do Blueprint que originou este Package.",
    )

    blueprint_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Snapshot completo do Blueprint no momento da criação do Package. "
            "Preservado para auditoria mesmo se o Blueprint evoluir."
        ),
    )

    view_names: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Views analíticas das quais este Package depende.",
    )

    # ── Ciclo de Vida ───────────────────────────────────────────────
    status: Mapped[PackageStatus] = mapped_column(
        SAEnum(PackageStatus, name="packagestatus"),
        nullable=False,
        default=PackageStatus.ACTIVE,
        index=True,
        comment="Status atual no ciclo de vida do Package.",
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Versão do Package. Incrementada quando o blueprint-fonte evolui.",
    )

    # ── Scores de Qualidade e Saúde ─────────────────────────────────
    quality_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        comment=(
            "Score de qualidade (0.0-1.0). Calculado a partir de: "
            "reuso rate (40%), data freshness (20%), blueprint health (20%), "
            "consistency (20%)."
        ),
    )

    health_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        comment=(
            "Score de saúde técnica (0.0-1.0). Calculado a partir de: "
            "schema validity (30%), view availability (30%), "
            "compatibility (20%), performance (20%)."
        ),
    )

    # ── Métricas de Uso ─────────────────────────────────────────────
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Número total de reusos deste Package.",
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp da última utilização do Package.",
    )

    avg_execution_time_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Tempo médio de execução (ms) nas reutilizações.",
    )

    error_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Número de execuções com erro. Usado no quality_score.",
    )

    # ── Dependências e Compatibilidade ──────────────────────────────
    dependencies: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Dependências do Package: view_ids, blueprint_ids, "
            "catalog_ids. Usadas para detecção de breaking changes."
        ),
    )

    compatible_fingerprints: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment=(
            "Lista de intent_keys de fingerprints comprovadamente compatíveis. "
            "Otimiza lookup sem recalcular compatibilidade."
        ),
    )

    # ── Rastreabilidade ─────────────────────────────────────────────
    created_by: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="AI_PIPELINE",
        comment="Origem da criação: 'AI_PIPELINE' ou 'MANUAL'.",
    )

    deprecation_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Motivo da depreciação, quando aplicável.",
    )

    # ── Timestamps ──────────────────────────────────────────────────
    criado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    atualizado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relacionamentos ─────────────────────────────────────────────
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        lazy="select",
    )

    instances: Mapped[list[PackageDashboardInstance]] = relationship(
        "PackageDashboardInstance",
        back_populates="package",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="PackageDashboardInstance.criado_em.desc()",
    )

    def __repr__(self) -> str:
        return (
            f"<AnalyticalPackage id={self.id!s:.8} "
            f"status={self.status.value} "
            f"version={self.version} "
            f"usage={self.usage_count} "
            f"quality={self.quality_score:.2f}>"
        )

    # ── Métodos de Score ────────────────────────────────────────────

    def compute_quality_score(self, recent_usage: int, total_usage: int, error_rate: float, freshness_days: int) -> float:
        """
        Recalcula o quality_score baseado em métricas atuais.

        Parâmetros:
            recent_usage    — usos nos últimos 30 dias
            total_usage     — usos totais históricos
            error_rate      — proporção de execuções com erro (0.0-1.0)
            freshness_days  — dias desde o último refresh de dados
        """
        # Reuso rate (40%): quanto mais usado recentemente, maior a qualidade
        reuse_score = min(1.0, recent_usage / 10.0) * 0.40

        # Data freshness (20%): dados frescos valem mais
        freshness_score = max(0.0, 1.0 - (freshness_days / 30.0)) * 0.20

        # Blueprint health (20%): delegado ao health_score
        blueprint_score = self.health_score * 0.20

        # Consistency (20%): taxa de sucesso das execuções
        consistency_score = (1.0 - min(1.0, error_rate)) * 0.20

        score = reuse_score + freshness_score + blueprint_score + consistency_score
        return round(min(1.0, max(0.0, score)), 4)

    def compute_health_score(
        self,
        schema_valid: bool,
        views_available: bool,
        no_breaking_changes: bool,
        avg_time_ms: float,
        threshold_ms: float = 5000.0,
    ) -> float:
        """
        Recalcula o health_score baseado em verificações técnicas.

        Parâmetros:
            schema_valid         — blueprint-fonte ainda é válido no Catalog
            views_available      — views dependentes existem e respondem
            no_breaking_changes  — sem breaking changes detectados
            avg_time_ms          — tempo médio de execução atual
            threshold_ms         — threshold de performance aceitável
        """
        schema_score = 1.0 if schema_valid else 0.0
        view_score = 1.0 if views_available else 0.0
        compat_score = 1.0 if no_breaking_changes else 0.0
        perf_score = max(0.0, 1.0 - (avg_time_ms / threshold_ms)) if avg_time_ms > 0 else 1.0

        score = (
            schema_score * 0.30
            + view_score * 0.30
            + compat_score * 0.20
            + perf_score * 0.20
        )
        return round(min(1.0, max(0.0, score)), 4)
