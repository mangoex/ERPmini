"""Rutas REST para el módulo mrp."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import TenantContext, get_tenant_context
from app.modules.mrp.models import (
    MRPProductionOrder,
)
from app.modules.mrp.schemas import (
    BOMStructureCreate,
    BOMStructureResponse,
    ProductionOrderCreate,
    ProductionOrderResponse,
    UnbuildOrderCreate,
    UnbuildOrderResponse,
    WorkCenterCreate,
    WorkCenterResponse,
)
from app.modules.mrp.service import MRPService

router = APIRouter(prefix="/api/v1/mrp", tags=["MRP & Manufacturing"])


@router.post("/work-centers", response_model=WorkCenterResponse)
async def create_work_center(
    data: WorkCenterCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    wc = await MRPService.create_work_center(db, ctx, data)
    await db.commit()
    return wc


@router.get("/work-centers", response_model=list[WorkCenterResponse])
async def list_work_centers(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    wcs = await MRPService.list_work_centers(db, ctx)
    return wcs


@router.post("/bom-lines", response_model=BOMStructureResponse)
async def create_bom_line(
    data: BOMStructureCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    bom = await MRPService.create_bom_line(db, ctx, data)
    await db.commit()
    return bom


@router.get("/bom/explode/{product_id}")
async def explode_bom(
    product_id: uuid.UUID,
    qty: float = 1.0,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    return await MRPService.explode_bom_recursive(db, ctx, product_id, qty)


@router.post("/production-orders", response_model=ProductionOrderResponse)
async def create_production_order(
    data: ProductionOrderCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    mo = await MRPService.create_and_complete_production_order(db, ctx, data)
    await db.commit()
    return mo


@router.get("/production-orders", response_model=list[ProductionOrderResponse])
async def list_production_orders(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = (
        select(MRPProductionOrder)
        .where(MRPProductionOrder.tenant_id == ctx.tenant_id)
        .order_by(MRPProductionOrder.created_at.desc())
        .limit(100)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/unbuild-orders", response_model=UnbuildOrderResponse)
async def execute_unbuild(
    data: UnbuildOrderCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    unbuild = await MRPService.execute_regrind_unbuild(db, ctx, data)
    await db.commit()
    return unbuild
