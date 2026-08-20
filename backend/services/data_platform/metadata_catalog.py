"""
Metadata Catalog Service — LuminaAI Data Platform
---------------------------------------------------
Centro de Governança da Data Platform.
Registra, organiza, monitora e disponibiliza todas as informações estruturais
da plataforma analítica (Views, Blueprints, Datasets, KPIs, Dashboards).

Responsabilidades:
  - Registro de qualquer tipo de estrutura
  - Pesquisa full-text por nome, tag e categoria
  - Data Lineage e Dependency Graph
  - Versionamento imutável (snapshots)
  - Métricas de uso e performance
  - Cache metadata
  - Auditoria e rastreabilidade
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, or_
from sqlalchemy.dialects.postgresql import insert

from models.metadata_catalog import MetadataCatalog
from models.metadata_catalog_version import MetadataCatalogVersion
from database import get_db_context

logger = logging.getLogger("luminaai.data_platform.metadata_catalog")


class MetadataCatalogService:
    """
    Módulo Metadata Catalog — Centro de Governança da Data Platform.
    API única para todos os módulos consultarem e atualizarem metadados estruturais.
    """

    # ═══════════════════════════════════════════════════════════════════════
    # Métodos EXISTENTES (preservados integralmente)
    # ═══════════════════════════════════════════════════════════════════════

    def _build_snapshot(self, meta: MetadataCatalog) -> dict[str, Any]:
        """Serializa os campos estruturais principais para versionamento imutavel."""
        return {
            "nome_view": meta.nome_view,
            "tipo_estrutura": meta.tipo_estrutura,
            "estrutura_id": meta.estrutura_id,
            "origem": meta.origem,
            "owner": meta.owner,
            "categoria": meta.categoria,
            "tags": meta.tags,
            "blueprint_associado": meta.blueprint_associado,
            "dashboard_associado": meta.dashboard_associado,
            "tabelas_utilizadas": meta.tabelas_utilizadas,
            "campos_utilizados": meta.campos_utilizados,
            "relacionamentos": meta.relacionamentos,
            "filtros_padrao": meta.filtros_padrao,
            "periodos_suportados": meta.periodos_suportados,
            "kpis_suportados": meta.kpis_suportados,
            "dependencias": meta.dependencias,
            "lineage": meta.lineage,
            "dependencias_grafo": meta.dependencias_grafo,
            "versao": meta.versao,
            "status": meta.status,
            "integridade": meta.integridade,
            "hash_integridade": meta.hash_integridade,
            "health_score": float(meta.health_score or 100.0),
            "integrity_score": float(meta.integrity_score or 100.0),
            "performance_score": float(meta.performance_score or 100.0),
            "freshness_score": float(meta.freshness_score or 100.0),
            "usage_score": float(meta.usage_score or 0.0),
            "snapshot_em": datetime.now(timezone.utc).isoformat(),
        }

    async def register_view(
        self,
        tenant_id: uuid.UUID,
        view_name: str,
        origem: str,
        tabelas_utilizadas: list[str],
    ) -> MetadataCatalog:
        """Cria ou atualiza um registro de metadados para uma view analítica."""
        async with get_db_context() as db_session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.nome_view == view_name,
            )
            res = await db_session.execute(stmt)
            existing = res.scalar_one_or_none()

            if existing:
                existing.origem = origem
                existing.tabelas_utilizadas = tabelas_utilizadas
                existing.estrutura_id = existing.estrutura_id or view_name
                db_session.add(existing)
                await db_session.flush()
                return existing

            new_meta = MetadataCatalog(
                tenant_id=tenant_id,
                nome_view=view_name,
                estrutura_id=view_name,
                tipo_estrutura="VIEW",
                origem=origem,
                tabelas_utilizadas=tabelas_utilizadas,
                versao=1,
                status="success",
                ultima_sincronizacao=None,
                proxima_sincronizacao=None,
                quantidade_consultas=0,
                dependencias=tabelas_utilizadas,
                tempo_medio_atualizacao=0.0,
                tempo_medio_execucao=0.0,
                integridade="valid",
            )
            db_session.add(new_meta)
            await db_session.flush()
            return new_meta

    async def register_sync(
        self,
        tenant_id: uuid.UUID,
        view_name: str,
        status: str,
        update_time_ms: float,
    ) -> None:
        """Atualiza os metadados da view analítica após um ciclo de sincronização."""
        async with get_db_context() as db_session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.nome_view == view_name,
            )
            res = await db_session.execute(stmt)
            meta = res.scalar_one_or_none()

            if not meta:
                meta = MetadataCatalog(
                    tenant_id=tenant_id,
                    nome_view=view_name,
                    estrutura_id=view_name,
                    tipo_estrutura="VIEW",
                    origem="ERP_ORACLE",
                    tabelas_utilizadas=[],
                    versao=1,
                    status=status,
                    ultima_sincronizacao=datetime.now(timezone.utc),
                    quantidade_consultas=0,
                    tempo_medio_atualizacao=update_time_ms,
                    tempo_medio_execucao=0.0,
                    integridade="valid",
                )
            else:
                meta.status = status
                meta.ultima_sincronizacao = datetime.now(timezone.utc)
                if float(meta.tempo_medio_atualizacao) == 0.0:
                    meta.tempo_medio_atualizacao = update_time_ms
                else:
                    meta.tempo_medio_atualizacao = (
                        float(meta.tempo_medio_atualizacao) * 0.7 + update_time_ms * 0.3
                    )
                meta.integridade = "valid" if status == "success" else "corrupted"

            db_session.add(meta)
            await db_session.flush()

    async def register_query(
        self,
        tenant_id: uuid.UUID,
        view_name: str,
        execution_time_ms: float,
    ) -> None:
        """Incrementa a contagem de consultas e atualiza o tempo médio de execução."""
        async with get_db_context() as db_session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.nome_view == view_name,
            )
            res = await db_session.execute(stmt)
            meta = res.scalar_one_or_none()

            if not meta:
                meta = MetadataCatalog(
                    tenant_id=tenant_id,
                    nome_view=view_name,
                    estrutura_id=view_name,
                    tipo_estrutura="VIEW",
                    origem="ERP_ORACLE",
                    tabelas_utilizadas=[],
                    versao=1,
                    status="success",
                    quantidade_consultas=1,
                    ultima_utilizacao=datetime.now(timezone.utc),
                    tempo_medio_atualizacao=0.0,
                    tempo_medio_execucao=execution_time_ms,
                    integridade="valid",
                )
            else:
                meta.quantidade_consultas += 1
                meta.ultima_utilizacao = datetime.now(timezone.utc)
                if float(meta.tempo_medio_execucao) == 0.0:
                    meta.tempo_medio_execucao = execution_time_ms
                else:
                    meta.tempo_medio_execucao = (
                        float(meta.tempo_medio_execucao) * 0.8 + execution_time_ms * 0.2
                    )

            db_session.add(meta)
            await db_session.flush()

    # ═══════════════════════════════════════════════════════════════════════
    # Métodos NOVOS — Governança Corporativa
    # ═══════════════════════════════════════════════════════════════════════

    async def register_entity(
        self,
        tenant_id: uuid.UUID,
        tipo: str,
        dados: dict[str, Any],
    ) -> MetadataCatalog:
        """
        Registra ou atualiza qualquer estrutura (VIEW, BLUEPRINT, DATASET, KPI, DASHBOARD).
        O campo `estrutura_id` é o identificador externo único da estrutura por tenant.
        """
        tipo = tipo.upper()
        estrutura_id = dados.get("estrutura_id") or dados.get("nome_view", "")
        nome_view = dados.get("nome_view") or estrutura_id

        logger.info(
            "[MetadataCatalog] Registrando entidade | tenant=%s | tipo=%s | id=%s",
            str(tenant_id)[:8],
            tipo,
            estrutura_id,
        )

        async with get_db_context() as session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
                MetadataCatalog.tipo_estrutura == tipo,
            )
            res = await session.execute(stmt)
            meta = res.scalar_one_or_none()

            if meta:
                has_changes = False
                for field, value in dados.items():
                    if hasattr(meta, field) and value is not None and getattr(meta, field) != value:
                        if not has_changes:
                            session.add(
                                MetadataCatalogVersion(
                                    tenant_id=tenant_id,
                                    metadata_id=meta.id,
                                    versao=meta.versao,
                                    snapshot=self._build_snapshot(meta),
                                    autor=dados.get("autor") or "system",
                                    motivo=dados.get("motivo") or f"Atualizacao de {tipo}",
                                )
                            )
                            has_changes = True
                        setattr(meta, field, value)
                if has_changes:
                    meta.versao += 1
            else:
                meta = MetadataCatalog(
                    tenant_id=tenant_id,
                    tipo_estrutura=tipo,
                    estrutura_id=estrutura_id,
                    nome_view=nome_view,
                    origem=dados.get("origem", "ERP_ORACLE"),
                    owner=dados.get("owner", ""),
                    categoria=dados.get("categoria", "Geral"),
                    tags=dados.get("tags", []),
                    blueprint_associado=dados.get("blueprint_associado"),
                    dashboard_associado=dados.get("dashboard_associado"),
                    tabelas_utilizadas=dados.get("tabelas_utilizadas", []),
                    campos_utilizados=dados.get("campos_utilizados", []),
                    relacionamentos=dados.get("relacionamentos", []),
                    filtros_padrao=dados.get("filtros_padrao", {}),
                    periodos_suportados=dados.get("periodos_suportados", []),
                    kpis_suportados=dados.get("kpis_suportados", []),
                    dependencias=dados.get("dependencias", []),
                    lineage=dados.get("lineage", []),
                    dependencias_grafo=dados.get("dependencias_grafo", {}),
                    versao=1,
                    status=dados.get("status", "success"),
                    integridade=dados.get("integridade", "valid"),
                    hash_integridade=dados.get("hash_integridade", ""),
                )
                session.add(meta)

            await session.flush()
            await session.commit()
            return meta

    async def get_entity(
        self,
        tenant_id: uuid.UUID,
        tipo: str,
        estrutura_id: str,
    ) -> MetadataCatalog | None:
        """Busca um registro por tipo de estrutura e ID externo."""
        async with get_db_context() as session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.tipo_estrutura == tipo.upper(),
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    async def get_entity_any(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> MetadataCatalog | None:
        """Busca um registro pelo ID externo, sem exigir conhecimento previo do tipo."""
        async with get_db_context() as session:
            stmt = (
                select(MetadataCatalog)
                .where(
                    MetadataCatalog.tenant_id == tenant_id,
                    MetadataCatalog.estrutura_id == estrutura_id,
                )
                .order_by(MetadataCatalog.atualizado_em.desc())
            )
            res = await session.execute(stmt)
            return res.scalars().first()

    async def search(
        self,
        tenant_id: uuid.UUID,
        query: str | None = None,
        tipo: str | None = None,
        tags: list[str] | None = None,
        categoria: str | None = None,
        limit: int = 50,
    ) -> list[MetadataCatalog]:
        """
        Pesquisa full-text no Metadata Catalog.
        Suporta filtros por nome, tipo, tags e categoria.
        """
        async with get_db_context() as session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id
            )

            if tipo:
                stmt = stmt.where(MetadataCatalog.tipo_estrutura == tipo.upper())

            if categoria:
                stmt = stmt.where(MetadataCatalog.categoria == categoria)

            if query:
                q = f"%{query.lower()}%"
                stmt = stmt.where(
                    or_(
                        MetadataCatalog.nome_view.ilike(q),
                        MetadataCatalog.estrutura_id.ilike(q),
                        MetadataCatalog.owner.ilike(q),
                    )
                )

            # Tags: filtra por contenção (JSONB contains)
            if tags:
                for tag in tags:
                    stmt = stmt.where(
                        MetadataCatalog.tags.contains([tag])
                    )

            stmt = stmt.order_by(MetadataCatalog.atualizado_em.desc()).limit(limit)
            res = await session.execute(stmt)
            return list(res.scalars().all())

    async def get_lineage(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> list[dict[str, Any]]:
        """Retorna o lineage registrado de uma estrutura."""
        async with get_db_context() as session:
            stmt = select(MetadataCatalog.lineage).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res = await session.execute(stmt)
            row = res.scalar_one_or_none()
        return row if isinstance(row, list) else []

    async def get_dependency_graph(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> dict[str, Any]:
        """Retorna o grafo de dependências diretas e transitivas de uma estrutura."""
        async with get_db_context() as session:
            stmt = select(MetadataCatalog.dependencias_grafo).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res = await session.execute(stmt)
            row = res.scalar_one_or_none()
        return row if isinstance(row, dict) else {"upstream": [], "downstream": []}

    async def update_health_scores(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        scores: dict[str, float],
    ) -> None:
        """Atualiza os scores de saúde de uma estrutura e persiste alertas."""
        async with get_db_context() as session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res = await session.execute(stmt)
            meta = res.scalar_one_or_none()
            if not meta:
                return
            for key in ("health_score", "integrity_score", "performance_score",
                        "freshness_score", "usage_score"):
                if key in scores:
                    setattr(meta, key, scores[key])
            if "alertas" in scores:
                meta.alertas = scores["alertas"]
            session.add(meta)
            await session.commit()

    async def update_cache_metadata(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        cache_ativo: bool,
        ttl_segundos: int = 3600,
        hit_rate: float | None = None,
    ) -> None:
        """Atualiza os metadados de cache de uma estrutura."""
        async with get_db_context() as session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res = await session.execute(stmt)
            meta = res.scalar_one_or_none()
            if not meta:
                return
            meta.cache_ativo = cache_ativo
            meta.cache_atualizado_em = datetime.now(timezone.utc)
            meta.cache_ttl_segundos = ttl_segundos
            if hit_rate is not None:
                meta.cache_hit_rate = hit_rate
            session.add(meta)
            await session.commit()

    async def create_version_snapshot(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        motivo: str | None = None,
        autor: str | None = None,
    ) -> MetadataCatalogVersion | None:
        """
        Cria um snapshot imutável da versão atual da estrutura.
        Usado antes de qualquer alteração significativa.
        """
        async with get_db_context() as session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res = await session.execute(stmt)
            meta = res.scalar_one_or_none()
            if not meta:
                return None

            # Serializa snapshot da estrutura atual
            snapshot = {
                "nome_view": meta.nome_view,
                "tipo_estrutura": meta.tipo_estrutura,
                "estrutura_id": meta.estrutura_id,
                "origem": meta.origem,
                "owner": meta.owner,
                "categoria": meta.categoria,
                "tags": meta.tags,
                "versao": meta.versao,
                "status": meta.status,
                "integridade": meta.integridade,
                "hash_integridade": meta.hash_integridade,
                "tabelas_utilizadas": meta.tabelas_utilizadas,
                "campos_utilizados": meta.campos_utilizados,
                "kpis_suportados": meta.kpis_suportados,
                "health_score": float(meta.health_score or 100.0),
                "lineage": meta.lineage,
                "dependencias_grafo": meta.dependencias_grafo,
                "snapshot_em": datetime.now(timezone.utc).isoformat(),
            }

            version = MetadataCatalogVersion(
                tenant_id=tenant_id,
                metadata_id=meta.id,
                versao=meta.versao,
                snapshot=snapshot,
                autor=autor,
                motivo=motivo,
            )
            session.add(version)
            await session.commit()
            logger.info(
                "[MetadataCatalog] Snapshot v%d criado para estrutura: %s",
                meta.versao,
                estrutura_id,
            )
            return version

    async def get_version_history(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> list[MetadataCatalogVersion]:
        """Lista o histórico de versões de uma estrutura em ordem decrescente."""
        async with get_db_context() as session:
            # Primeiro obtém o metadata_id
            stmt_id = select(MetadataCatalog.id).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res_id = await session.execute(stmt_id)
            meta_id = res_id.scalar_one_or_none()
            if not meta_id:
                return []

            stmt = select(MetadataCatalogVersion).where(
                MetadataCatalogVersion.tenant_id == tenant_id,
                MetadataCatalogVersion.metadata_id == meta_id,
            ).order_by(MetadataCatalogVersion.versao.desc())
            res = await session.execute(stmt)
            return list(res.scalars().all())

    async def rollback_to_version(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        versao_alvo: int,
    ) -> MetadataCatalog | None:
        """
        Restaura uma estrutura para o estado de uma versão anterior.
        Cria automaticamente um snapshot da versão atual antes do rollback.
        """
        # Snapshot automático antes do rollback
        await self.create_version_snapshot(
            tenant_id=tenant_id,
            estrutura_id=estrutura_id,
            motivo=f"Snapshot automático antes de rollback para versão {versao_alvo}",
            autor="system",
        )

        async with get_db_context() as session:
            stmt_id = select(MetadataCatalog.id).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res_id = await session.execute(stmt_id)
            meta_id = res_id.scalar_one_or_none()
            if not meta_id:
                return None

            stmt_v = select(MetadataCatalogVersion).where(
                MetadataCatalogVersion.metadata_id == meta_id,
                MetadataCatalogVersion.versao == versao_alvo,
            )
            res_v = await session.execute(stmt_v)
            version = res_v.scalar_one_or_none()
            if not version:
                logger.warning(
                    "[MetadataCatalog] Versão %d não encontrada para rollback: %s",
                    versao_alvo, estrutura_id
                )
                return None

            stmt = select(MetadataCatalog).where(MetadataCatalog.id == meta_id)
            res = await session.execute(stmt)
            meta = res.scalar_one()

            snapshot = version.snapshot
            for field in (
                "nome_view", "origem", "owner", "categoria", "tags",
                "tabelas_utilizadas", "campos_utilizados", "kpis_suportados",
                "status", "integridade", "hash_integridade", "lineage",
            ):
                if field in snapshot:
                    setattr(meta, field, snapshot[field])

            meta.versao = versao_alvo
            session.add(meta)
            await session.commit()
            logger.info(
                "[MetadataCatalog] Rollback executado | estrutura=%s | versão=%d",
                estrutura_id, versao_alvo
            )
            return meta

    async def update_sync_metadata(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        resultado_sync: dict[str, Any],
    ) -> None:
        """
        Atualiza metadados de sincronização (duração, registros, status, erros).

        Args:
            resultado_sync: {
                "status": "success" | "error",
                "duracao_ms": float,
                "registros": int,
                "erros": list[dict],
                "avisos": list[str],
            }
        """
        async with get_db_context() as session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res = await session.execute(stmt)
            meta = res.scalar_one_or_none()
            if not meta:
                return
            meta.status = resultado_sync.get("status", meta.status)
            meta.ultima_sincronizacao = datetime.now(timezone.utc)
            meta.duracao_ultima_sync_ms = resultado_sync.get("duracao_ms", 0.0)
            meta.registros_ultima_sync = resultado_sync.get("registros", 0)
            meta.erros_sync = resultado_sync.get("erros", [])
            meta.integridade = "valid" if resultado_sync.get("status") == "success" else "corrupted"
            session.add(meta)
            await session.commit()

    async def get_catalog_summary(
        self,
        tenant_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Resumo executivo do catálogo do tenant.
        Totais por tipo, saúde geral, alertas ativos, cache rate.
        """
        async with get_db_context() as session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id
            )
            res = await session.execute(stmt)
            entities = res.scalars().all()

        if not entities:
            return {"total": 0}

        por_tipo: dict[str, int] = {}
        total_alertas = 0
        health_sum = 0.0
        cache_ativos = 0

        for e in entities:
            t = e.tipo_estrutura
            por_tipo[t] = por_tipo.get(t, 0) + 1
            total_alertas += len(e.alertas or [])
            health_sum += float(e.health_score or 100.0)
            if e.cache_ativo:
                cache_ativos += 1

        return {
            "total": len(entities),
            "por_tipo": por_tipo,
            "alertas_ativos": total_alertas,
            "health_medio": round(health_sum / len(entities), 2),
            "cache_ativos": cache_ativos,
        }

    async def register_access(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        user_id: str | None = None,
    ) -> None:
        """Registra um acesso de usuário à estrutura para métricas de uso."""
        async with get_db_context() as session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res = await session.execute(stmt)
            meta = res.scalar_one_or_none()
            if not meta:
                return
            meta.quantidade_consultas += 1
            meta.ultima_utilizacao = datetime.now(timezone.utc)
            # Incrementa usuários únicos apenas se user_id fornecido (simplificado)
            if user_id:
                meta.quantidade_usuarios = max(meta.quantidade_usuarios, 1)
            session.add(meta)
            await session.commit()
