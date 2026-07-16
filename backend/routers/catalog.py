"""
LuminaAI — Rotas de Gerenciamento do Catálogo de Views Oracle
------------------------------------------------------------
Este módulo implementa o CRUD completo para gerenciar as views cadastradas
no catálogo do tenant. Essas views definem quais consultas o motor de inteligência
artificial (ai_service) pode invocar de forma parametrizada.

Regras de Acesso (RBAC):
- O acesso a estes endpoints é restrito exclusivamente a usuários com papel
  ADMIN ou GESTOR.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from database import get_db
from models.user import User
from models.view_catalog import ViewCatalog
from routers.dependencies import check_admin_or_gestor_role, enforce_password_change
from schemas.view_catalog import (
    ViewCatalogCreate,
    ViewCatalogResponse,
    ViewCatalogUpdate,
)

logger = logging.getLogger("luminaai.routers.catalog")


def _get_catalog_api():
    from services.data_platform.catalog_api import catalog_api
    return catalog_api


router = APIRouter(
    prefix="/catalog",
    tags=["📋 Catálogo de Views"],
    dependencies=[Depends(enforce_password_change)],
)


@router.get(
    "/",
    response_model=list[ViewCatalogResponse],
    summary="Listar Todas as Views do Catálogo (Admin/Gestor-Only)",
    description="Retorna a lista completa de views cadastradas no catálogo do tenant associado ao usuário.",
)
async def list_catalog_views(
    current_user: Annotated[User, Depends(check_admin_or_gestor_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> list[ViewCatalogResponse]:
    """
    Lista todas as views ativas e inativas pertencentes ao tenant do usuário autenticado.
    """
    logger.info("Listando catálogo de views do tenant: %s", str(current_user.tenant_id)[:8])
    stmt = (
        select(ViewCatalog)
        .where(ViewCatalog.tenant_id == current_user.tenant_id)
        .order_by(ViewCatalog.nome_view_oracle.asc())
    )
    result = await db.execute(stmt)
    views = result.scalars().all()
    return [ViewCatalogResponse.model_validate(v) for v in views]


@router.post(
    "/",
    response_model=ViewCatalogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar Nova View no Catálogo (Admin/Gestor-Only)",
    description=(
        "Cadastra uma nova view Oracle no catálogo do tenant. A descrição da view "
        "será imediatamente disponibilizada no prompt da IA como contexto para matching."
    ),
)
async def create_catalog_view(
    payload: ViewCatalogCreate,
    current_user: Annotated[User, Depends(check_admin_or_gestor_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ViewCatalogResponse:
    """
    Insere uma nova definição de view no catálogo associado ao tenant do usuário.
    Garante unicidade do nome da view por tenant.
    """
    # 1. Verifica se já existe uma view com o mesmo nome no catálogo do mesmo tenant
    stmt = select(ViewCatalog).where(
        ViewCatalog.nome_view_oracle == payload.nome_view_oracle.upper(),
        ViewCatalog.tenant_id == current_user.tenant_id
    )
    res = await db.execute(stmt)
    existing_view = res.scalar_one_or_none()
    
    if existing_view is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uma view com o nome '{payload.nome_view_oracle}' já está cadastrada no catálogo do seu Tenant.",
        )
        
    # 2. Cria a nova entidade mapeada do SQLAlchemy
    new_view = ViewCatalog(
        tenant_id=current_user.tenant_id,
        nome_view_oracle=payload.nome_view_oracle.upper(),  # Força uppercase para bater com as convenções do Oracle
        descricao_para_ia=payload.descricao_para_ia,
        tipo_grafico_padrao=payload.tipo_grafico_padrao,
        parametros_schema=payload.parametros_schema,
        ativo=True
    )
    
    db.add(new_view)
    await db.commit()
    await db.refresh(new_view)
    
    logger.info(
        "Nova view cadastrada no catálogo: view=%s | tenant=%s | autor=%s",
        new_view.nome_view_oracle,
        str(new_view.tenant_id)[:8],
        current_user.email
    )
    
    try:
        await _get_catalog_api().register(
            tenant_id=current_user.tenant_id,
            tipo="VIEW",
            dados={
                "estrutura_id": new_view.nome_view_oracle,
                "nome_view": new_view.nome_view_oracle,
                "origem": "ERP_ORACLE",
                "owner": current_user.email,
                "categoria": "Catalogo",
                "tags": ["catalog", "view"],
                "filtros_padrao": new_view.parametros_schema or {},
                "status": "success" if new_view.ativo else "inactive",
                "integridade": "valid",
                "autor": current_user.email,
                "motivo": "Cadastro via catalogo administrativo",
            },
            lineage_tabelas=[new_view.nome_view_oracle.replace("VW_", "")],
            upstream_ids=[new_view.nome_view_oracle.replace("VW_", "")],
        )
    except Exception as exc:
        logger.warning("Falha ao registrar view no Metadata Catalog: %s", exc)
    
    return ViewCatalogResponse.model_validate(new_view)


@router.put(
    "/{view_id}",
    response_model=ViewCatalogResponse,
    summary="Atualizar View do Catálogo (Admin/Gestor-Only)",
    description="Atualiza as configurações, descrição semântica ou status de ativação de uma view existente.",
)
async def update_catalog_view(
    view_id: uuid.UUID,
    payload: ViewCatalogUpdate,
    current_user: Annotated[User, Depends(check_admin_or_gestor_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ViewCatalogResponse:
    """
    Atualiza dados de uma view específica. Protege o tenant impedindo modificação de views de terceiros.
    """
    # 1. Busca a view e valida se pertence ao tenant do usuário
    stmt = select(ViewCatalog).where(
        ViewCatalog.id == view_id,
        ViewCatalog.tenant_id == current_user.tenant_id
    )
    res = await db.execute(stmt)
    view = res.scalar_one_or_none()
    
    if view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="A view especificada não foi encontrada no catálogo do seu Tenant.",
        )
        
    # 2. Aplica as alterações parciais fornecidas no payload
    try:
        await _get_catalog_api().snapshot(
            tenant_id=current_user.tenant_id,
            estrutura_id=view.nome_view_oracle,
            motivo="Antes de atualizar view via catalogo administrativo",
            autor=current_user.email,
        )
    except Exception as exc:
        logger.debug("Snapshot do Metadata Catalog ignorado: %s", exc)
        
    if payload.descricao_para_ia is not None:
        view.descricao_para_ia = payload.descricao_para_ia
        
    if payload.tipo_grafico_padrao is not None:
        view.tipo_grafico_padrao = payload.tipo_grafico_padrao
        
    if payload.parametros_schema is not None:
        view.parametros_schema = payload.parametros_schema
        
    if payload.ativo is not None:
        view.ativo = payload.ativo
        
    await db.commit()
    await db.refresh(view)
    
    logger.info(
        "View do catálogo atualizada: view=%s | tenant=%s | ativo=%s",
        view.nome_view_oracle,
        str(view.tenant_id)[:8],
        view.ativo
    )
    
    try:
        await _get_catalog_api().register(
            tenant_id=current_user.tenant_id,
            tipo="VIEW",
            dados={
                "estrutura_id": view.nome_view_oracle,
                "nome_view": view.nome_view_oracle,
                "origem": "ERP_ORACLE",
                "owner": current_user.email,
                "categoria": "Catalogo",
                "tags": ["catalog", "view"],
                "filtros_padrao": view.parametros_schema or {},
                "status": "success" if view.ativo else "inactive",
                "integridade": "valid" if view.ativo else "degraded",
                "autor": current_user.email,
                "motivo": "Atualizacao via catalogo administrativo",
            },
            lineage_tabelas=[view.nome_view_oracle.replace("VW_", "")],
            upstream_ids=[view.nome_view_oracle.replace("VW_", "")],
        )
    except Exception as exc:
        logger.warning("Falha ao atualizar Metadata Catalog da view: %s", exc)
    
    return ViewCatalogResponse.model_validate(view)


@router.delete(
    "/{view_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Deletar View do Catálogo (Admin/Gestor-Only)",
    description="Remove permanentemente uma view do catálogo de consultas do tenant.",
)
async def delete_catalog_view(
    view_id: uuid.UUID,
    current_user: Annotated[User, Depends(check_admin_or_gestor_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Response:
    """
    Remove uma view específica do catálogo de views. Valida o isolamento por tenant.
    """
    stmt = select(ViewCatalog).where(
        ViewCatalog.id == view_id,
        ViewCatalog.tenant_id == current_user.tenant_id
    )
    res = await db.execute(stmt)
    view = res.scalar_one_or_none()
    
    if view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="A view especificada não foi encontrada no catálogo do seu Tenant.",
        )
        
    try:
        api = _get_catalog_api()
        await api.snapshot(
            tenant_id=current_user.tenant_id,
            estrutura_id=view.nome_view_oracle,
            motivo="Antes de remover view do catalogo operacional",
            autor=current_user.email,
        )
        await api.register(
            tenant_id=current_user.tenant_id,
            tipo="VIEW",
            dados={
                "estrutura_id": view.nome_view_oracle,
                "nome_view": view.nome_view_oracle,
                "origem": "ERP_ORACLE",
                "owner": current_user.email,
                "categoria": "Catalogo",
                "tags": ["catalog", "view", "deleted"],
                "status": "deleted",
                "integridade": "degraded",
                "autor": current_user.email,
                "motivo": "Remocao via catalogo administrativo",
            },
        )
    except Exception as exc:
        logger.warning("Falha ao registrar remocao no Metadata Catalog: %s", exc)
        
    await db.delete(view)
    await db.commit()
    
    logger.info(
        "View deletada do catálogo: id=%s | tenant=%s | autor=%s",
        str(view_id),
        str(current_user.tenant_id)[:8],
        current_user.email
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
