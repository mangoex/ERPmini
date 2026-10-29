"""Servicio público del módulo purchase: Proveedores, POs y Báscula."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TenantContext
from app.core.uuid7 import generate_uuid7
from app.modules.inventory.schemas import StockMoveCreate
from app.modules.inventory.service import InventoryService
from app.modules.purchase.models import (
    PurchaseGoodsReceiptLine,
    PurchaseGoodsReceiptNote,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseSupplier,
)
from app.modules.purchase.schemas import (
    GoodsReceiptCreate,
    PurchaseOrderCreate,
    SupplierCreate,
)


class PurchaseService:
    """Contrato público de compras y pesaje industrial."""

    @staticmethod
    async def create_supplier(
        session: AsyncSession,
        ctx: TenantContext,
        data: SupplierCreate,
    ) -> PurchaseSupplier:
        supplier = PurchaseSupplier(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            code=data.code,
            name=data.name,
            tax_id=data.tax_id,
        )
        session.add(supplier)
        await session.flush()
        return supplier

    @staticmethod
    async def create_purchase_order(
        session: AsyncSession,
        ctx: TenantContext,
        data: PurchaseOrderCreate,
    ) -> PurchaseOrder:
        po = PurchaseOrder(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            supplier_id=data.supplier_id,
            status="DRAFT",
        )
        for line_data in data.lines:
            line = PurchaseOrderLine(
                id=generate_uuid7(),
                purchase_order_id=po.id,
                product_id=line_data.product_id,
                qty_ordered=line_data.qty_ordered,
                unit_price=line_data.unit_price,
            )
            po.lines.append(line)

        session.add(po)
        await session.flush()
        return po

    @staticmethod
    async def approve_purchase_order(
        session: AsyncSession,
        ctx: TenantContext,
        po_id: uuid.UUID,
    ) -> PurchaseOrder:
        po = await PurchaseService.get_purchase_order(session, ctx, po_id)
        if not po:
            raise ValueError(f"Purchase order {po_id} not found")
        po.status = "APPROVED"
        await session.flush()
        return po

    @staticmethod
    async def get_purchase_order(
        session: AsyncSession,
        ctx: TenantContext,
        po_id: uuid.UUID,
    ) -> PurchaseOrder | None:
        query = select(PurchaseOrder).where(
            PurchaseOrder.id == po_id,
            PurchaseOrder.tenant_id == ctx.tenant_id,
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_goods_receipt(
        session: AsyncSession,
        ctx: TenantContext,
        grn_id: uuid.UUID,
    ) -> PurchaseGoodsReceiptNote | None:
        query = select(PurchaseGoodsReceiptNote).where(
            PurchaseGoodsReceiptNote.id == grn_id,
            PurchaseGoodsReceiptNote.tenant_id == ctx.tenant_id,
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def receive_goods_at_scale(
        session: AsyncSession,
        ctx: TenantContext,
        data: GoodsReceiptCreate,
    ) -> PurchaseGoodsReceiptNote:
        """Registra la recepción en báscula (Bruto - Tara = Neto) e ingresa el stock por doble entrada."""
        net_weight = data.gross_weight_kg - data.tare_weight_kg
        grn = PurchaseGoodsReceiptNote(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            purchase_order_id=data.purchase_order_id,
            scale_ticket_number=data.scale_ticket_number,
            gross_weight_kg=data.gross_weight_kg,
            tare_weight_kg=data.tare_weight_kg,
            net_weight_kg=net_weight,
            source_place_id=data.source_place_id,
            dest_place_id=data.dest_place_id,
            lot_code=data.lot_code,
            status="DONE",
        )

        po = await PurchaseService.get_purchase_order(
            session, ctx, data.purchase_order_id
        )
        po_lines_map = {line.id: line for line in (po.lines if po else [])}

        for line_data in data.lines:
            grn_line = PurchaseGoodsReceiptLine(
                id=generate_uuid7(),
                grn_id=grn.id,
                po_line_id=line_data.po_line_id,
                product_id=line_data.product_id,
                qty_received_kg=line_data.qty_received_kg,
            )
            grn.lines.append(grn_line)

            unit_cost = 0.0
            if line_data.po_line_id in po_lines_map:
                unit_cost = po_lines_map[line_data.po_line_id].unit_price

            # Movimiento de inventario comunicándose a través de InventoryService
            await InventoryService.create_stock_move(
                session=session,
                ctx=ctx,
                data=StockMoveCreate(
                    product_id=line_data.product_id,
                    source_place_id=data.source_place_id,
                    dest_place_id=data.dest_place_id,
                    qty=line_data.qty_received_kg,
                    uom="KG",
                    unit_cost=unit_cost,
                    reference=f"GRN-{data.scale_ticket_number}",
                    lot_code=data.lot_code,
                ),
            )

        session.add(grn)
        await session.flush()
        return grn
