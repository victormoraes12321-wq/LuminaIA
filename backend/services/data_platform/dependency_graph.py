"""
Dependency Graph — LuminaAI Data Platform
------------------------------------------
Mantém um grafo bidirecional de dependências entre as estruturas da Data Platform.

Grafo oficial:
  View → Dataset → Blueprint → Dashboard → Componentes
  View → KPI → Indicadores

Permite:
  - Saber o impacto de qualquer alteração (downstream)
  - Saber de onde uma estrutura depende (upstream)
  - Resolver dependências transitivas recursivamente
"""
import logging
import uuid
import json
from typing import Any

from sqlalchemy import select
from models.metadata_catalog import MetadataCatalog
from database import get_db_context

logger = logging.getLogger("luminaai.data_platform.dependency_graph")


class DependencyGraph:
    """
    Grafo de dependências da Data Platform.
    Registra e resolve relacionamentos upstream/downstream entre estruturas.
    """

    def _make_graph(
        self,
        upstream: list[str] | None = None,
        downstream: list[str] | None = None,
    ) -> dict[str, list[str]]:
        """Cria estrutura padrão do grafo."""
        return {
            "upstream": upstream or [],
            "downstream": downstream or [],
        }

    def _coerce_graph(self, value: Any) -> dict[str, list[str]]:
        """Normaliza dependencias_grafo persistido como dict ou JSON string."""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return self._make_graph()

        if not isinstance(value, dict):
            return self._make_graph()

        upstream = value.get("upstream", [])
        downstream = value.get("downstream", [])
        if not isinstance(upstream, list):
            upstream = []
        if not isinstance(downstream, list):
            downstream = []
        return self._make_graph(upstream=upstream, downstream=downstream)

    # ── Registro de dependências ───────────────────────────────────────────

    async def register_dependency(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        depende_de: list[str],
        requerido_por: list[str] | None = None,
    ) -> None:
        """
        Registra as dependências de uma estrutura.

        Args:
            estrutura_id:  Estrutura que está sendo registrada
            depende_de:    IDs das estruturas que esta depende (upstream)
            requerido_por: IDs das estruturas que dependem desta (downstream)
        """
        logger.info(
            "[DependencyGraph] Registrando dependências | tenant=%s | estrutura=%s | upstream=%s",
            str(tenant_id)[:8],
            estrutura_id,
            depende_de,
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
                    "[DependencyGraph] Estrutura não encontrada: %s", estrutura_id
                )
                return

            existing = self._coerce_graph(meta.dependencias_grafo)
            meta.dependencias_grafo = {
                "upstream": list(set(existing.get("upstream", []) + depende_de)),
                "downstream": list(set(existing.get("downstream", []) + (requerido_por or []))),
            }
            session.add(meta)

            # Atualiza o downstream das estruturas upstream
            for upstream_id in depende_de:
                stmt_up = select(MetadataCatalog).where(
                    MetadataCatalog.tenant_id == tenant_id,
                    MetadataCatalog.estrutura_id == upstream_id,
                )
                res_up = await session.execute(stmt_up)
                meta_up = res_up.scalar_one_or_none()
                if meta_up:
                    existing_up = self._coerce_graph(meta_up.dependencias_grafo)
                    downstream_up = existing_up.get("downstream", [])
                    if estrutura_id not in downstream_up:
                        downstream_up.append(estrutura_id)
                    meta_up.dependencias_grafo = {
                        "upstream": existing_up.get("upstream", []),
                        "downstream": downstream_up,
                    }
                    session.add(meta_up)

            await session.commit()

    async def get_graph(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
    ) -> dict[str, list[str]]:
        """Retorna o grafo direto de dependências (upstream + downstream) de uma estrutura."""
        async with get_db_context() as session:
            stmt = select(MetadataCatalog.dependencias_grafo).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res = await session.execute(stmt)
            row = res.scalar_one_or_none()

        return self._coerce_graph(row)

    async def get_impact(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        max_depth: int = 5,
    ) -> dict[str, Any]:
        """
        Calcula o impacto de uma alteração na estrutura.
        Resolve transitivamente todos os downstream dependentes.

        Returns:
            {
                "estrutura_id": ...,
                "impacto_direto": [...],
                "impacto_total": [...],   # inclui transitivos
                "profundidade": int
            }
        """
        graph = await self.get_graph(tenant_id, estrutura_id)
        direto = graph.get("downstream", [])

        # Resolve transitivo via BFS
        visitados: set[str] = set(direto)
        fila = list(direto)
        profundidade = 0

        while fila and profundidade < max_depth:
            proximo_nivel = []
            for dep_id in fila:
                sub_graph = await self.get_graph(tenant_id, dep_id)
                for sub_dep in sub_graph.get("downstream", []):
                    if sub_dep not in visitados:
                        visitados.add(sub_dep)
                        proximo_nivel.append(sub_dep)
            fila = proximo_nivel
            profundidade += 1

        return {
            "estrutura_id": estrutura_id,
            "impacto_direto": direto,
            "impacto_total": list(visitados),
            "profundidade": profundidade,
        }

    async def remove_dependency(
        self,
        tenant_id: uuid.UUID,
        estrutura_id: str,
        remover_upstream: str,
    ) -> None:
        """Remove uma dependência upstream específica e atualiza o grafo."""
        async with get_db_context() as session:
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id,
                MetadataCatalog.estrutura_id == estrutura_id,
            )
            res = await session.execute(stmt)
            meta = res.scalar_one_or_none()

            if meta:
                existing = meta.dependencias_grafo or {}
                upstream = [u for u in existing.get("upstream", []) if u != remover_upstream]
                meta.dependencias_grafo = {
                    "upstream": upstream,
                    "downstream": existing.get("downstream", []),
                }
                session.add(meta)
                await session.commit()


# Singleton export
dependency_graph = DependencyGraph()
