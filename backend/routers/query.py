"""
LuminaAI — Endpoint Central de Consulta Inteligente
POST /api/v1/query

Orquestra o fluxo completo:
  1. Autentica o usuário (mock estruturado com Role)
  2. Busca o catálogo de views ativas do tenant no PostgreSQL
  3. Aciona o Motor de Intenção (ai_service) para identificar a view
  4. Gera dados simulando a execução da view Oracle (mock realista)
  5. Persiste a consulta no search_history de forma assíncrona
  6. Retorna resposta estruturada completa ao frontend
"""
from __future__ import annotations

import logging
import time
import uuid
import json
import hashlib
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from contracts.analytical_v2 import AnalyticalResponseV2, PipelineKind
from contracts.conversation_state_v2 import (
    ConversationStateV2,
    ConversationTurnCompletion,
    ConversationTurnFailure,
    ConversationTurnStart,
)
from database import get_db, get_db_context
from models.search_history import SearchHistory
from models.favorite import Favorite
from models.tenant import Tenant
from models.user import User, UserRole
from models.view_catalog import ChartType, ViewCatalog
from schemas.query import QueryRequest, QueryResponse, HistoryListItem, FavoriteListItem, IntentionPlanItem
from schemas.view_catalog import ViewCatalogSummary
from services.ai_service import AIServiceError, IntentionResponse, identify_intention
from services.query_planner import create_query_plan, QueryPlanItem
from services.oracle_service import decrypt_connection_details
from services.postgresql_clone_service import get_clone_db_connection, execute_clone_view
from services.data_transformer import transform_data
from services.query_intelligence_engine import query_intelligence_engine
from services.query_response_governance import query_response_governance
from routers.dependencies import get_current_user, enforce_password_change, check_admin_role
from services.conversation_state.service import (
    ConversationStateError,
    StartedTurn,
    conversation_state_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/query",
    tags=["🔍 Query Engine"],
)


def _conversation_http_error(exc: ConversationStateError) -> HTTPException:
    return HTTPException(
        status_code=exc.http_status,
        detail={
            "code": exc.code,
            "message": str(exc),
            "actual_context_version": exc.actual_context_version,
        },
    )


def _fingerprint_json(value: Any) -> str:
    normalized = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _state_from_governed_response(
    governed: dict[str, Any],
    *,
    started: StartedTurn,
) -> ConversationStateV2:
    sidecar = governed.get("analytical_contract")
    if sidecar:
        try:
            contract = (
                sidecar
                if isinstance(sidecar, AnalyticalResponseV2)
                else AnalyticalResponseV2.model_validate_json(
                    json.dumps(sidecar, default=str)
                )
            )
            intent = contract.intent
            return ConversationStateV2(
                context_epoch=started.context_epoch,
                context_version=started.base_context_version,
                active_metric_refs=intent.metric_refs,
                active_dimension_refs=intent.dimension_refs,
                active_filters=intent.filters,
                active_time_windows=intent.time_windows,
                active_comparison=intent.comparison,
                active_visualizations=intent.requested_visualizations,
                last_intent_kind=intent.intent_kind,
                last_readiness=intent.readiness,
                last_plan_fingerprint=_fingerprint_json(governed.get("plano_execucao") or {}),
                last_response_fingerprint=_fingerprint_json({
                    "query_id": governed.get("query_id"),
                    "status": governed.get("status"),
                    "view_name": governed.get("view_name"),
                }),
                pending_clarification=bool(governed.get("ambiguities") or governed.get("missing_information")),
                field_origins=intent.field_origins,
            )
        except (ValueError, TypeError):
            logger.warning(
                "[CONVERSATION] Sidecar analitico invalido para snapshot; usando estado minimo",
                extra={"session_id": started.public_session_id},
            )
    return ConversationStateV2(
        context_epoch=started.context_epoch,
        context_version=started.base_context_version,
        last_response_fingerprint=_fingerprint_json({
            "query_id": governed.get("query_id"),
            "status": governed.get("status"),
            "view_name": governed.get("view_name"),
        }),
        pending_clarification=bool(governed.get("ambiguities") or governed.get("missing_information")),
    )


