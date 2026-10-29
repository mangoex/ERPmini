"""Esquemas Pydantic para el módulo purchase."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class SupplierCreate(BaseModel):
    code: str
    name: str
    tax_id: str


class SupplierResponse(SupplierCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None


class PurchaseOrderLineCreate(BaseModel):
    product_id: uuid.UUID
    qty_ordered: float
    unit_price: float


class PurchaseOrderLineResponse(PurchaseOrderLineCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_order_id: uuid.UUID


class PurchaseOrderCreate(BaseModel):
    supplier_id: uuid.UUID
    lines: list[PurchaseOrderLineCreate]


class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    supplier_id: uuid.UUID
    status: str
    created_at: datetime.datetime
    lines: list[PurchaseOrderLineResponse] = []


class GoodsReceiptLineCreate(BaseModel):
    po_line_id: uuid.UUID
    product_id: uuid.UUID
    qty_received_kg: float


class GoodsReceiptLineResponse(GoodsReceiptLineCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    grn_id: uuid.UUID


class GoodsReceiptCreate(BaseModel):
    purchase_order_id: uuid.UUID
    scale_ticket_number: str
    gross_weight_kg: float
    tare_weight_kg: float
    source_place_id: uuid.UUID
    dest_place_id: uuid.UUID
    lot_code: str
    lines: list[GoodsReceiptLineCreate]


class GoodsReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    purchase_order_id: uuid.UUID
    scale_ticket_number: str
    gross_weight_kg: float
    tare_weight_kg: float
    net_weight_kg: float
    source_place_id: uuid.UUID
    dest_place_id: uuid.UUID
    lot_code: str | None = None
    status: str
    created_at: datetime.datetime
    lines: list[GoodsReceiptLineResponse] = []
