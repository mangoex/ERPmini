"""Servicios del módulo system: Auditoría, Outbox y RBAC."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RBACPermissionDeniedError
from app.core.security import TenantContext
from app.core.uuid7 import generate_uuid7
from app.modules.system.models import SystemAuditLog, SystemTransactionalOutbox


class AuditService:
    """Servicio de pista de auditoría inmutable."""

    @staticmethod
    async def log_change(
        session: AsyncSession,
        ctx: TenantContext,
        entity_name: str,
        entity_id: uuid.UUID,
        action: str,
        previous_value: dict | None = None,
        new_value: dict | None = None,
    ) -> SystemAuditLog:
        entry = SystemAuditLog(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            user_id=ctx.user_id,
            entity_name=entity_name,
            entity_id=entity_id,
            action=action,
            previous_value=previous_value,
            new_value=new_value,
        )
        session.add(entry)
        await session.flush()
        return entry


class OutboxService:
    """Servicio del Transactional Outbox."""

    @staticmethod
    async def publish(
        session: AsyncSession,
        ctx: TenantContext,
        event_type: str,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        payload: dict,
    ) -> SystemTransactionalOutbox:
        outbox = SystemTransactionalOutbox(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            status="PENDING",
        )
        session.add(outbox)
        await session.flush()
        return outbox


class RBACService:
    """Servicio de verificación estricta de permisos RBAC."""

    @staticmethod
    def check_permission(ctx: TenantContext, required_permission: str) -> bool:
        if "*" in ctx.permissions or "ADMIN_PLANTA" in ctx.roles:
            return True
        if required_permission in ctx.permissions:
            return True
        raise RBACPermissionDeniedError(
            f"Access denied: User {ctx.user_id} lacks permission '{required_permission}'"
        )
