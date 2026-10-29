"""Rutas REST para el módulo bot."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import RBACPermissionDeniedError
from app.core.security import TenantContext, get_tenant_context
from app.core.uuid7 import generate_uuid7
from app.modules.bot.schemas import WhatsAppWebhookPayload, WhatsAppWebhookResponse
from app.modules.bot.service import BotOrchestratorService
from app.modules.system.service import AuditService

router = APIRouter(prefix="/api/v1/bot", tags=["Bot & WhatsApp"])


@router.post("/webhook", response_model=WhatsAppWebhookResponse)
@router.post("/whatsapp/webhook", response_model=WhatsAppWebhookResponse)
async def handle_whatsapp_webhook(
    payload: WhatsAppWebhookPayload,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    try:
        result = await BotOrchestratorService.handle_whatsapp_command(db, ctx, payload)
        await db.commit()
        return result
    except RBACPermissionDeniedError as exc:
        await AuditService.log_change(
            session=db,
            ctx=ctx,
            entity_name="bot_security",
            entity_id=generate_uuid7(),
            action=f"RBAC_BLOCKED:{payload.requested_tool}",
            previous_value={"from_phone": payload.from_phone, "roles": ctx.roles},
            new_value={"message": payload.message_text, "error": str(exc)},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"RBAC Bloqueado: El rol '{','.join(ctx.roles)}' no cuenta con permiso '{payload.requested_tool}' para ejecutar esta acción.",
        )