async def _complete_conversation_turn(
    governed: dict[str, Any],
    *,
    started: StartedTurn | None,
    current_user: User,
) -> dict[str, Any]:
    if started is None:
        return governed
    response_text = str(
        governed.get("resposta_direta")
        or governed.get("mensagem")
        or governed.get("ia_analise")
        or "Resposta analitica concluida."
    )
    try:
        completed = await conversation_state_service.complete_turn(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            completion=ConversationTurnCompletion(
                session_id=started.session_id,
                query_node_id=started.query_node_id,
                base_context_version=started.base_context_version,
                response_content=response_text[:12000],
                state=_state_from_governed_response(governed, started=started),
                response_fingerprint=_fingerprint_json({
                    "query_id": governed.get("query_id"),
                    "status": governed.get("status"),
                }),
            ),
        )
    except ConversationStateError as exc:
        if conversation_state_service.postgres_is_authority:
            raise _conversation_http_error(exc)
        governed["conversation_warning"] = exc.code
        return governed
    governed.update({
        "session_id": completed.public_session_id,
        "query_node_id": completed.query_node_id,
        "response_node_id": completed.response_node_id,
        "parent_id": completed.parent_node_id,
        "context_version": completed.context_version,
        "context_epoch": completed.context_epoch,
        "conversation_status": "ACTIVE",
        "idempotent_replay": completed.idempotent_replay,
    })
    return governed


async def _fail_conversation_turn(
    *,
    started: StartedTurn | None,
    current_user: User,
) -> None:
    if started is None:
        return
    try:
        await conversation_state_service.fail_turn(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            failure=ConversationTurnFailure(
                session_id=started.session_id,
                query_node_id=started.query_node_id,
                base_context_version=started.base_context_version,
                error_code="PIPELINE_FAILED",
                safe_message="A consulta falhou antes de concluir a resposta.",
            ),
        )
    except Exception:
        logger.exception("[CONVERSATION] Falha ao registrar turno incompleto")

# ── Mock Data Generator ───────────────────────────────────────
from services.mock_service import gerar_dados_mock_oracle

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# BACKGROUND TASK — Persistir histórico de consulta
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

async def _persistir_historico(
    user_id: uuid.UUID,
    view_catalog_id: uuid.UUID | None,
    pergunta: str,
    parametros: dict[str, str],
    confianca: float | None,
    tempo_ms: int,
) -> None:
    """
    Persiste o registro da consulta no search_history de forma assíncrona.
    """
    try:
        async with get_db_context() as session:
            historico = SearchHistory(
                user_id=user_id,
                view_catalog_id=view_catalog_id,
                pergunta_texto=pergunta,
                parametros_extraidos=parametros,
                ia_confianca=Decimal(str(round(confianca, 4))) if confianca is not None else None,
                tempo_resposta_ms=tempo_ms,
            )
            session.add(historico)

        logger.info(
            "✅ Histórico persistido | user=%s | view=%s | tempo=%dms",
            str(user_id)[:8],
            str(view_catalog_id)[:8] if view_catalog_id else "N/A",
            tempo_ms,
        )
    except Exception:
        logger.exception(
            "❌ Falha ao persistir histórico (não afeta o usuário) | user=%s",
            str(user_id)[:8],
        )


