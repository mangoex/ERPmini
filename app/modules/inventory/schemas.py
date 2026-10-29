"""Esquemas Pydantic para el módulo inventory."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class StockPlaceCreate(BaseModel):
    code: str
    name: str
    place_type: str  # INTERNAL, VENDOR, CUSTOMER, SCRAP, PRODUCTION


class StockPlaceResponse(StockPlaceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None


class ProductCreate(BaseModel):
    sku: str
    name: str
    category: str  # RAW_RESIN, REGRIND, MASTERBATCH_UV, FINISHED_CRATE, SCRAP_FLASH
    uom: str  # KG, PCS
    weight_kg: float = 0.0
    min_stock: float = 0.0
    standard_cost: float = 0.0


class ProductResponse(ProductCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None


class StockMoveCreate(BaseModel):
    product_id: uuid.UUID
    source_place_id: uuid.UUID
    dest_place_id: uuid.UUID
    qty: float
    uom: str
    unit_cost: float = 0.0
    reference: str | None = None
    lot_code: str | None = None


class StockMoveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    product_id: uuid.UUID
    source_place_id: uuid.UUID
    dest_place_id: uuid.UUID
    lot_id: uuid.UUID | None = None
    qty: float
    uom: str
    unit_cost: float
    reference: str | None = None
    status: str
    created_at: datetime.datetime
