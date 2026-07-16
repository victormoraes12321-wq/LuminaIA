"""
LuminaAI — Rotas de Gerenciamento do Tenant (Visual, IA, Conexão Oracle)
----------------------------------------------------------------------
Este módulo implementa os endpoints de configuração do Tenant:
1. `PUT /settings`: Atualiza o nome, logo_url, configurações visuais, chaves de IA
   e credenciais do Oracle de forma criptografada.
2. `POST /test-oracle`: Testa a conectividade em tempo real com o banco Oracle
   usando os parâmetros enviados na aba Banco de Dados do painel admin.

Regras de Acesso (RBAC):
- Restrito exclusivamente a usuários com privilégios de ADMIN.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from cryptography.fernet import Fernet

from config import settings as app_settings
from database import get_db
from models.user import User
from models.tenant import Tenant
from models.search_history import SearchHistory
from routers.dependencies import check_admin_role, enforce_password_change
from schemas.tenant import TenantResponse, TenantSettingsUpdate
from services.ai_credential_manager import AICMError, ai_credential_manager
from services.ai_invocation_manager import ai_invocation_manager
from services.oracle_service import (
    OracleConnectionValidationError,
    get_oracle_connection,
    decrypt_connection_details,
)
from services.postgresql_clone_service import get_clone_db_connection, close_clone_db_pool

logger = logging.getLogger("luminaai.routers.tenant")

router = APIRouter(
    prefix="/tenant",
    tags=["🏢 Configurações do Tenant"],
    dependencies=[Depends(enforce_password_change)],
)


@router.get(
    "/settings",
    response_model=dict[str, Any],
    summary="Obter Configurações Atuais (Admin-Only)",
    description="Retorna as configurações atuais visuais, de IA e banco de dados (mascaradas) do tenant.",
)
async def get_tenant_settings(
    current_user: Annotated[User, Depends(check_admin_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, Any]:
    """
    Retorna os dados do tenant para o formulário do admin, mascarando a senha do banco.
    """
    stmt = select(Tenant).where(Tenant.id == current_user.tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant não encontrado.",
        )
        
    # Helper para decodificar JSON se vier como string
    def safe_parse_json(val: Any) -> dict:
        if isinstance(val, dict):
            return val
        if isinstance(val, str) and val.strip():
            try:
                return json.loads(val)
            except Exception:
                pass
        return {}

    oracle_conn = safe_parse_json(tenant.oracle_conn)
    clone_db_conn = safe_parse_json(tenant.clone_db_conn)
    ia_config = safe_parse_json(tenant.ia_config)
    sync_config = safe_parse_json(tenant.sync_config)

    # Tenta decodificar a conexão atual para extrair host/porta/usuário/sid/service_name
    oracle_info = {"host": "", "port": 1521, "user": "", "password": "", "sid": "", "service_name": ""}
    
    if oracle_conn and oracle_conn.get("payload"):
        try:
            payload = oracle_conn["payload"]
            if payload != "DEMO_TENANT_ORACLE_CONN_ENCRYPTED_REPLACE_WITH_REAL":
                key_bytes = app_settings.ENCRYPTION_KEY.encode("utf-8")
                f = Fernet(key_bytes)
                decrypted_bytes = f.decrypt(payload.encode("utf-8"))
                decrypted_str = decrypted_bytes.decode("utf-8")
                raw_conn = json.loads(decrypted_str)
                
                # Mascara a senha para segurança
                oracle_info = {
                    "host": raw_conn.get("host", ""),
                    "port": raw_conn.get("port", 1521),
                    "user": raw_conn.get("user", ""),
                    "password": "••••••••" if raw_conn.get("password") else "",
                    "sid": raw_conn.get("sid", ""),
                    "service_name": raw_conn.get("service_name", ""),
                }
        except Exception:
            logger.warning("Falha ao descriptografar conexão existente para exibição.")
            
    # Tenta decodificar a conexão do PostgreSQL clonado para extrair host/porta/usuário/banco
    postgres_clone_info = {"host": "", "port": 5432, "user": "", "password": "", "database": ""}
    
    if clone_db_conn and clone_db_conn.get("payload"):
        try:
            payload = clone_db_conn["payload"]
            if payload != "DEMO_TENANT_CLONE_CONN_ENCRYPTED_REPLACE_WITH_REAL":
                key_bytes = app_settings.ENCRYPTION_KEY.encode("utf-8")
                f = Fernet(key_bytes)
                decrypted_bytes = f.decrypt(payload.encode("utf-8"))
                decrypted_str = decrypted_bytes.decode("utf-8")
                raw_conn = json.loads(decrypted_str)
                
                # Mascara a senha para segurança
                postgres_clone_info = {
                    "host": raw_conn.get("host", ""),
                    "port": raw_conn.get("port", 5432),
                    "user": raw_conn.get("user", ""),
                    "password": "••••••••" if raw_conn.get("password") else "",
                    "database": raw_conn.get("database", ""),
                }
        except Exception:
            logger.warning("Falha ao descriptografar conexão do clone existente para exibição.")
            
    # Mascara a API Key de IA se houver
    ia_info = ia_config.copy()
    if ia_info.get("api_key"):
        key = ia_info["api_key"]
        ia_info["api_key"] = ai_credential_manager.mask_credential(key)
        
    # Mascara chaves de API nos modelos cadastrados
    registered_models = ia_info.get("registered_models", [])
    masked_models = []
    for model in registered_models:
        model_copy = model.copy()
        m_key = model_copy.get("api_key", "")
        if m_key:
            model_copy["api_key"] = ai_credential_manager.mask_credential(m_key)
        masked_models.append(model_copy)
    ia_info["registered_models"] = masked_models
        
    return {
        "id": tenant.id,
        "nome": tenant.nome,
        "logo_url": tenant.logo_url,
        "tema_config": tenant.tema_config,
        "ia_config": ia_info,
        "oracle_conn": oracle_info,
        "clone_db_conn": postgres_clone_info,
        "sync_config": sync_config or {"enabled": False, "times": []},
        "ativo": tenant.ativo,
    }


@router.put(
    "/settings",
    response_model=TenantResponse,
    summary="Atualizar Configurações do Tenant (Admin-Only)",
    description=(
        "Salva as configurações de tema, IA e Banco de Dados. Credenciais "
        "sensíveis (como a senha do Oracle) são criptografadas com Fernet "
        "antes de serem salvas no PostgreSQL."
    ),
)
async def update_tenant_settings(
    payload: TenantSettingsUpdate,
    current_user: Annotated[User, Depends(check_admin_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TenantResponse:
    """
    Atualiza as configurações do tenant do administrador atual.
    Criptografa as credenciais do Oracle Database e chaves de API.
    """
    # 1. Busca o tenant no PostgreSQL
    stmt = select(Tenant).where(Tenant.id == current_user.tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant não encontrado no sistema.",
        )
        
    # Helper para decodificar JSON se vier como string
    def safe_parse_json(val: Any) -> dict:
        if isinstance(val, dict):
            return val
        if isinstance(val, str) and val.strip():
            try:
                return json.loads(val)
            except Exception:
                pass
        return {}

    current_theme = safe_parse_json(tenant.tema_config)
    current_ia = safe_parse_json(tenant.ia_config)
    current_oracle = safe_parse_json(tenant.oracle_conn)
    current_clone = safe_parse_json(tenant.clone_db_conn)
    current_sync = safe_parse_json(tenant.sync_config)

    # 2. Atualiza dados cadastrais
    if payload.nome is not None:
        tenant.nome = payload.nome
        
    if payload.logo_url is not None:
        tenant.logo_url = payload.logo_url
        
    # 3. Atualiza configurações de Tema (merge)
    if payload.tema_config is not None:
        tenant.tema_config = {**current_theme, **payload.tema_config}
        
    # 4. Atualiza configurações de IA (merge + encrypt api_key se enviada)
    if payload.ia_config is not None:
        new_ia = payload.ia_config.copy()
        
        # Helper para verificar se a chave está mascarada ou corrompida
        def is_masked_key(k: str | None) -> bool:
            if not k:
                return False
            return "•" in k or "●" in k or "•" in k or "●" in k or "*" in k or any(ord(c) > 127 for c in k)

        # Se a chave foi enviada como mascarada, mantém a anterior do banco
        if new_ia.get("api_key") and is_masked_key(new_ia["api_key"]):
            new_ia["api_key"] = current_ia.get("api_key", "")
            
        # Se a lista de modelos de IA registrados foi enviada, mergeia preservando as chaves anteriores do banco se vierem mascaradas
        current_models = current_ia.get("registered_models", [])
        new_models = new_ia.get("registered_models", [])
        
        merged_models = []
        for n_mod in new_models:
            n_mod_copy = n_mod.copy()
            # Encontra o correspondente existente pelo ID
            matched = next((c_mod for c_mod in current_models if c_mod.get("id") == n_mod_copy.get("id")), None)
            if matched and n_mod_copy.get("api_key") and is_masked_key(n_mod_copy["api_key"]):
                n_mod_copy["api_key"] = matched.get("api_key", "")
            merged_models.append(n_mod_copy)
            
        new_ia["registered_models"] = merged_models
        tenant.ia_config = {**current_ia, **new_ia}
        
        # Invalidate tenant cached OpenAI client
        from services.ai_service import close_tenant_openai_client
        await close_tenant_openai_client(current_user.tenant_id)
        
    # 5. Atualiza conexão do Oracle (criptografia Fernet)
    if payload.oracle_conn is not None:
        # Se a senha veio vazia ou mascarada, tenta preservar a senha antiga.
        conn_payload = payload.oracle_conn.copy()
        password = conn_payload.get("password")
        
        old_password = None
        if current_oracle and current_oracle.get("payload"):
            try:
                old_payload = current_oracle["payload"]
                if old_payload != "DEMO_TENANT_ORACLE_CONN_ENCRYPTED_REPLACE_WITH_REAL":
                    key_bytes = app_settings.ENCRYPTION_KEY.encode("utf-8")
                    f = Fernet(key_bytes)
                    decrypted = f.decrypt(old_payload.encode("utf-8"))
                    old_conn = json.loads(decrypted.decode("utf-8"))
                    old_password = old_conn.get("password")
            except Exception:
                logger.warning("Falha ao recuperar a senha antiga do Oracle para merge.")
                
        if not password or "•••" in password or "•••" in password:
            conn_payload["password"] = old_password or ""
            
        # Realiza a criptografia com a chave simétrica Fernet
        try:
            key_bytes = app_settings.ENCRYPTION_KEY.encode("utf-8")
            f = Fernet(key_bytes)
            
            # Converte a conexão plana em string JSON e criptografa
            serialized = json.dumps(conn_payload).encode("utf-8")
            encrypted_payload = f.encrypt(serialized).decode("utf-8")
            
            tenant.oracle_conn = {
                "encrypted": True,
                "algorithm": "Fernet",
                "payload": encrypted_payload
            }
        except Exception as exc:
            logger.error("Erro crítico de criptografia de banco ao salvar configurações: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criptografar credenciais do banco. Configurações não salvas.",
            ) from exc
            
        # Invalidate the Oracle connection pool for this tenant
        from services.oracle_service import close_oracle_pool
        await close_oracle_pool(current_user.tenant_id)

    # 6. Atualiza conexão do Postgres Clone (criptografia Fernet)
    if payload.clone_db_conn is not None:
        conn_payload = payload.clone_db_conn.copy()
        password = conn_payload.get("password")
        
        old_password = None
        if current_clone and current_clone.get("payload"):
            try:
                old_payload = current_clone["payload"]
                if old_payload != "DEMO_TENANT_CLONE_CONN_ENCRYPTED_REPLACE_WITH_REAL":
                    key_bytes = app_settings.ENCRYPTION_KEY.encode("utf-8")
                    f = Fernet(key_bytes)
                    decrypted = f.decrypt(old_payload.encode("utf-8"))
                    old_conn = json.loads(decrypted.decode("utf-8"))
                    old_password = old_conn.get("password")
            except Exception:
                logger.warning("Falha ao recuperar a senha antiga do clone para merge.")
                
        if not password or "•••" in password or "•••" in password:
            conn_payload["password"] = old_password or ""
            
        try:
            key_bytes = app_settings.ENCRYPTION_KEY.encode("utf-8")
            f = Fernet(key_bytes)
            serialized = json.dumps(conn_payload).encode("utf-8")
            encrypted_payload = f.encrypt(serialized).decode("utf-8")
            
            tenant.clone_db_conn = {
                "encrypted": True,
                "algorithm": "Fernet",
                "payload": encrypted_payload
            }
        except Exception as exc:
            logger.error("Erro crítico de criptografia ao salvar credenciais do clone: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criptografar credenciais do clone. Configurações não salvas.",
            ) from exc
            
        # Invalidate the PostgreSQL connection pool for this tenant
        await close_clone_db_pool(current_user.tenant_id)

    # 7. Atualiza configurações de Sincronização
    if payload.sync_config is not None:
        tenant.sync_config = {
            "enabled": payload.sync_config.get("enabled", current_sync.get("enabled", False)),
            "times": payload.sync_config.get("times", current_sync.get("times", [])),
            "last_sync": current_sync.get("last_sync"),
            "last_sync_status": current_sync.get("last_sync_status"),
            "last_sync_message": current_sync.get("last_sync_message")
        }
            
    await db.commit()
    await db.refresh(tenant)
    
    logger.info("Configurações do Tenant %s atualizadas com sucesso pelo Admin %s", tenant.nome, current_user.email)
    return TenantResponse.model_validate(tenant)


@router.post(
    "/test-oracle",
    summary="Testar Conexão Oracle (Admin-Only)",
    description="Tenta estabelecer uma conexão em modo Thin com as credenciais especificadas para validar o formulário.",
)
async def test_oracle_connection(
    conn_params: dict[str, Any],
    current_user: Annotated[User, Depends(check_admin_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, Any]:
    """
    Recebe os parâmetros do banco de dados na aba de configurações e testa a conectividade.
    Lança erro descritivo em caso de falha de conexão ou credenciais inválidas.
    """
    logger.info("Executando teste de conexão Oracle solicitado pelo Admin: %s", current_user.email)
    # Se o simulador de Oracle estiver ativo globalmente no backend,
    # retorna sucesso simulado para permitir que o usuário configure parâmetros fictícios locais.
    if app_settings.MOCK_ORACLE:
        logger.info("[MockOracle] Simulando teste de conexão Oracle com sucesso para desenvolvimento.")
        return {
            "success": True,
            "message": "Conexão com o banco Oracle estabelecida com sucesso! (Modo Simulação Ativo)",
        }

    # 1. Se a senha vier mascarada ou vazia, recupera a senha cadastrada no banco para testar
    password = conn_params.get("password")
    if not password or "•••" in password or "•••" in password:
        stmt = select(Tenant).where(Tenant.id == current_user.tenant_id)
        res = await db.execute(stmt)
        tenant = res.scalar_one_or_none()
        
        saved_password = None
        oracle_conn = tenant.oracle_conn if tenant else None
        if isinstance(oracle_conn, str) and oracle_conn.strip():
            try:
                oracle_conn = json.loads(oracle_conn)
            except Exception:
                oracle_conn = {}
        if tenant and oracle_conn and oracle_conn.get("payload"):
            try:
                details = decrypt_connection_details(oracle_conn)
                saved_password = details.get("password")
            except Exception as exc:
                logger.warning("Falha ao recuperar a senha antiga do Oracle para o teste: %s", exc)
                
        if not saved_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Para realizar o teste de conexão, informe a senha atual ou digite a nova senha.",
            )
        conn_params["password"] = saved_password
        
    try:
        # 2. Abre a conexão de forma assíncrona (Thin mode)
        conn = await get_oracle_connection(conn_params, ignore_mock_global=True)
        
        # 3. Fecha a conexão imediatamente após obter sucesso
        await conn.close()
        return {
            "success": True,
            "message": "Conexão com o banco Oracle estabelecida com sucesso!",
        }
    except OracleConnectionValidationError as exc:
        logger.warning(
            "Teste Oracle falhou para o admin %s | code=%s | detail=%s",
            current_user.email,
            exc.code,
            exc.technical_detail,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.user_message,
        ) from None
    except Exception as exc:
        # Registra o erro real e detalhado no console do servidor para fins de diagnóstico interno (seguro)
        logger.warning("Erro de teste de conexão com o banco Oracle para o tenant do admin %s: %s", current_user.email, exc)
        # Retorna uma mensagem amigável, higienizada e segura para o cliente, ocultando IPs, portas ou credenciais
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Não foi possível estabelecer contato com o servidor do banco Oracle. "
                "Verifique se o host, a porta, o usuário e a senha estão corretos e tente novamente."
            ),
        ) from None


@router.post(
    "/test-ai",
    summary="Testar Conexão de IA (Admin-Only)",
    description="Tenta validar a chave de API da OpenAI efetuando uma chamada simples de teste de modelo.",
)
async def test_ai_connection(
    conn_params: dict[str, Any],
    current_user: Annotated[User, Depends(check_admin_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, Any]:
    """
    Testa a credencial de IA exclusivamente pelo AI Credential Manager.
    """
    logger.info("Executando teste de conexao IA solicitado pelo Admin: %s", current_user.email)

    raw_api_key = conn_params.get("api_key")
    explicit_api_key = None
    explicit_key_provided = False
    if isinstance(raw_api_key, str) and raw_api_key.strip():
        key = raw_api_key.strip()
        if not any(marker in key for marker in ("*", "•", "●", "•", "●")):
            explicit_key_provided = True
            if ai_credential_manager.is_probably_invalid_key(key):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Falha ao validar a chave de API da OpenAI. Para realizar o teste de conexão, informe uma chave de API válida.",
                )
            explicit_api_key = key

    requested_model = conn_params.get("model_base") or conn_params.get("model")

    try:
        report = await ai_credential_manager.validate_connection(
            tenant_id=current_user.tenant_id,
            db=db,
            explicit_api_key=explicit_api_key,
            requested_model=requested_model,
            allow_global_fallback=not explicit_key_provided,
        )
        return {
            "success": True,
            "message": "Conexao com o provider de IA estabelecida com sucesso pelo AI Credential Manager.",
            "provider": report.get("provider"),
            "model": report.get("model"),
            "credential_hash": report.get("credential_hash"),
            "latency_ms": report.get("latency_ms"),
        }
    except AICMError as exc:
        logger.warning("Erro controlado do AICM no teste IA do tenant %s: %s", current_user.tenant_id, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.user_message,
        ) from None
    except Exception as exc:
        logger.warning("Erro de teste de conexao IA para o tenant do admin %s: %s", current_user.email, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha ao validar a credencial de IA. Verifique a chave configurada e tente novamente.",
        ) from None


@router.get(
    "/ai-status",
    summary="Status do AI Credential Manager (Admin-Only)",
    description="Retorna saude, fallback, cooldown e auditoria segura das credenciais de IA sem expor segredos.",
)
async def get_ai_credential_status(
    current_user: Annotated[User, Depends(check_admin_role)]
) -> dict[str, Any]:
    return ai_credential_manager.get_status(current_user.tenant_id)


@router.get(
    "/aim-status",
    summary="Status do AI Invocation Manager (Admin-Only)",
    description="Retorna decisões, estratégias, tokens, cache, custo e latência governados pelo AIM.",
)
async def get_ai_invocation_status(
    current_user: Annotated[User, Depends(check_admin_role)]
) -> dict[str, Any]:
    return ai_invocation_manager.get_status(current_user.tenant_id)


@router.get(
    "/audit-logs",
    summary="Obter logs de auditoria de consultas (Admin-Only)",
    description="Retorna os logs de consultas de todos os usuários do tenant para monitoramento de IA.",
)
async def get_tenant_audit_logs(
    current_user: Annotated[User, Depends(check_admin_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> list[dict[str, Any]]:
    """
    Retorna a lista das últimas 100 consultas realizadas pelos usuários deste tenant,
    unindo dados de usuários e metadados de views catalogadas.
    """
    stmt = (
        select(SearchHistory)
        .join(User, SearchHistory.user_id == User.id)
        .options(
            joinedload(SearchHistory.user),
            joinedload(SearchHistory.view_catalog)
        )
        .where(User.tenant_id == current_user.tenant_id)
        .order_by(SearchHistory.criado_em.desc())
        .limit(100)
    )
    res = await db.execute(stmt)
    logs = res.scalars().all()
    
    out = []
    for log in logs:
        out.append({
            "id": str(log.id),
            "pergunta": log.pergunta_texto,
            "parametros": log.parametros_extraidos,
            "ia_confianca": float(log.ia_confianca) if log.ia_confianca is not None else None,
            "tempo_resposta_ms": log.tempo_resposta_ms,
            "criado_em": log.criado_em.isoformat(),
            "usuario": {
                "nome": log.user.nome,
                "email": log.user.email,
                "role": log.user.role.value
            },
            "view": {
                "nome_view_oracle": log.view_catalog.nome_view_oracle if log.view_catalog else None,
                "tipo_grafico_padrao": log.view_catalog.tipo_grafico_padrao.value if log.view_catalog else None
            }
        })
    return out


@router.post(
    "/test-postgres-clone",
    summary="Testar Conexão PostgreSQL do Clone (Admin-Only)",
    description="Tenta estabelecer uma conexão com as credenciais especificadas do clone para validar o formulário.",
)
async def test_postgres_clone_connection(
    conn_params: dict[str, Any],
    current_user: Annotated[User, Depends(check_admin_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, Any]:
    """
    Recebe os parâmetros do banco de dados clonado e testa a conectividade.
    """
    logger.info("Executando teste de conexão Postgres Clone solicitado pelo Admin: %s", current_user.email)
    
    # Se a senha vier mascarada ou vazia, recupera a senha cadastrada
    password = conn_params.get("password")
    if not password or "•••" in password or "•••" in password:
        stmt = select(Tenant).where(Tenant.id == current_user.tenant_id)
        res = await db.execute(stmt)
        tenant = res.scalar_one_or_none()
        
        saved_password = None
        clone_db_conn = tenant.clone_db_conn if tenant else None
        if isinstance(clone_db_conn, str) and clone_db_conn.strip():
            try:
                clone_db_conn = json.loads(clone_db_conn)
            except Exception:
                clone_db_conn = {}
        if tenant and clone_db_conn and clone_db_conn.get("payload"):
            try:
                details = decrypt_connection_details(clone_db_conn)
                saved_password = details.get("password")
            except Exception as exc:
                logger.warning("Falha ao recuperar a senha antiga do clone para o teste: %s", exc)
                
        if not saved_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Para realizar o teste de conexão, informe a senha atual ou digite a nova senha.",
            )
        conn_params["password"] = saved_password
        
    try:
        # Abre a conexão
        conn = await get_clone_db_connection(conn_params)
        await conn.close()
        return {
            "success": True,
            "message": "Conexão com o banco PostgreSQL clonado estabelecida com sucesso!",
        }
    except Exception as exc:
        logger.warning("Erro de teste de conexão com o banco do clone para o admin %s: %s", current_user.email, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Não foi possível estabelecer contato com o banco de dados clonado. "
                "Verifique se o host, a porta, o usuário, a senha e o nome do banco estão corretos."
            )
        ) from None


@router.post(
    "/sync-now",
    summary="Forçar Sincronização Imediata (Admin-Only)",
    description="Dispara manualmente a rotina de sincronização dos dados do Oracle para o PostgreSQL Clone em background.",
)
async def trigger_tenant_sync(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(check_admin_role)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Executa a rotina de sincronização imediatamente em segundo plano.
    """
    logger.info("Sincronização manual solicitada pelo Admin: %s", current_user.email)
    
    from models.tenant import Tenant
    from sqlalchemy import select
    import json
    
    # ── Validação Estrita de Janela de Horários Configurados ──
    stmt_t = select(Tenant).where(Tenant.id == current_user.tenant_id)
    res_t = await db.execute(stmt_t)
    tenant = res_t.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant não encontrado."
        )

    # Bloqueia se estiver em produção fora dos horários programados
    if app_settings.ENVIRONMENT == "production":
        sync_config = tenant.sync_config or {}
        if isinstance(sync_config, str):
            try:
                sync_config = json.loads(sync_config)
            except Exception:
                sync_config = {}
                
        if not sync_config.get("enabled", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A sincronização não está habilitada nas configurações deste tenant."
            )
            
        from services.data_platform.sync_scheduler import sync_orchestrator
        local_time = sync_orchestrator._get_localized_time(sync_config.get("timezone", "America/Sao_Paulo"))
        if not sync_orchestrator.should_trigger_sync(sync_config, local_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Operação rejeitada: Em produção, todas as views devem ser sincronizadas exclusivamente nos horários configurados. Horário local atual ({local_time.strftime('%H:%M')}) fora da janela programada."
            )
            
    # 1. Verifica rápido se já há sync ativa
    from services.sync_service import _active_syncs
    import uuid
    tenant_key = uuid.UUID(str(current_user.tenant_id))
    if tenant_key in _active_syncs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sincronização já em andamento para esta empresa."
        )
        
    # 2. Executa a sincronização em background usando um contexto isolado de sessão
    async def run_sync_in_background():
        from database import get_db_context
        from services.sync_service import sync_tenant_database
        try:
            async with get_db_context() as session:
                await sync_tenant_database(current_user.tenant_id, session)
        except Exception as exc:
            logger.error("Erro na sincronização manual em background: %s", exc)

    background_tasks.add_task(run_sync_in_background)
    
    return {
        "success": True,
        "message": "Sincronização iniciada com sucesso. Os dados estão sendo atualizados em segundo plano.",
    }

@router.get(
    "/sync-progress",
    summary="Consultar Progresso da Sincronizacao (Admin-Only)",
    description="Retorna o progresso em tempo quase real da sincronizacao Oracle -> PostgreSQL Clone do tenant atual.",
)
async def get_tenant_sync_progress(
    current_user: Annotated[User, Depends(check_admin_role)],
) -> dict[str, Any]:
    from services.sync_service import get_sync_progress

    progress = await get_sync_progress(current_user.tenant_id)
    if not progress:
        return {
            "active": False,
            "status": "idle",
            "phase": "idle",
            "percent": 0.0,
            "current_view": None,
            "current_view_index": 0,
            "total_views": 0,
            "current_view_rows": 0,
            "current_view_estimated_rows": None,
            "processed_views": 0,
            "processed_rows": 0,
            "total_rows": 0,
            "message": "Nenhuma sincronizacao em andamento.",
            "updated_at": None,
            "started_at": None,
            "finished_at": None,
            "error": None,
        }
    return progress