@router.get(
    "/history",
    response_model=list[HistoryListItem],
    summary="Listar histórico de pesquisas (Hidratação)",
    description="Retorna as últimas 50 consultas realizadas pelo usuário atual, resolvidas com os metadados da view catalogada.",
)
async def get_query_history(
    current_user: User = Depends(get_current_user),
    _pwd_guard: User = Depends(enforce_password_change),
    db: AsyncSession = Depends(get_db),
) -> list[HistoryListItem]:
    """Busca o histórico de pesquisas no PostgreSQL e resolve relacionamentos."""
    stmt = (
        select(SearchHistory)
        .options(joinedload(SearchHistory.view_catalog))
        .where(SearchHistory.user_id == current_user.id)
        .order_by(SearchHistory.criado_em.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    history_records = result.scalars().all()

    items = []
    for r in history_records:
        items.append(
            HistoryListItem(
                id=r.id,
                pergunta=r.pergunta_texto,
                view_name=r.view_catalog.nome_view_oracle if r.view_catalog else None,
                chart_type=r.view_catalog.tipo_grafico_padrao if r.view_catalog else None,
                timestamp=r.criado_em,
                parametros=r.parametros_extraidos,
            )
        )
    return items


@router.get(
    "/favorites",
    response_model=list[FavoriteListItem],
    summary="Listar consultas favoritadas (Hidratação)",
    description="Retorna todas as análises favoritadas pelo usuário com seus respectivos parâmetros persistidos.",
)
async def get_query_favorites(
    current_user: User = Depends(get_current_user),
    _pwd_guard: User = Depends(enforce_password_change),
    db: AsyncSession = Depends(get_db),
) -> list[FavoriteListItem]:
    """Busca os favoritos do usuário no PostgreSQL e resolve relacionamentos."""
    stmt = (
        select(Favorite)
        .options(joinedload(Favorite.view_catalog))
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.criado_em.desc())
    )
    result = await db.execute(stmt)
    favorite_records = result.scalars().all()

    items = []
    for r in favorite_records:
        items.append(
            FavoriteListItem(
                id=r.id,
                titulo=r.titulo_personalizado if r.titulo_personalizado else r.view_catalog.nome_view_oracle,
                view_name=r.view_catalog.nome_view_oracle,
                chart_type=r.view_catalog.tipo_grafico_padrao,
                parametros=r.parametros_salvos,
                query_id=r.id,
            )
        )
    return items


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ENDPOINT: POST /api/v1/query
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@router.post(
    "/",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Consulta Inteligente via Motor de Intenção",
    description=(
        "**Fluxo completo de consulta inteligente do LuminaAI:**\n\n"
        "1. Autentica o usuário e valida permissões\n"
        "2. Busca o catálogo de views ativas do tenant no PostgreSQL\n"
        "3. Aciona o Motor de Intenção (OpenAI Structured Outputs) para identificar a view\n"
        "4. Executa a view Oracle (simulado) e retorna dados estruturados\n"
        "5. Persiste a consulta no histórico de forma assíncrona\n"
        "6. Retorna JSON estruturado com dados prontos para renderização visual"
    ),
    response_description="Dados estruturados da consulta com tipo de componente visual",
)
async def processar_consulta(
    payload: QueryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    _pwd_guard: User = Depends(enforce_password_change),
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """
    Endpoint central de consulta inteligente do LuminaAI.
    """
    # ── Cronômetro para medir latência total ─────────────────
    inicio = time.perf_counter()
    query_id = uuid.uuid4()

    # ── 1. Autenticação e Prevenção Cross-Tenant ─────────────
    if current_user.tenant_id != payload.tenant_id:
        logger.warning(
            "Tentativa de acesso cross-tenant rejeitada: user=%s (tenant=%s) | payload tenant=%s",
            str(current_user.id)[:8],
            str(current_user.tenant_id)[:8],
            str(payload.tenant_id)[:8],
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. O tenant_id informado não corresponde ao seu usuário.",
        )

    # ESP - Audit & Tenant Isolation
    from services.security.enterprise_security_platform import esp_platform
    esp_platform.audit_event("QUERY_REQUESTED", current_user.email, {"pergunta": payload.pergunta})
    esp_platform.enforce_tenant_isolation(current_user.tenant_id, payload.tenant_id)

    logger.info(
        "[QUERY] Query recebida | user=%s (%s) | tenant=%s | pergunta=%r",
        str(current_user.id)[:8],
        current_user.role.value,
        str(payload.tenant_id)[:8],
        payload.pergunta[:60] + ("..." if len(payload.pergunta) > 60 else ""),
    )

    # ── 2. Buscar catálogo de views ativas do tenant ─────────
    stmt = (
        select(ViewCatalog)
        .where(
            ViewCatalog.tenant_id == payload.tenant_id,
            ViewCatalog.ativo.is_(True),
        )
        .order_by(ViewCatalog.criado_em.asc())
    )
    result = await db.execute(stmt)
    views: list[ViewCatalog] = list(result.scalars().all())

    if not views:
        logger.warning(
            "Catálogo vazio para tenant_id=%s", str(payload.tenant_id)[:8]
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Nenhuma view ativa encontrada no catálogo desta empresa. "
                "Contate o administrador para cadastrar views no catálogo."
            ),
        )

    # Converte para ViewCatalogSummary para injeção no prompt da IA
    catalog_summaries: list[ViewCatalogSummary] = [
        ViewCatalogSummary.model_validate(v) for v in views
    ]

    logger.info(
        "Catálogo carregado | views_ativas=%d | tenant=%s",
        len(catalog_summaries),
        str(payload.tenant_id)[:8],
    )

    # 3. Carregar dados do Tenant e extrair apenas contexto nao sensivel de IA
    tenant_stmt = select(Tenant).where(Tenant.id == payload.tenant_id)
    tenant_res = await db.execute(tenant_stmt)
    tenant = tenant_res.scalar_one_or_none()

    if not tenant:
        logger.error("Tenant não encontrado no PostgreSQL: %s", payload.tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa (Tenant) não cadastrada no sistema.",
        )

    # Defensively parse JSON columns if they are strings
    def safe_parse_json(val) -> dict:
        if isinstance(val, dict):
            return val
        if isinstance(val, str) and val.strip():
            try:
                import json
                return json.loads(val)
            except Exception:
                pass
        return {}

    tenant_ia_config = safe_parse_json(tenant.ia_config)

    ia_api_key = None
    ia_model = None
    ia_temp = None
    ia_instructions = None

    if tenant_ia_config:
        ia_temp = tenant_ia_config.get("temperature")
        ia_instructions = tenant_ia_config.get("custom_instructions")
    # Calcula data atual para orientar cálculos temporais relativos da IA
    from datetime import datetime
    data_atual_str = datetime.now().strftime("%Y-%m-%d")
    instrucoes_finais = (
        f"{ia_instructions or ''}\n\n"
        f"[REFERÊNCIA TEMPORAL] A data atual do sistema hoje é exatamente: {data_atual_str}. "
        "Use esta data como ponto de partida para calcular datas relativas como 'primeiro semestre', 'esse ano', 'mes passado', etc."
    )

    conversation_turn: StartedTurn | None = None
    conversation_server_state: ConversationStateV2 | None = None
    if conversation_state_service.postgres_writes_enabled:
        try:
            parent_uuid = None
            if payload.parent_id:
                try:
                    parent_uuid = uuid.UUID(str(payload.parent_id))
                except ValueError:
                    parent_uuid = None
            conversation_turn = await conversation_state_service.start_turn(
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                turn=ConversationTurnStart(
                    public_session_id=payload.session_id,
                    client_message_id=payload.client_message_id or uuid.uuid4(),
                    parent_node_id=parent_uuid,
                    expected_context_version=payload.expected_context_version,
                    content=payload.pergunta,
                ),
            )
            if conversation_state_service.postgres_is_authority:
                _, conversation_server_state = await conversation_state_service.load_state(
                    tenant_id=current_user.tenant_id,
                    user_id=current_user.id,
                    public_session_id=conversation_turn.public_session_id,
                )
        except (ConversationStateError, ValueError) as exc:
            if isinstance(exc, ConversationStateError):
                if conversation_state_service.postgres_is_authority:
                    raise _conversation_http_error(exc)
                logger.warning("[CONVERSATION] Shadow write ignorado: %s", exc.code)
                conversation_turn = None
            elif conversation_state_service.postgres_is_authority:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"code": "INVALID_CONVERSATION_REQUEST", "message": str(exc)},
                ) from exc
            else:
                logger.warning("[CONVERSATION] Shadow request invalido; legado preservado")
                conversation_turn = None
        if conversation_turn.idempotent_replay and conversation_turn.response_node_id:
            return QueryResponse(
                query_id=conversation_turn.response_node_id,
                pergunta_original=payload.pergunta,
                mensagem="Esta mensagem ja foi processada. A referencia da resposta existente foi retornada.",
                status="IDEMPOTENT_REPLAY",
                session_id=conversation_turn.public_session_id,
                query_node_id=conversation_turn.query_node_id,
                response_node_id=conversation_turn.response_node_id,
                parent_id=conversation_turn.parent_node_id,
                context_version=conversation_turn.base_context_version,
                context_epoch=conversation_turn.context_epoch,
                conversation_status="ACTIVE",
                idempotent_replay=True,
            )

    # ── 4. Strangler Pattern: Desvio controlado para o Novo Pipeline ─────────
    import os as _os
    _is_testing = "PYTEST_CURRENT_TEST" in _os.environ
    from config import settings
    # Em testes, só usa o novo pipeline se explicitamente solicitado pelo payload
    _use_new_pipeline = getattr(payload, "use_new_pipeline", False)
    if (not _is_testing and (settings.NEW_PIPELINE_ACTIVE or settings.ENABLE_DETERMINISTIC_PIPELINE)) or _use_new_pipeline:
        logger.info("[Orchestrator] Desviando consulta para o NOVO pipeline cognitivo (ENABLE_DETERMINISTIC_PIPELINE=True)...")
        from services.new_query_orchestrator import new_query_orchestrator
        
        # Converte o payload history para o formato esperado (lista de dicts)
        history_list = []
        if payload.history:
            history_list = [{"role": h.role, "content": h.content} for h in payload.history]
            
        try:
            res_dict = await new_query_orchestrator.run_pipeline(
                pergunta=payload.pergunta,
                tenant_id=str(payload.tenant_id),
                session_id=(
                    conversation_turn.public_session_id
                    if conversation_turn and conversation_state_service.postgres_is_authority
                    else payload.session_id
                ),
                history=history_list,
                parent_id=getattr(payload, "parent_id", None),
                mode=payload.mode,
                conversation_state=conversation_server_state,
                postgres_conversation_authority=conversation_state_service.postgres_is_authority,
            )
        except Exception:
            await _fail_conversation_turn(started=conversation_turn, current_user=current_user)
            raise
        
        governed = await query_response_governance.enrich(
            res_dict,
            db=db,
            tenant=tenant,
            current_user=current_user,
            pipeline=PipelineKind.NEW,
            session_id=payload.session_id,
        )
        governed = await _complete_conversation_turn(
            governed,
            started=conversation_turn,
            current_user=current_user,
        )
        return QueryResponse.model_validate(governed)

    # ── 4. Delegar execução para o pipeline legado da Query Intelligence Engine ─────
    try:
        legacy_response = await query_intelligence_engine.process_query(
            payload=payload,
            current_user=current_user,
            db=db,
            background_tasks=background_tasks,
            instrucoes_finais=instrucoes_finais,
            ia_api_key=ia_api_key,
            ia_model=ia_model,
            ia_temp=ia_temp,
            catalog_summaries=catalog_summaries,
            tenant=tenant,
            intent_identifier=identify_intention,
        )
    except Exception:
        await _fail_conversation_turn(started=conversation_turn, current_user=current_user)
        raise
    legacy_payload = (
        legacy_response.model_dump(mode="json")
        if hasattr(legacy_response, "model_dump")
        else dict(legacy_response)
    )
    governed = await query_response_governance.enrich(
        legacy_payload,
        db=db,
        tenant=tenant,
        current_user=current_user,
        pipeline=PipelineKind.LEGACY,
        session_id=payload.session_id,
    )
    governed = await _complete_conversation_turn(
        governed,
        started=conversation_turn,
        current_user=current_user,
    )
    return QueryResponse.model_validate(governed)


