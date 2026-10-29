"""Rutas REST para el módulo system."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import TenantContext, get_tenant_context
from app.modules.system.models import SystemAuditLog, SystemTransactionalOutbox
from app.modules.system.schemas import AuditLogResponse, OutboxResponse

router = APIRouter(prefix="/api/v1/system", tags=["System & Audit"])


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = (
        select(SystemAuditLog)
        .where(SystemAuditLog.tenant_id == ctx.tenant_id)
        .order_by(SystemAuditLog.created_at.desc())
        .limit(100)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/outbox", response_model=list[OutboxResponse])
async def list_outbox_events(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = (
        select(SystemTransactionalOutbox)
        .where(SystemTransactionalOutbox.tenant_id == ctx.tenant_id)
        .order_by(SystemTransactionalOutbox.created_at.desc())
        .limit(100)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
