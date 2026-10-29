"""Esquemas Pydantic para el módulo sales."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class CustomerCreate(BaseModel):
    code: str
    name: str
    tax_id: str
    credit_limit: float = 0.0


class CustomerResponse(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None


class SalesOrderLineCreate(BaseModel):
    product_id: uuid.UUID
    qty: float
    unit_price: float


class SalesOrderLineResponse(SalesOrderLineCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sales_order_id: uuid.UUID


class SalesOrderCreate(BaseModel):
    customer_id: uuid.UUID
    warehouse_place_id: uuid.UUID
    lines: list[SalesOrderLineCreate]


class SalesOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    customer_id: uuid.UUID
    warehouse_place_id: uuid.UUID
    total_amount: float
    status: str
    created_at: datetime.datetime
    lines: list[SalesOrderLineResponse] = []