@router.get("/intelligence", status_code=status.HTTP_200_OK)
async def obter_metricas_inteligencia(
    current_user: User = Depends(check_admin_role)
):
    """
    Retorna métricas consolidadas de eficiência do Query Intelligence Engine (QIE).
    """
    from services.query_intelligence_engine import query_intelligence_engine
    return query_intelligence_engine.get_intelligence_metrics()


@router.get("/cache/stats", status_code=status.HTTP_200_OK)
async def obter_estatisticas_cache(
    current_user: User = Depends(check_admin_role)
):
    """
    Retorna estatísticas detalhadas de performance e saúde da Intelligent Caching Platform (ICP).
    """
    from services.cache_service import global_cache
    return global_cache.get_statistics()


@router.post("/cache/clear", status_code=status.HTTP_200_OK)
async def limpar_cache_plataforma(
    current_user: User = Depends(check_admin_role)
):
    """
    Invalida e limpa o cache associado ao tenant do usuário logado.
    Administradores do sistema podem limpar todo o cache se necessário.
    """
    from services.cache_service import global_cache
    if current_user.role.value == "ADMIN":
        global_cache.clear_all()
        return {"status": "SUCCESS", "mensagem": "Todo o cache da plataforma ICP foi limpo."}
    else:
        global_cache.clear_tenant(current_user.tenant_id)
        return {"status": "SUCCESS", "mensagem": f"O cache do tenant {current_user.tenant_id} foi limpo."}


