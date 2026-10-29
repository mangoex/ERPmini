"""Servicio público del módulo mrp: Centros de Trabajo, BOM, Producción y Molienda."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainValidationError
from app.core.security import TenantContext
from app.core.uuid7 import generate_uuid7
from app.modules.inventory.schemas import StockMoveCreate
from app.modules.inventory.service import InventoryService
from app.modules.mrp.models import (
    MRPBOMStructure,
    MRPProductionOrder,
    MRPUnbuildOrder,
    MRPWorkCenter,
)
from app.modules.mrp.schemas import (
    BOMStructureCreate,
    ProductionOrderCreate,
    UnbuildOrderCreate,
    WorkCenterCreate,
)


class MRPService:
    """Contrato público de manufactura y reciclaje en planta."""

    @staticmethod
    async def create_work_center(
        session: AsyncSession,
        ctx: TenantContext,
        data: WorkCenterCreate,
    ) -> MRPWorkCenter:
        wc = MRPWorkCenter(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            code=data.code,
            name=data.name,
            center_type=data.center_type,
            mold_code=data.mold_code,
            cavities=data.cavities,
            cycle_time_seconds=data.cycle_time_seconds,
        )
        session.add(wc)
        await session.flush()
        return wc

    @staticmethod
    async def get_work_center(
        session: AsyncSession,
        ctx: TenantContext,
        wc_id: uuid.UUID,
    ) -> MRPWorkCenter | None:
        query = select(MRPWorkCenter).where(
            MRPWorkCenter.id == wc_id,
            MRPWorkCenter.tenant_id == ctx.tenant_id,
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def list_work_centers(
        session: AsyncSession,
        ctx: TenantContext,
    ) -> list[MRPWorkCenter]:
        query = select(MRPWorkCenter).where(MRPWorkCenter.tenant_id == ctx.tenant_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_bom_line(
        session: AsyncSession,
        ctx: TenantContext,
        data: BOMStructureCreate,
    ) -> MRPBOMStructure:
        bom = MRPBOMStructure(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            parent_product_id=data.parent_product_id,
            child_product_id=data.child_product_id,
            qty_ratio=data.qty_ratio,
            scrap_return_ratio=data.scrap_return_ratio,
            scrap_product_id=data.scrap_product_id,
        )
        session.add(bom)
        await session.flush()
        return bom

    @staticmethod
    async def explode_bom_recursive(
        session: AsyncSession,
        ctx: TenantContext,
        parent_product_id: uuid.UUID,
        target_qty: float,
    ) -> list[dict]:
        """Explosión recursiva de BOM calculando cantidades requeridas y rebaba esperada."""
        results = []

        query = select(MRPBOMStructure).where(
            MRPBOMStructure.tenant_id == ctx.tenant_id,
            MRPBOMStructure.parent_product_id == parent_product_id,
        )
        result = await session.execute(query)
        bom_lines = list(result.scalars().all())

        for line in bom_lines:
            req_qty = line.qty_ratio * target_qty
            expected_scrap = req_qty * line.scrap_return_ratio
            product = await InventoryService.get_product(
                session, ctx, line.child_product_id
            )
            sku = product.sku if product else str(line.child_product_id)

            # Check if this child has sub-BOM lines (recursive check)
            sub_query = select(MRPBOMStructure).where(
                MRPBOMStructure.tenant_id == ctx.tenant_id,
                MRPBOMStructure.parent_product_id == line.child_product_id,
            )
            sub_res = await session.execute(sub_query)
            sub_lines = list(sub_res.scalars().all())

            if sub_lines:
                sub_results = await MRPService.explode_bom_recursive(
                    session, ctx, line.child_product_id, req_qty
                )
                results.extend(sub_results)
            else:
                results.append(
                    {
                        "child_product_id": line.child_product_id,
                        "sku": sku,
                        "required_qty": req_qty,
                        "expected_scrap_qty": expected_scrap,
                        "scrap_product_id": line.scrap_product_id,
                    }
                )

        return results

    @staticmethod
    async def create_production_order(
        session: AsyncSession,
        ctx: TenantContext,
        data: ProductionOrderCreate,
    ) -> MRPProductionOrder:
        """Crea una orden de producción sin completar inmediatamente (ej. disparada por déficit de stock)."""
        mo = MRPProductionOrder(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            product_id=data.product_id,
            work_center_id=data.work_center_id,
            qty_planned=data.qty_planned,
            qty_produced=0.0,
            scrap_generated_kg=0.0,
            source_place_id=data.source_place_id,
            finished_dest_place_id=data.finished_dest_place_id,
            scrap_dest_place_id=data.scrap_dest_place_id,
            status="CONFIRMED",
        )
        session.add(mo)
        await session.flush()
        return mo

    @staticmethod
    async def create_and_complete_production_order(
        session: AsyncSession,
        ctx: TenantContext,
        data: ProductionOrderCreate,
    ) -> MRPProductionOrder:
        """Ejecuta una orden de producción completa: consume componentes, produce producto terminado y rebaba."""
        explosion = await MRPService.explode_bom_recursive(
            session, ctx, data.product_id, data.qty_planned
        )

        total_scrap = 0.0

        # Consumo de materias primas desde source_place_id hacia finished_dest_place_id
        for comp in explosion:
            await InventoryService.create_stock_move(
                session=session,
                ctx=ctx,
                data=StockMoveCreate(
                    product_id=comp["child_product_id"],
                    source_place_id=data.source_place_id,
                    dest_place_id=data.finished_dest_place_id,
                    qty=comp["required_qty"],
                    uom="KG",
                    unit_cost=0.0,
                    reference=f"MO-CONSUMO-{data.product_id}",
                ),
            )
            if comp.get("scrap_product_id") and comp["expected_scrap_qty"] > 0:
                total_scrap += comp["expected_scrap_qty"]
                await InventoryService.create_stock_move(
                    session=session,
                    ctx=ctx,
                    data=StockMoveCreate(
                        product_id=comp["scrap_product_id"],
                        source_place_id=data.source_place_id,
                        dest_place_id=data.scrap_dest_place_id,
                        qty=comp["expected_scrap_qty"],
                        uom="KG",
                        unit_cost=0.0,
                        reference=f"MO-REBABA-{data.product_id}",
                    ),
                )

        # Entrada del producto terminado
        crate_prod = await InventoryService.get_product(session, ctx, data.product_id)
        uom = crate_prod.uom if crate_prod else "PCS"
        await InventoryService.create_stock_move(
            session=session,
            ctx=ctx,
            data=StockMoveCreate(
                product_id=data.product_id,
                source_place_id=data.source_place_id,
                dest_place_id=data.finished_dest_place_id,
                qty=data.qty_planned,
                uom=uom,
                unit_cost=0.0,
                reference=f"MO-PRODUCTO-TERMINADO-{data.product_id}",
            ),
        )

        mo = MRPProductionOrder(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            product_id=data.product_id,
            work_center_id=data.work_center_id,
            qty_planned=data.qty_planned,
            qty_produced=data.qty_planned,
            scrap_generated_kg=total_scrap,
            source_place_id=data.source_place_id,
            finished_dest_place_id=data.finished_dest_place_id,
            scrap_dest_place_id=data.scrap_dest_place_id,
            status="DONE",
        )
        session.add(mo)
        await session.flush()
        return mo

    @staticmethod
    async def execute_regrind_unbuild(
        session: AsyncSession,
        ctx: TenantContext,
        data: UnbuildOrderCreate,
    ) -> MRPUnbuildOrder:
        """Molienda y recuperación de rebaba validando balance estricto de masa (Entrada = Salida + Pérdida)."""
        mass_diff = abs(
            (data.output_regrind_qty_kg + data.process_loss_kg) - data.input_qty_kg
        )
        if mass_diff > 1e-4:
            raise DomainValidationError(
                f"Mass balance violation in granulator: input ({data.input_qty_kg} kg) "
                f"does not match output ({data.output_regrind_qty_kg} kg) + process loss ({data.process_loss_kg} kg)"
            )

        # Consumo de rebaba en tolva del molino
        await InventoryService.create_stock_move(
            session=session,
            ctx=ctx,
            data=StockMoveCreate(
                product_id=data.scrap_product_id,
                source_place_id=data.source_scrap_place_id,
                dest_place_id=data.dest_regrind_place_id,
                qty=data.input_qty_kg,
                uom="KG",
                unit_cost=0.0,
                reference="MOLINO-CONSUMO-REBABA",
            ),
        )

        # Generación de regrind recuperado hacia piso de planta
        await InventoryService.create_stock_move(
            session=session,
            ctx=ctx,
            data=StockMoveCreate(
                product_id=data.regrind_product_id,
                source_place_id=data.source_scrap_place_id,
                dest_place_id=data.dest_regrind_place_id,
                qty=data.output_regrind_qty_kg,
                uom="KG",
                unit_cost=0.0,
                reference="MOLINO-PRODUCCION-REGRIND",
            ),
        )

        unbuild = MRPUnbuildOrder(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            work_center_id=data.work_center_id,
            scrap_product_id=data.scrap_product_id,
            regrind_product_id=data.regrind_product_id,
            source_scrap_place_id=data.source_scrap_place_id,
            dest_regrind_place_id=data.dest_regrind_place_id,
            input_qty_kg=data.input_qty_kg,
            output_regrind_qty_kg=data.output_regrind_qty_kg,
            process_loss_kg=data.process_loss_kg,
            status="DONE",
        )
        session.add(unbuild)
        await session.flush()
        return unbuild
