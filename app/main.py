"""FastAPI App Factory y Entrypoint de ERPmini."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import Base, engine, get_db_session
from app.core.security import TenantContext, get_tenant_context
from app.core.uuid7 import generate_uuid7
from app.modules.account.router import router as account_router
from app.modules.bot.router import router as bot_router
from app.modules.hr.router import router as hr_router
from app.modules.inventory.models import InventoryStockPlace
from app.modules.inventory.router import router as inventory_router
from app.modules.inventory.schemas import StockMoveCreate
from app.modules.inventory.service import InventoryService
from app.modules.mrp.models import MRPBOMStructure, MRPWorkCenter
from app.modules.mrp.router import router as mrp_router
from app.modules.mrp.schemas import (
    BOMStructureCreate,
    ProductionOrderCreate,
    UnbuildOrderCreate,
)
from app.modules.mrp.service import MRPService
from app.modules.purchase.models import PurchaseSupplier
from app.modules.purchase.router import router as purchase_router
from app.modules.purchase.schemas import (
    GoodsReceiptCreate,
    GoodsReceiptLineCreate,
    PurchaseOrderCreate,
    PurchaseOrderLineCreate,
)
from app.modules.purchase.service import PurchaseService
from app.modules.sales.router import router as sales_router
from app.modules.system.models import SystemAuditLog, SystemTransactionalOutbox
from app.modules.system.router import router as system_router
from app.modules.system.service import AuditService, OutboxService
from app.seed import seed_demo_data

# --- Esquemas de Demostración Operativa ---


class QuickGRNRequest(BaseModel):
    ticket_number: str = Field(default="TKT-BASC-8821")
    product_sku: str = Field(default="HDPE-SOPLADO-5502")
    gross_weight_kg: float = Field(default=38500.0)
    tare_weight_kg: float = Field(default=14500.0)
    silo_code: str = Field(default="LOC-SILO-01")


class QuickProductionRequest(BaseModel):
    work_center_code: str = Field(default="ENGEL-DUO-450")
    product_sku: str = Field(default="CAJA-AGRO-20KG")
    qty_planned: float = Field(default=100.0)


class QuickRegrindRequest(BaseModel):
    work_center_code: str = Field(default="PAGANI-GR-50")
    input_qty_kg: float = Field(default=14.0)
    loss_percent: float = Field(default=3.5)


async def _ensure_tenant_is_seeded(db: AsyncSession, ctx: TenantContext) -> None:
    """Verifica si el tenant cuenta con datos maestros; si no, ejecuta seed_demo_data de forma idempotente."""
    existing_prod = await InventoryService.get_product_by_sku(
        db, ctx, "HDPE-SOPLADO-5502"
    )
    if not existing_prod:
        await seed_demo_data(db, ctx)


def create_app() -> FastAPI:
    """Crea y configura la aplicación FastAPI con el monolito modular completo."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if "sqlite" in settings.DATABASE_URL:
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            except Exception:
                pass
        yield

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Sistema ERP Modular Enterprise para Planta de Soplado e Inyección de Plástico.",
        lifespan=lifespan,
    )

    # Registro de routers de los 8 módulos del monolito
    app.include_router(system_router)
    app.include_router(inventory_router)
    app.include_router(purchase_router)
    app.include_router(mrp_router)
    app.include_router(sales_router)
    app.include_router(account_router)
    app.include_router(hr_router)
    app.include_router(bot_router)

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "app": "ERPmini", "version": settings.VERSION}

    @app.get("/", response_class=HTMLResponse)
    async def industrial_dashboard():
        template_file = Path(__file__).resolve().parent / "templates" / "dashboard.html"
        if template_file.exists():
            return template_file.read_text(encoding="utf-8")
        return """
        <!DOCTYPE html>
        <html lang="es">
        <head><title>ERPmini — Dashboard Industrial</title></head>
        <body><h1>ERPmini — Planta Industrial de Soplado e Inyección</h1></body>
        </html>
        """

    @app.get("/api/v1/summary")
    async def system_summary():
        return {
            "app": "ERPmini",
            "version": settings.VERSION,
            "status": "operational",
            "architecture": "Strict Modular Monolith",
            "plant": "Soplado e Inyección de Plástico para Cajas Agrícolas",
            "modules": [
                "system",
                "inventory",
                "purchase",
                "mrp",
                "sales",
                "account",
                "hr",
                "bot",
            ],
        }

    @app.post("/api/v1/seed")
    async def seed_data(
        db: AsyncSession = Depends(get_db_session),
        ctx: TenantContext = Depends(get_tenant_context),
    ):
        result = await seed_demo_data(db, ctx)
        return result

    # --- Endpoints de Demostración Operativa en Tiempo Real ---

    @app.get("/api/v1/demo/dashboard-state")
    async def demo_dashboard_state(
        db: AsyncSession = Depends(get_db_session),
        ctx: TenantContext = Depends(get_tenant_context),
    ):
        """Retorna el estado de stock en silos, tolvas, molino, cajas y auditoría para el tenant."""
        prod_soplado = await InventoryService.get_product_by_sku(
            db, ctx, "HDPE-SOPLADO-5502"
        )
        prod_inj = await InventoryService.get_product_by_sku(db, ctx, "HDPE-INJ-6070")
        prod_regrind = await InventoryService.get_product_by_sku(
            db, ctx, "HDPE-MOLIDO-REC"
        )
        prod_mb = await InventoryService.get_product_by_sku(db, ctx, "MB-VERDE-UV")
        prod_scrap = await InventoryService.get_product_by_sku(
            db, ctx, "SCRAP-REBABA-HDPE"
        )
        prod_caja20 = await InventoryService.get_product_by_sku(
            db, ctx, "CAJA-AGRO-20KG"
        )
        prod_caja15 = await InventoryService.get_product_by_sku(
            db, ctx, "CAJA-EXPORT-15KG"
        )

        if not prod_soplado:
            return {
                "tenant_id": str(ctx.tenant_id),
                "is_seeded": False,
                "kpis": {
                    "resin_virgin_total_kg": 0.0,
                    "resin_soplado_silo1_kg": 0.0,
                    "resin_inyeccion_silo2_kg": 0.0,
                    "regrind_hopper_kg": 0.0,
                    "masterbatch_uv_kg": 0.0,
                    "scrap_mill_hopper_kg": 0.0,
                    "finished_crates_total_pcs": 0.0,
                    "crates_20kg_pcs": 0.0,
                    "crates_15kg_pcs": 0.0,
                    "outbox_pending_count": 0,
                    "audit_logs_count": 0,
                },
                "recent_audit_logs": [],
            }

        # Obtener ubicaciones
        places_res = await db.execute(
            select(InventoryStockPlace).where(
                InventoryStockPlace.tenant_id == ctx.tenant_id
            )
        )
        places = {p.code: p for p in places_res.scalars().all()}

        loc_silo1 = places.get("LOC-SILO-01")
        loc_silo2 = places.get("LOC-SILO-02")
        loc_molido = places.get("LOC-TOLVA-MOLIDO")
        loc_planta = places.get("LOC-PISO-PLANTA")
        loc_pigmento = places.get("LOC-ALM-PIGMENTO")
        loc_molino = places.get("LOC-TOLVA-REBABA")
        loc_pt = places.get("LOC-ALM-PT")

        silo1_bal = (
            await InventoryService.get_stock_balance(
                db, ctx, prod_soplado.id, loc_silo1.id
            )
            if (prod_soplado and loc_silo1)
            else 0.0
        )
        silo2_bal = (
            await InventoryService.get_stock_balance(db, ctx, prod_inj.id, loc_silo2.id)
            if (prod_inj and loc_silo2)
            else 0.0
        )
        virgin_total = silo1_bal + silo2_bal

        regrind_tolva = (
            await InventoryService.get_stock_balance(
                db, ctx, prod_regrind.id, loc_molido.id
            )
            if (prod_regrind and loc_molido)
            else 0.0
        )
        regrind_planta = (
            await InventoryService.get_stock_balance(
                db, ctx, prod_regrind.id, loc_planta.id
            )
            if (prod_regrind and loc_planta)
            else 0.0
        )
        regrind_total = regrind_tolva + regrind_planta

        mb_bal = (
            await InventoryService.get_stock_balance(
                db, ctx, prod_mb.id, loc_pigmento.id
            )
            if (prod_mb and loc_pigmento)
            else 0.0
        )
        scrap_bal = (
            await InventoryService.get_stock_balance(
                db, ctx, prod_scrap.id, loc_molino.id
            )
            if (prod_scrap and loc_molino)
            else 0.0
        )

        caja20_bal = (
            await InventoryService.get_stock_balance(db, ctx, prod_caja20.id, loc_pt.id)
            if (prod_caja20 and loc_pt)
            else 0.0
        )
        caja15_bal = (
            await InventoryService.get_stock_balance(db, ctx, prod_caja15.id, loc_pt.id)
            if (prod_caja15 and loc_pt)
            else 0.0
        )
        crates_total = caja20_bal + caja15_bal

        # Logs de auditoría recientes
        audit_res = await db.execute(
            select(SystemAuditLog)
            .where(SystemAuditLog.tenant_id == ctx.tenant_id)
            .order_by(SystemAuditLog.created_at.desc())
            .limit(10)
        )
        recent_audits = [
            {
                "id": str(log.id),
                "created_at": log.created_at.isoformat() if log.created_at else "",
                "entity_name": log.entity_name,
                "action": log.action,
                "new_value": log.new_value,
            }
            for log in audit_res.scalars().all()
        ]

        audit_count_res = await db.execute(
            select(func.count(SystemAuditLog.id)).where(
                SystemAuditLog.tenant_id == ctx.tenant_id
            )
        )
        audit_count = audit_count_res.scalar_one() or 0

        outbox_count_res = await db.execute(
            select(func.count(SystemTransactionalOutbox.id)).where(
                SystemTransactionalOutbox.tenant_id == ctx.tenant_id,
                SystemTransactionalOutbox.status == "PENDING",
            )
        )
        outbox_pending_count = outbox_count_res.scalar_one() or 0

        return {
            "tenant_id": str(ctx.tenant_id),
            "is_seeded": True,
            "kpis": {
                "resin_virgin_total_kg": round(virgin_total, 2),
                "resin_soplado_silo1_kg": round(silo1_bal, 2),
                "resin_inyeccion_silo2_kg": round(silo2_bal, 2),
                "regrind_hopper_kg": round(regrind_total, 2),
                "masterbatch_uv_kg": round(mb_bal, 2),
                "scrap_mill_hopper_kg": round(scrap_bal, 2),
                "finished_crates_total_pcs": round(crates_total, 0),
                "crates_20kg_pcs": round(caja20_bal, 0),
                "crates_15kg_pcs": round(caja15_bal, 0),
                "outbox_pending_count": outbox_pending_count,
                "audit_logs_count": audit_count,
            },
            "recent_audit_logs": recent_audits,
        }

    @app.post("/api/v1/demo/quick-grn")
    async def demo_quick_grn(
        payload: QuickGRNRequest,
        db: AsyncSession = Depends(get_db_session),
        ctx: TenantContext = Depends(get_tenant_context),
    ):
        """Simula y procesa la llegada y pesaje en báscula de un camión de resina HDPE hacia el silo."""
        await _ensure_tenant_is_seeded(db, ctx)

        net_kg = max(0.0, payload.gross_weight_kg - payload.tare_weight_kg)
        if net_kg <= 0:
            raise HTTPException(
                status_code=400, detail="Peso neto debe ser mayor a 0 kg"
            )

        prod = await InventoryService.get_product_by_sku(db, ctx, payload.product_sku)
        if not prod:
            raise HTTPException(
                status_code=404, detail=f"Producto {payload.product_sku} no encontrado"
            )

        dest_silo_res = await db.execute(
            select(InventoryStockPlace).where(
                InventoryStockPlace.code == payload.silo_code,
                InventoryStockPlace.tenant_id == ctx.tenant_id,
            )
        )
        dest_silo = dest_silo_res.scalars().first()

        prov_loc_res = await db.execute(
            select(InventoryStockPlace).where(
                InventoryStockPlace.code == "LOC-PROV-PETRO",
                InventoryStockPlace.tenant_id == ctx.tenant_id,
            )
        )
        prov_loc = prov_loc_res.scalars().first()

        supplier_res = await db.execute(
            select(PurchaseSupplier).where(
                PurchaseSupplier.code == "PROV-PETRO-MEX",
                PurchaseSupplier.tenant_id == ctx.tenant_id,
            )
        )
        supplier = supplier_res.scalars().first()

        if not (dest_silo and prov_loc and supplier):
            raise HTTPException(
                status_code=500, detail="Entidades maestras requeridas no encontradas"
            )

        # 1. Crear y aprobar Orden de Compra para el camión
        po = await PurchaseService.create_purchase_order(
            db,
            ctx,
            PurchaseOrderCreate(
                supplier_id=supplier.id,
                lines=[
                    PurchaseOrderLineCreate(
                        product_id=prod.id,
                        qty_ordered=net_kg,
                        unit_price=prod.standard_cost,
                    )
                ],
            ),
        )
        await PurchaseService.approve_purchase_order(db, ctx, po.id)

        # 2. Registrar Recepción en Báscula (GRN)
        lot_code = f"LOT-PETRO-{generate_uuid7().hex[:6].upper()}"
        grn = await PurchaseService.receive_goods_at_scale(
            db,
            ctx,
            GoodsReceiptCreate(
                purchase_order_id=po.id,
                scale_ticket_number=payload.ticket_number,
                gross_weight_kg=payload.gross_weight_kg,
                tare_weight_kg=payload.tare_weight_kg,
                source_place_id=prov_loc.id,
                dest_place_id=dest_silo.id,
                lot_code=lot_code,
                lines=[
                    GoodsReceiptLineCreate(
                        po_line_id=po.lines[0].id,
                        product_id=prod.id,
                        qty_received_kg=net_kg,
                    )
                ],
            ),
        )

        # 3. Auditoría inmutable y Outbox
        await AuditService.log_change(
            session=db,
            ctx=ctx,
            entity_name="scale_grn",
            entity_id=grn.id,
            action="SCALE_RECEIVE_RESIN",
            previous_value=None,
            new_value={
                "ticket": grn.scale_ticket_number,
                "product_sku": prod.sku,
                "gross_kg": payload.gross_weight_kg,
                "tare_kg": payload.tare_weight_kg,
                "net_kg": net_kg,
                "silo": dest_silo.code,
            },
        )
        await OutboxService.publish(
            session=db,
            ctx=ctx,
            event_type="scale.grn_completed",
            aggregate_type="scale_grn",
            aggregate_id=grn.id,
            payload={
                "ticket": grn.scale_ticket_number,
                "net_kg": net_kg,
                "silo": dest_silo.code,
                "lot_code": lot_code,
            },
        )
        await db.commit()

        new_balance = await InventoryService.get_stock_balance(
            db, ctx, prod.id, dest_silo.id
        )
        return {
            "status": "SUCCESS",
            "ticket_number": grn.scale_ticket_number,
            "net_weight_kg": net_kg,
            "product_sku": prod.sku,
            "silo_code": dest_silo.code,
            "new_silo_balance_kg": new_balance,
        }

    @app.post("/api/v1/demo/quick-production")
    async def demo_quick_production(
        payload: QuickProductionRequest,
        db: AsyncSession = Depends(get_db_session),
        ctx: TenantContext = Depends(get_tenant_context),
    ):
        """Ejecuta una corrida de producción de cajas: consume materias primas, produce cajas terminadas y rebaba flash."""
        await _ensure_tenant_is_seeded(db, ctx)

        crate = await InventoryService.get_product_by_sku(db, ctx, payload.product_sku)
        if not crate:
            raise HTTPException(
                status_code=404, detail=f"Producto {payload.product_sku} no encontrado"
            )

        wc_res = await db.execute(
            select(MRPWorkCenter).where(
                MRPWorkCenter.code == payload.work_center_code,
                MRPWorkCenter.tenant_id == ctx.tenant_id,
            )
        )
        wc = wc_res.scalars().first()
        if not wc:
            raise HTTPException(
                status_code=404,
                detail=f"Centro de trabajo {payload.work_center_code} no encontrado",
            )

        places_res = await db.execute(
            select(InventoryStockPlace).where(
                InventoryStockPlace.tenant_id == ctx.tenant_id
            )
        )
        places = {p.code: p for p in places_res.scalars().all()}
        loc_planta = places.get("LOC-PISO-PLANTA")
        loc_pt = places.get("LOC-ALM-PT")
        loc_molino = places.get("LOC-TOLVA-REBABA")

        if not (loc_planta and loc_pt and loc_molino):
            raise HTTPException(
                status_code=500, detail="Ubicaciones de planta no configuradas"
            )

        # Asegurar BOM para Caja 15kg si no existe
        if payload.product_sku == "CAJA-EXPORT-15KG":
            existing_bom = await db.execute(
                select(MRPBOMStructure).where(
                    MRPBOMStructure.parent_product_id == crate.id,
                    MRPBOMStructure.tenant_id == ctx.tenant_id,
                )
            )
            if not existing_bom.scalars().first():
                prod_soplado = await InventoryService.get_product_by_sku(
                    db, ctx, "HDPE-SOPLADO-5502"
                )
                prod_regrind = await InventoryService.get_product_by_sku(
                    db, ctx, "HDPE-MOLIDO-REC"
                )
                prod_mb = await InventoryService.get_product_by_sku(
                    db, ctx, "MB-VERDE-UV"
                )
                prod_scrap = await InventoryService.get_product_by_sku(
                    db, ctx, "SCRAP-REBABA-HDPE"
                )
                await MRPService.create_bom_line(
                    db,
                    ctx,
                    BOMStructureCreate(
                        parent_product_id=crate.id,
                        child_product_id=prod_soplado.id,
                        qty_ratio=1.05,
                        scrap_return_ratio=0.10,
                        scrap_product_id=prod_scrap.id,
                    ),
                )
                await MRPService.create_bom_line(
                    db,
                    ctx,
                    BOMStructureCreate(
                        parent_product_id=crate.id,
                        child_product_id=prod_regrind.id,
                        qty_ratio=0.42,
                        scrap_return_ratio=0.0,
                    ),
                )
                await MRPService.create_bom_line(
                    db,
                    ctx,
                    BOMStructureCreate(
                        parent_product_id=crate.id,
                        child_product_id=prod_mb.id,
                        qty_ratio=0.03,
                        scrap_return_ratio=0.0,
                    ),
                )

        # Explosión BOM y transferencia de materias primas a piso de planta
        explosion = await MRPService.explode_bom_recursive(
            db, ctx, crate.id, payload.qty_planned
        )
        for comp in explosion:
            comp_prod = await InventoryService.get_product(
                db, ctx, comp["child_product_id"]
            )
            if not comp_prod:
                continue
            source_loc_code = "LOC-SILO-02"
            if "SOPLADO" in comp_prod.sku:
                source_loc_code = "LOC-SILO-01"
            elif "MOLIDO" in comp_prod.sku:
                source_loc_code = "LOC-TOLVA-MOLIDO"
            elif "MB" in comp_prod.sku or "PIGMENTO" in comp_prod.sku:
                source_loc_code = "LOC-ALM-PIGMENTO"

            src_place = places.get(source_loc_code, loc_planta)
            if src_place and src_place.id != loc_planta.id:
                # Verificar saldo en silo/almacén antes de mover; si falta, aprovisionar desde proveedor
                avail = await InventoryService.get_stock_balance(
                    db, ctx, comp_prod.id, src_place.id
                )
                if avail < comp["required_qty"]:
                    prov_place = places.get("LOC-PROV-PETRO")
                    if prov_place:
                        await InventoryService.create_stock_move(
                            db,
                            ctx,
                            StockMoveCreate(
                                product_id=comp_prod.id,
                                source_place_id=prov_place.id,
                                dest_place_id=src_place.id,
                                qty=comp["required_qty"] * 2.0,
                                uom=comp_prod.uom,
                                unit_cost=comp_prod.standard_cost,
                                reference="REABASTECIMIENTO-AUTOMATICO",
                            ),
                        )
                # Mover material al piso de planta
                await InventoryService.create_stock_move(
                    db,
                    ctx,
                    StockMoveCreate(
                        product_id=comp_prod.id,
                        source_place_id=src_place.id,
                        dest_place_id=loc_planta.id,
                        qty=comp["required_qty"],
                        uom=comp_prod.uom,
                        unit_cost=comp_prod.standard_cost,
                        reference=f"ALIMENTACION-MAQUINA-{wc.code}",
                    ),
                )

        # Ejecutar orden de producción
        mo = await MRPService.create_and_complete_production_order(
            db,
            ctx,
            ProductionOrderCreate(
                product_id=crate.id,
                work_center_id=wc.id,
                qty_planned=payload.qty_planned,
                source_place_id=loc_planta.id,
                finished_dest_place_id=loc_pt.id,
                scrap_dest_place_id=loc_molino.id,
            ),
        )

        # Auditoría y outbox
        await AuditService.log_change(
            session=db,
            ctx=ctx,
            entity_name="mrp_production_order",
            entity_id=mo.id,
            action="PRODUCTION_COMPLETED",
            previous_value=None,
            new_value={
                "work_center": wc.code,
                "product_sku": crate.sku,
                "qty_produced": mo.qty_produced,
                "scrap_generated_kg": mo.scrap_generated_kg,
            },
        )
        await OutboxService.publish(
            session=db,
            ctx=ctx,
            event_type="mrp.production_run_completed",
            aggregate_type="mrp_production_order",
            aggregate_id=mo.id,
            payload={
                "work_center": wc.code,
                "product_sku": crate.sku,
                "qty_produced": mo.qty_produced,
                "scrap_generated_kg": mo.scrap_generated_kg,
            },
        )
        await db.commit()

        return {
            "status": "SUCCESS",
            "production_order_id": str(mo.id),
            "work_center": wc.code,
            "product_sku": crate.sku,
            "qty_produced": mo.qty_produced,
            "scrap_generated_kg": mo.scrap_generated_kg,
        }

    @app.post("/api/v1/demo/quick-regrind")
    async def demo_quick_regrind(
        payload: QuickRegrindRequest,
        db: AsyncSession = Depends(get_db_session),
        ctx: TenantContext = Depends(get_tenant_context),
    ):
        """Muele y recupera la rebaba acumulada en la tolva del molino validando el balance estricto de masa."""
        await _ensure_tenant_is_seeded(db, ctx)

        scrap_prod = await InventoryService.get_product_by_sku(
            db, ctx, "SCRAP-REBABA-HDPE"
        )
        regrind_prod = await InventoryService.get_product_by_sku(
            db, ctx, "HDPE-MOLIDO-REC"
        )
        if not (scrap_prod and regrind_prod):
            raise HTTPException(
                status_code=500, detail="Productos de reciclaje no encontrados"
            )

        wc_res = await db.execute(
            select(MRPWorkCenter).where(
                MRPWorkCenter.code == payload.work_center_code,
                MRPWorkCenter.tenant_id == ctx.tenant_id,
            )
        )
        wc = wc_res.scalars().first()
        if not wc:
            raise HTTPException(
                status_code=404, detail="Molino granulador no encontrado"
            )

        places_res = await db.execute(
            select(InventoryStockPlace).where(
                InventoryStockPlace.tenant_id == ctx.tenant_id
            )
        )
        places = {p.code: p for p in places_res.scalars().all()}
        loc_molino = places.get("LOC-TOLVA-REBABA")
        loc_tolva_molido = places.get("LOC-TOLVA-MOLIDO")
        loc_planta = places.get("LOC-PISO-PLANTA")

        # Asegurar saldo de rebaba en tolva de molino
        avail_scrap = await InventoryService.get_stock_balance(
            db, ctx, scrap_prod.id, loc_molino.id
        )
        if avail_scrap < payload.input_qty_kg:
            diff = payload.input_qty_kg - avail_scrap
            await InventoryService.create_stock_move(
                db,
                ctx,
                StockMoveCreate(
                    product_id=scrap_prod.id,
                    source_place_id=loc_planta.id,
                    dest_place_id=loc_molino.id,
                    qty=diff,
                    uom="KG",
                    unit_cost=scrap_prod.standard_cost,
                    reference="RECOLECCION-REBABA-PISO-PLANTA",
                ),
            )

        # Cálculo estricto de balance de masa
        output_regrind = round(
            payload.input_qty_kg * (1.0 - (payload.loss_percent / 100.0)), 2
        )
        process_loss = round(payload.input_qty_kg - output_regrind, 2)

        unbuild = await MRPService.execute_regrind_unbuild(
            db,
            ctx,
            UnbuildOrderCreate(
                work_center_id=wc.id,
                scrap_product_id=scrap_prod.id,
                regrind_product_id=regrind_prod.id,
                source_scrap_place_id=loc_molino.id,
                dest_regrind_place_id=loc_tolva_molido.id,
                input_qty_kg=payload.input_qty_kg,
                output_regrind_qty_kg=output_regrind,
                process_loss_kg=process_loss,
            ),
        )

        # Auditoría y Outbox
        await AuditService.log_change(
            session=db,
            ctx=ctx,
            entity_name="mrp_unbuild_order",
            entity_id=unbuild.id,
            action="REGRIND_MILL_COMPLETED",
            previous_value={"input_scrap_kg": payload.input_qty_kg},
            new_value={
                "work_center": wc.code,
                "regrind_produced_kg": output_regrind,
                "process_loss_kg": process_loss,
                "destination": loc_tolva_molido.code,
            },
        )
        await OutboxService.publish(
            session=db,
            ctx=ctx,
            event_type="mrp.regrind_recycled",
            aggregate_type="mrp_unbuild_order",
            aggregate_id=unbuild.id,
            payload={
                "regrind_produced_kg": output_regrind,
                "process_loss_kg": process_loss,
            },
        )
        await db.commit()

        return {
            "status": "SUCCESS",
            "unbuild_id": str(unbuild.id),
            "input_scrap_kg": payload.input_qty_kg,
            "output_regrind_kg": output_regrind,
            "process_loss_kg": process_loss,
        }

    return app


app = create_app()