@router.get("/performance/center", status_code=status.HTTP_200_OK)
async def obter_relatorio_performance(
    current_user: User = Depends(check_admin_role)
):
    """
    Retorna o relatório consolidado do Performance Center monitorado pela POP.
    """
    from services.performance.performance_optimization_platform import pop_platform
    return pop_platform.get_performance_center_report()


@router.post("/performance/optimize", status_code=status.HTTP_200_OK)
async def otimizar_recursos_sistema(
    current_user: User = Depends(check_admin_role)
):
    """
    Força otimização imediata de memória e desalocação de objetos órfãos.
    """
    from services.performance.performance_optimization_platform import pop_platform
    return pop_platform.optimize_memory()


@router.get("/security/center", status_code=status.HTTP_200_OK)
async def obter_relatorio_seguranca(
    current_user: User = Depends(check_admin_role)
):
    """
    Retorna o relatório consolidado do Security Center monitorado pela ESP.
    """
    from services.security.enterprise_security_platform import esp_platform
    return esp_platform.get_security_center_report()


@router.post("/security/backup", status_code=status.HTTP_200_OK)
async def criar_backup_seguro(
    current_user: User = Depends(check_admin_role)
):
    """
    Cria um backup criptografado do catálogo semântico e metadados analíticos.
    """
    from services.security.enterprise_security_platform import esp_platform
    # Simula backup simples com dados fictícios de metadados analíticos
    payload = {
        "export_source": "LuminaAI Security Platform",
        "tenant_id": str(current_user.tenant_id),
        "timestamp": time.time(),
        "catalog_keys": ["vw_vendas", "vw_faturamento"]
    }
    encrypted_str = esp_platform.perform_secured_backup(payload)
    return {"status": "SUCCESS", "backup_data": encrypted_str}


