"""Servicio público del módulo sales: Clientes, Órdenes y Validación de Crédito."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CreditLimitExceededError
from app.core.security import TenantContext
from app.core.uuid7 import generate_uuid7
from app.modules.inventory.service import InventoryService
from app.modules.mrp.schemas import ProductionOrderCreate
from app.modules.mrp.service import MRPService
from app.modules.sales.models import SalesCustomer, SalesOrder, SalesOrderLine
from app.modules.sales.schemas import CustomerCreate, SalesOrderCreate


class SalesService:
    """Contrato público de ventas, CRM y sincronización con manufactura."""

    @staticmethod
    async def create_customer(
        session: AsyncSession,
        ctx: TenantContext,
        data: CustomerCreate,
    ) -> SalesCustomer:
        customer = SalesCustomer(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            code=data.code,
            name=data.name,
            tax_id=data.tax_id,
            credit_limit=data.credit_limit,
        )
        session.add(customer)
        await session.flush()
        return customer

    @staticmethod
    async def get_customer(
        session: AsyncSession,
        ctx: TenantContext,
        customer_id: uuid.UUID,
    ) -> SalesCustomer | None:
        query = select(SalesCustomer).where(
            SalesCustomer.id == customer_id,
            SalesCustomer.tenant_id == ctx.tenant_id,
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def create_sales_order(
        session: AsyncSession,
        ctx: TenantContext,
        data: SalesOrderCreate,
    ) -> SalesOrder:
        total = sum(l.qty * l.unit_price for l in data.lines)
        so = SalesOrder(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            customer_id=data.customer_id,
            warehouse_place_id=data.warehouse_place_id,
            total_amount=total,
            status="DRAFT",
        )
        for line_data in data.lines:
            line = SalesOrderLine(
                id=generate_uuid7(),
                sales_order_id=so.id,
                product_id=line_data.product_id,
                qty=line_data.qty,
                unit_price=line_data.unit_price,
            )
            so.lines.append(line)

        session.add(so)
        await session.flush()
        return so

    @staticmethod
    async def get_sales_order(
        session: AsyncSession,
        ctx: TenantContext,
        so_id: uuid.UUID,
    ) -> SalesOrder | None:
        query = select(SalesOrder).where(
            SalesOrder.id == so_id,
            SalesOrder.tenant_id == ctx.tenant_id,
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def confirm_sales_order(
        session: AsyncSession,
        ctx: TenantContext,
        sales_order_id: uuid.UUID,
        default_work_center_id: uuid.UUID | None = None,
    ) -> dict:
        """Confirma la orden validando crédito y dispara automáticamente MRP si el stock es insuficiente."""
        so = await SalesService.get_sales_order(session, ctx, sales_order_id)
        if not so:
            raise ValueError(f"Sales order {sales_order_id} not found")

        customer = await SalesService.get_customer(session, ctx, so.customer_id)
        if not customer:
            raise ValueError(f"Customer {so.customer_id} not found")

        if so.total_amount > customer.credit_limit:
            raise CreditLimitExceededError(
                f"Sales order total ({so.total_amount:.2f} MXN) exceeds customer credit limit ({customer.credit_limit:.2f} MXN)"
            )

        so.status = "CONFIRMED"
        triggered_orders = []

        for line in so.lines:
            avail_stock = await InventoryService.get_stock_balance(
                session, ctx, line.product_id, so.warehouse_place_id
            )
            if avail_stock < line.qty:
                deficit = line.qty - avail_stock
                mrp_order = await MRPService.create_production_order(
                    session=session,
                    ctx=ctx,
                    data=ProductionOrderCreate(
                        product_id=line.product_id,
                        work_center_id=default_work_center_id,
                        qty_planned=deficit,
                        source_place_id=so.warehouse_place_id,
                        finished_dest_place_id=so.warehouse_place_id,
                        scrap_dest_place_id=so.warehouse_place_id,
                    ),
                )
                triggered_orders.append(
                    {
                        "id": mrp_order.id,
                        "product_id": line.product_id,
                        "qty_planned": deficit,
                    }
                )

        await session.flush()
        return {
            "status": "CONFIRMED",
            "sales_order_id": so.id,
            "triggered_production_orders": triggered_orders,
        }
