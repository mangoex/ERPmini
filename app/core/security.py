"""Seguridad, Contexto Multitenancy (RLS) y RBAC para ERPmini."""

import uuid
from typing import Annotated

from fastapi import Header, Request
from pydantic import BaseModel, Field

from app.core.uuid7 import generate_uuid7


class TenantContext(BaseModel):
    """Contexto de seguridad y tenencia para la sesión actual."""

    tenant_id: uuid.UUID
    branch_id: uuid.UUID
    user_id: uuid.UUID
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


async def get_tenant_context(
    request: Request,
    x_tenant_id: Annotated[str | None, Header()] = None,
    x_branch_id: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
    x_user_roles: Annotated[str | None, Header()] = None,
) -> TenantContext:
    """Extrae o provee un contexto de Tenant y permisos para las peticiones HTTP."""
    tenant_id = uuid.UUID(x_tenant_id) if x_tenant_id else generate_uuid7()
    branch_id = uuid.UUID(x_branch_id) if x_branch_id else generate_uuid7()
    user_id = uuid.UUID(x_user_id) if x_user_id else generate_uuid7()
    roles = (
        [r.strip() for r in x_user_roles.split(",") if r.strip()]
        if x_user_roles
        else ["ADMIN_PLANTA"]
    )
    permissions = ["*"] if "ADMIN_PLANTA" in roles else []

    return TenantContext(
        tenant_id=tenant_id,
        branch_id=branch_id,
        user_id=user_id,
        roles=roles,
        permissions=permissions,
    )