@router.post("/security/restore", status_code=status.HTTP_200_OK)
async def restaurar_backup_seguro(
    payload: dict,
    current_user: User = Depends(check_admin_role)
):
    """
    Restaura permissões e metadados a partir de um backup criptografado verificado.
    """
    from services.security.enterprise_security_platform import esp_platform
    backup_data = payload.get("backup_data")
    if not backup_data:
        raise HTTPException(status_code=400, detail="Chave backup_data ausente no payload.")
        
    try:
        restored = esp_platform.perform_secured_restore(backup_data)
        return {"status": "SUCCESS", "mensagem": "Backup restaurado com sucesso.", "restored_keys": restored.get("catalog_keys")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── INSPECTOR PIPELINE DEBUG ENDPOINTS ──────────────────────────────────────

@router.get("/inspector/traces", status_code=status.HTTP_200_OK)
async def get_inspector_traces(
    current_user: User = Depends(check_admin_role)
):
    """
    Lista todos os traces analíticos recentes gravados em runtime-logs/debug/ para exibição no painel de inspeção.
    """
    import os
    import json
    
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime-logs", "debug")
    if not os.path.exists(log_dir):
        return []
        
    traces = []
    for filename in os.listdir(log_dir):
        if filename.endswith(".json") and filename != "debug_steps.json":
            filepath = os.path.join(log_dir, filename)
            try:
                # Pega apenas metadados iniciais para não estourar payload/performance
                mtime = os.path.getmtime(filepath)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                trace_id = filename.replace("debug_", "").replace(".json", "")
                traces.append({
                    "trace_id": trace_id,
                    "pergunta": data.get("pergunta", "Query sem pergunta"),
                    "intent": data.get("semantic_plan", {}).get("intent", "N/A"),
                    "status": data.get("canonical_plan", {}).get("status") or data.get("status") or "READY",
                    "execution_time_ms": data.get("execution_time_ms", 0.0),
                    "created_at": mtime
                })
            except Exception:
                pass
                
    # Ordena pelos mais recentes
    traces.sort(key=lambda x: x["created_at"], reverse=True)
    return traces[:40]


@router.get("/inspector/trace/{trace_id}", status_code=status.HTTP_200_OK)
async def get_inspector_trace_detail(
    trace_id: str,
    current_user: User = Depends(check_admin_role)
):
    """
    Retorna o payload de trace analítico completo de um ID específico.
    """
    import os
    import json
    
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime-logs", "debug")
    filename = f"debug_{trace_id}.json" if "-" in trace_id else f"{trace_id}.json"
    filepath = os.path.join(log_dir, filename)
    
    if not os.path.exists(filepath):
        # Fallback debug_steps.json
        filepath = os.path.join(log_dir, "debug_steps.json")
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Trace ID ou arquivo de debug correspondente não localizado no servidor.")
            
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo de debug: {e}")


@router.post("/inspector/replay", status_code=status.HTTP_200_OK)
async def run_inspector_replay(
    payload: dict,
    current_user: User = Depends(check_admin_role)
):
    """
    Aciona o replay analítico de um trace e retorna o resultado dinâmico do pipeline.
    """
    import os
    import json
    import time
    from services.metadata_catalog.loader import load_corporate_catalog
    from models.new_pipeline_contracts import SemanticPlan, CanonicalPlan, ExecutionPlan, DashboardState, VisualizationType
    from services.new_query_orchestrator import NewQueryOrchestrator
    from services.metadata_catalog.resolver import metadata_resolver
    from services.metadata_catalog.executor import database_executor
    from services.data_transformer import transform_data
    from models.view_catalog import ChartType as SchemaChartType
    
    trace_id = payload.get("trace_id")
    start_step = (payload.get("start_step") or "resolver").lower()
    call_ai = bool(payload.get("call_ai"))
    
    if not trace_id:
        raise HTTPException(status_code=400, detail="Chave trace_id ausente no payload.")
        
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime-logs", "debug")
    filename = f"debug_{trace_id}.json" if "-" in trace_id else f"{trace_id}.json"
    filepath = os.path.join(log_dir, filename)
    
    if not os.path.exists(filepath):
        filepath = os.path.join(log_dir, "debug_steps.json")
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Trace ID correspondente não encontrado.")
            
    try:
        load_corporate_catalog()
        with open(filepath, "r", encoding="utf-8") as f:
            debug_data = json.load(f)
            
        orchestrator = NewQueryOrchestrator()
        tenant_id = str(current_user.tenant_id)
        
        # 1. Semantic Plan
        semantic_plan_dict = debug_data.get("semantic_plan")
        semantic_plan = None
        if start_step == "semantic":
            if call_ai:
                from services.metadata_catalog.intent_engine import intent_engine
                from services.ai_credential_manager import ai_credential_manager
                lease = await ai_credential_manager.resolve_client(tenant_id=current_user.tenant_id)
                intent_output = await intent_engine.classify_intent(
                    query=debug_data.get("pergunta"),
                    client=lease.client,
                    model=lease.model
                )
                semantic_plan = intent_output.plan
            else:
                semantic_plan = SemanticPlan.model_validate(semantic_plan_dict) if semantic_plan_dict else None
        else:
            if semantic_plan_dict:
                semantic_plan = SemanticPlan.model_validate(semantic_plan_dict)
                
        # 2. Canonical Plan
        canonical_plan_dict = debug_data.get("canonical_plan")
        if start_step in ("semantic", "canonical"):
            canonical_plan = orchestrator.resolver.canonicalize(semantic_plan)
        else:
            canonical_plan = CanonicalPlan.model_validate(canonical_plan_dict) if canonical_plan_dict else None
            
        # 3. Metadata Resolver
        exec_plan_dict = debug_data.get("execution_plan")
        if start_step in ("semantic", "canonical", "resolver"):
            exec_plan = orchestrator.planner.resolve(canonical_plan)
        else:
            exec_plan = ExecutionPlan.model_validate(exec_plan_dict) if exec_plan_dict else None
            
        # 4. SQL Generator
        sql = debug_data.get("sql", {}).get("raw_sql")
        binds = debug_data.get("sql", {}).get("parameters", {})
        if start_step in ("semantic", "canonical", "resolver", "sql"):
            optimized_plan = orchestrator.optimizer.optimize_plan(exec_plan)
            sql, binds = orchestrator.generator.generate_sql(optimized_plan)
            
        # 5. Database Execution
        normalized_rows = debug_data.get("sample_rows", [])
        if start_step in ("semantic", "canonical", "resolver", "sql", "banco"):
            result_dataset = await database_executor.execute_query(
                plan=exec_plan,
                sql=sql,
                binds=binds,
                tenant_id=tenant_id
            )
            normalized_rows = result_dataset.get("values", [])
            
        # 6. Transformer
        transformed_chart_data = debug_data.get("transformer", {}).get("output", {})
        if start_step in ("semantic", "canonical", "resolver", "sql", "banco", "transformer"):
            v_type_str = canonical_plan.suggested_visualization.value.upper() if canonical_plan else "TABLE"
            vis_map = {
                "TABLE": SchemaChartType.TABLE, "BAR": SchemaChartType.BAR, "LINE": SchemaChartType.LINE,
                "PIE": SchemaChartType.PIE, "KPI": SchemaChartType.KPI, "AREA": SchemaChartType.AREA,
                "SCATTER": SchemaChartType.SCATTER
            }
            transformed_chart_data = transform_data(normalized_rows, vis_map.get(v_type_str, SchemaChartType.TABLE))
            
        return {
            "status": "SUCCESS",
            "pergunta": debug_data.get("pergunta"),
            "semantic_plan": semantic_plan.model_dump() if semantic_plan else None,
            "canonical_plan": canonical_plan.model_dump() if canonical_plan else None,
            "execution_plan": exec_plan.model_dump() if exec_plan else None,
            "sql": {"raw_sql": sql, "parameters": binds},
            "sample_rows": normalized_rows[:30],
            "transformer": {"output": transformed_chart_data}
        }
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": traceback.format_exc()})
