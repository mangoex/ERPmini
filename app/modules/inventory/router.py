"""Rutas REST para el módulo inventory."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import TenantContext, get_tenant_context
from app.modules.inventory.models import (
    InventoryProduct,
    InventoryStockMove,
    InventoryStockPlace,
)
from app.modules.inventory.schemas import (
    ProductCreate,
    ProductResponse,
    StockMoveCreate,
    StockMoveResponse,
    StockPlaceCreate,
    StockPlaceResponse,
)
from app.modules.inventory.service import InventoryService

router = APIRouter(prefix="/api/v1/inventory", tags=["Inventory & WMS"])


@router.post("/places", response_model=StockPlaceResponse)
async def create_place(
    data: StockPlaceCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    place = await InventoryService.create_place(db, ctx, data)
    await db.commit()
    return place


@router.get("/places", response_model=list[StockPlaceResponse])
async def list_places(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = select(InventoryStockPlace).where(
        InventoryStockPlace.tenant_id == ctx.tenant_id
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/products", response_model=ProductResponse)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    product = await InventoryService.create_product(db, ctx, data)
    await db.commit()
    return product


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = select(InventoryProduct).where(InventoryProduct.tenant_id == ctx.tenant_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/stock-balance/{product_id}/{place_id}")
async def get_balance(
    product_id: uuid.UUID,
    place_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    balance = await InventoryService.get_stock_balance(db, ctx, product_id, place_id)
    return {"product_id": product_id, "place_id": place_id, "balance": balance}


@router.post("/moves", response_model=StockMoveResponse)
async def create_move(
    data: StockMoveCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    move = await InventoryService.create_stock_move(db, ctx, data)
    await db.commit()
    return move


@router.get("/moves", response_model=list[StockMoveResponse])
async def list_moves(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = (
        select(InventoryStockMove)
        .where(InventoryStockMove.tenant_id == ctx.tenant_id)
        .order_by(InventoryStockMove.created_at.desc())
        .limit(100)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
