"""Esquemas Pydantic para el módulo mrp."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class WorkCenterCreate(BaseModel):
    code: str
    name: str
    center_type: str  # INJECTION_MOLDER, BLOW_MOLDER, GRANULATOR_MILL
    mold_code: str | None = None
    cavities: int = 1
    cycle_time_seconds: int = 0


class WorkCenterResponse(WorkCenterCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None


class BOMStructureCreate(BaseModel):
    parent_product_id: uuid.UUID
    child_product_id: uuid.UUID
    qty_ratio: float
    scrap_return_ratio: float = 0.0
    scrap_product_id: uuid.UUID | None = None


class BOMStructureResponse(BOMStructureCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None


class ProductionOrderCreate(BaseModel):
    product_id: uuid.UUID
    work_center_id: uuid.UUID | None = None
    qty_planned: float
    source_place_id: uuid.UUID
    finished_dest_place_id: uuid.UUID
    scrap_dest_place_id: uuid.UUID


class ProductionOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    product_id: uuid.UUID
    work_center_id: uuid.UUID | None = None
    qty_planned: float
    qty_produced: float
    scrap_generated_kg: float
    source_place_id: uuid.UUID
    finished_dest_place_id: uuid.UUID
    scrap_dest_place_id: uuid.UUID
    status: str
    created_at: datetime.datetime


class UnbuildOrderCreate(BaseModel):
    work_center_id: uuid.UUID
    scrap_product_id: uuid.UUID
    regrind_product_id: uuid.UUID
    source_scrap_place_id: uuid.UUID
    dest_regrind_place_id: uuid.UUID
    input_qty_kg: float
    output_regrind_qty_kg: float
    process_loss_kg: float


class UnbuildOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    work_center_id: uuid.UUID
    scrap_product_id: uuid.UUID
    regrind_product_id: uuid.UUID
    source_scrap_place_id: uuid.UUID
    dest_regrind_place_id: uuid.UUID
    input_qty_kg: float
    output_regrind_qty_kg: float
    process_loss_kg: float
    status: str
    created_at: datetime.datetime
