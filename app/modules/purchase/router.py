"""Rutas REST para el módulo purchase."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import TenantContext, get_tenant_context
from app.modules.purchase.models import (
    PurchaseGoodsReceiptNote,
    PurchaseSupplier,
)
from app.modules.purchase.schemas import (
    GoodsReceiptCreate,
    GoodsReceiptResponse,
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    SupplierCreate,
    SupplierResponse,
)
from app.modules.purchase.service import PurchaseService

router = APIRouter(prefix="/api/v1/purchase", tags=["Purchase & Scale"])


@router.post("/suppliers", response_model=SupplierResponse)
async def create_supplier(
    data: SupplierCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    supplier = await PurchaseService.create_supplier(db, ctx, data)
    await db.commit()
    return supplier


@router.get("/suppliers", response_model=list[SupplierResponse])
async def list_suppliers(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = select(PurchaseSupplier).where(PurchaseSupplier.tenant_id == ctx.tenant_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/orders", response_model=PurchaseOrderResponse)
async def create_order(
    data: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    po = await PurchaseService.create_purchase_order(db, ctx, data)
    await db.commit()
    return po


@router.post("/orders/{po_id}/approve", response_model=PurchaseOrderResponse)
async def approve_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    po = await PurchaseService.approve_purchase_order(db, ctx, po_id)
    await db.commit()
    return po


@router.post("/scale-receipts", response_model=GoodsReceiptResponse)
async def receive_at_scale(
    data: GoodsReceiptCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    grn = await PurchaseService.receive_goods_at_scale(db, ctx, data)
    await db.commit()
    return grn


@router.get("/scale-receipts", response_model=list[GoodsReceiptResponse])
async def list_receipts(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = (
        select(PurchaseGoodsReceiptNote)
        .where(PurchaseGoodsReceiptNote.tenant_id == ctx.tenant_id)
        .order_by(PurchaseGoodsReceiptNote.created_at.desc())
        .limit(100)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
