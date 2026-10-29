"""Esquemas Pydantic para el módulo bot."""

from pydantic import BaseModel, Field


class WhatsAppWebhookPayload(BaseModel):
    from_phone: str
    message_text: str
    requested_tool: str
    tool_args: dict = Field(default_factory=dict)


class WhatsAppWebhookResponse(BaseModel):
    status: str
    tool: str
    result: str
    phone: str | None = None
    message: str | None = None
