"""Esquemas Pydantic para el módulo system."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    entity_name: str
    entity_id: uuid.UUID
    action: str
    previous_value: dict | None = None
    new_value: dict | None = None
    created_at: datetime.datetime


class OutboxResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    event_type: str
    aggregate_type: str
    aggregate_id: uuid.UUID
    payload: dict
    status: str
    created_at: datetime.datetime
    processed_at: datetime.datetime | None = None
