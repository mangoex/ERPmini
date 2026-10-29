"""Servicio público del módulo inventory."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InsufficientStockError
from app.core.security import TenantContext
from app.core.uuid7 import generate_uuid7
from app.modules.inventory.models import (
    InventoryProduct,
    InventoryStockLot,
    InventoryStockMove,
    InventoryStockPlace,
)
from app.modules.inventory.schemas import (
    ProductCreate,
    StockMoveCreate,
    StockPlaceCreate,
)


class InventoryService:
    """Contrato público y lógica de negocio de WMS / Inventarios."""

    @staticmethod
    async def create_place(
        session: AsyncSession,
        ctx: TenantContext,
        data: StockPlaceCreate,
    ) -> InventoryStockPlace:
        place = InventoryStockPlace(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            code=data.code,
            name=data.name,
            place_type=data.place_type,
        )
        session.add(place)
        await session.flush()
        return place

    @staticmethod
    async def get_place(
        session: AsyncSession,
        ctx: TenantContext,
        place_id: uuid.UUID,
    ) -> InventoryStockPlace | None:
        query = select(InventoryStockPlace).where(
            InventoryStockPlace.id == place_id,
            InventoryStockPlace.tenant_id == ctx.tenant_id,
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def create_product(
        session: AsyncSession,
        ctx: TenantContext,
        data: ProductCreate,
    ) -> InventoryProduct:
        product = InventoryProduct(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            sku=data.sku,
            name=data.name,
            category=data.category,
            uom=data.uom,
            weight_kg=data.weight_kg,
            min_stock=data.min_stock,
            standard_cost=data.standard_cost,
        )
        session.add(product)
        await session.flush()
        return product

    @staticmethod
    async def get_product(
        session: AsyncSession,
        ctx: TenantContext,
        product_id: uuid.UUID,
    ) -> InventoryProduct | None:
        query = select(InventoryProduct).where(
            InventoryProduct.id == product_id,
            InventoryProduct.tenant_id == ctx.tenant_id,
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_product_by_sku(
        session: AsyncSession,
        ctx: TenantContext,
        sku: str,
    ) -> InventoryProduct | None:
        query = select(InventoryProduct).where(
            InventoryProduct.sku == sku,
            InventoryProduct.tenant_id == ctx.tenant_id,
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_stock_balance(
        session: AsyncSession,
        ctx: TenantContext,
        product_id: uuid.UUID,
        place_id: uuid.UUID,
    ) -> float:
        """Calcula el saldo exacto de stock inmutable por doble entrada: Sum(Inbound) - Sum(Outbound)."""
        inbound_stmt = select(
            func.coalesce(func.sum(InventoryStockMove.qty), 0.0)
        ).where(
            InventoryStockMove.tenant_id == ctx.tenant_id,
            InventoryStockMove.product_id == product_id,
            InventoryStockMove.dest_place_id == place_id,
            InventoryStockMove.status == "DONE",
        )
        outbound_stmt = select(
            func.coalesce(func.sum(InventoryStockMove.qty), 0.0)
        ).where(
            InventoryStockMove.tenant_id == ctx.tenant_id,
            InventoryStockMove.product_id == product_id,
            InventoryStockMove.source_place_id == place_id,
            InventoryStockMove.status == "DONE",
        )
        inbound = (await session.execute(inbound_stmt)).scalar_one()
        outbound = (await session.execute(outbound_stmt)).scalar_one()
        return float(inbound - outbound)

    @staticmethod
    async def create_stock_move(
        session: AsyncSession,
        ctx: TenantContext,
        data: StockMoveCreate,
    ) -> InventoryStockMove:
        """Crea un movimiento de inventario inmutable, previniendo saldos negativos en ubicaciones no-proveedor."""
        source_place = await session.get(InventoryStockPlace, data.source_place_id)
        if source_place and source_place.place_type == "INTERNAL":
            current_balance = await InventoryService.get_stock_balance(
                session, ctx, data.product_id, data.source_place_id
            )
            if current_balance < data.qty:
                raise InsufficientStockError(
                    f"Insufficient stock for product {data.product_id} at location '{source_place.name}': "
                    f"available {current_balance}, requested {data.qty}"
                )

        lot_id = None
        if data.lot_code:
            lot_query = select(InventoryStockLot).where(
                InventoryStockLot.tenant_id == ctx.tenant_id,
                InventoryStockLot.product_id == data.product_id,
                InventoryStockLot.lot_code == data.lot_code,
            )
            lot_res = await session.execute(lot_query)
            existing_lot = lot_res.scalars().first()
            if existing_lot:
                lot_id = existing_lot.id
            else:
                new_lot = InventoryStockLot(
                    id=generate_uuid7(),
                    tenant_id=ctx.tenant_id,
                    branch_id=ctx.branch_id,
                    lot_code=data.lot_code,
                    product_id=data.product_id,
                )
                session.add(new_lot)
                await session.flush()
                lot_id = new_lot.id

        move = InventoryStockMove(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            product_id=data.product_id,
            source_place_id=data.source_place_id,
            dest_place_id=data.dest_place_id,
            lot_id=lot_id,
            qty=data.qty,
            uom=data.uom,
            unit_cost=data.unit_cost,
            reference=data.reference,
            status="DONE",
        )
        session.add(move)
        await session.flush()
        return move
