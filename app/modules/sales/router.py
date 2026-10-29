"""Rutas REST para el módulo sales."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import TenantContext, get_tenant_context
from app.modules.sales.models import SalesCustomer, SalesOrder
from app.modules.sales.schemas import (
    CustomerCreate,
    CustomerResponse,
    SalesOrderCreate,
    SalesOrderResponse,
)
from app.modules.sales.service import SalesService

router = APIRouter(prefix="/api/v1/sales", tags=["Sales & CRM"])


@router.post("/customers", response_model=CustomerResponse)
async def create_customer(
    data: CustomerCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    customer = await SalesService.create_customer(db, ctx, data)
    await db.commit()
    return customer


@router.get("/customers", response_model=list[CustomerResponse])
async def list_customers(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = select(SalesCustomer).where(SalesCustomer.tenant_id == ctx.tenant_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/orders", response_model=SalesOrderResponse)
async def create_order(
    data: SalesOrderCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    order = await SalesService.create_sales_order(db, ctx, data)
    await db.commit()
    return order


@router.post("/orders/{so_id}/confirm")
async def confirm_order(
    so_id: uuid.UUID,
    default_work_center_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    confirmation = await SalesService.confirm_sales_order(
        db, ctx, so_id, default_work_center_id=default_work_center_id
    )
    await db.commit()
    return confirmation


@router.get("/orders", response_model=list[SalesOrderResponse])
async def list_orders(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = (
        select(SalesOrder)
        .where(SalesOrder.tenant_id == ctx.tenant_id)
        .order_by(SalesOrder.created_at.desc())
        .limit(100)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
