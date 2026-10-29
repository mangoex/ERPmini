"""Servicio público del módulo bot: GrokBot Tool-Calling con verificación RBAC."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TenantContext
from app.core.uuid7 import generate_uuid7
from app.modules.bot.schemas import WhatsAppWebhookPayload
from app.modules.system.service import AuditService, OutboxService, RBACService


class BotOrchestratorService:
    """Orquestador de agentes y comandos vía WhatsApp protegido por RBAC."""

    @staticmethod
    async def handle_whatsapp_command(
        session: AsyncSession,
        ctx: TenantContext,
        payload: WhatsAppWebhookPayload,
    ) -> dict:
        # Validación de seguridad: el usuario debe tener el permiso de la herramienta solicitada
        RBACService.check_permission(ctx, payload.requested_tool)

        tool_id = generate_uuid7()
        await AuditService.log_change(
            session=session,
            ctx=ctx,
            entity_name="bot_command",
            entity_id=tool_id,
            action=f"TOOL_CALL:{payload.requested_tool}",
            previous_value={"from_phone": payload.from_phone, "roles": ctx.roles},
            new_value={"message": payload.message_text, "args": payload.tool_args},
        )
        await OutboxService.publish(
            session=session,
            ctx=ctx,
            event_type="bot.tool_executed",
            aggregate_type="bot_command",
            aggregate_id=tool_id,
            payload={"tool": payload.requested_tool, "from_phone": payload.from_phone},
        )

        return {
            "status": "EXECUTED",
            "tool": payload.requested_tool,
            "result": "OK",
            "phone": payload.from_phone,
            "message": payload.message_text,
        }
