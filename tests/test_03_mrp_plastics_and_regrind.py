import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainValidationError
from app.core.security import TenantContext
from app.modules.inventory.schemas import (
    ProductCreate,
    StockMoveCreate,
    StockPlaceCreate,
)
from app.modules.inventory.service import InventoryService
from app.modules.mrp.schemas import (
    BOMStructureCreate,
    ProductionOrderCreate,
    UnbuildOrderCreate,
    WorkCenterCreate,
)
from app.modules.mrp.service import MRPService


@pytest.mark.asyncio
async def test_mrp_recursive_bom_crate_production_and_regrind_mill(
    db_session: AsyncSession, tenant_context: TenantContext
):
    """Validates recursive CTE BOM explosion, plastic crate production with flash scrap generation, and granulator mill regrind loop."""
    # 1. Setup Locations
    vendor_loc = await InventoryService.create_place(
        db_session,
        tenant_context,
        StockPlaceCreate(code="LOC-EXT-PROV", name="Proveedor", place_type="VENDOR"),
    )
    prod_loc = await InventoryService.create_place(
        db_session,
        tenant_context,
        StockPlaceCreate(
            code="LOC-PLANTA", name="Piso Planta", place_type="PRODUCTION"
        ),
    )
    wh_loc = await InventoryService.create_place(
        db_session,
        tenant_context,
        StockPlaceCreate(
            code="LOC-ALM-PT", name="Almacén Producto Terminado", place_type="INTERNAL"
        ),
    )
    scrap_loc = await InventoryService.create_place(
        db_session,
        tenant_context,
        StockPlaceCreate(
            code="LOC-MOLINO", name="Tolva Molino Rebaba", place_type="SCRAP"
        ),
    )

    # 2. Setup Products: Virgen HDPE, Molido (Regrind), Masterbatch UV, Rebaba (Scrap Flash), Caja Agrícola 20kg
    resin_virgen = await InventoryService.create_product(
        db_session,
        tenant_context,
        ProductCreate(
            sku="HDPE-INJ-VIRGEN",
            name="Resina HDPE Virgen Inyección",
            category="RAW_RESIN",
            uom="KG",
            weight_kg=1.0,
            min_stock=200.0,
            standard_cost=28.0,
        ),
    )
    regrind = await InventoryService.create_product(
        db_session,
        tenant_context,
        ProductCreate(
            sku="HDPE-MOLIDO-REC",
            name="Polietileno Molido Recuperado",
            category="REGRIND",
            uom="KG",
            weight_kg=1.0,
            min_stock=50.0,
            standard_cost=15.0,
        ),
    )
    masterbatch_uv = await InventoryService.create_product(
        db_session,
        tenant_context,
        ProductCreate(
            sku="MB-VERDE-UV",
            name="Masterbatch Verde Agrícola Filtro UV",
            category="MASTERBATCH_UV",
            uom="KG",
            weight_kg=1.0,
            min_stock=20.0,
            standard_cost=95.0,
        ),
    )
    scrap_flash = await InventoryService.create_product(
        db_session,
        tenant_context,
        ProductCreate(
            sku="SCRAP-REBABA-HDPE",
            name="Rebaba y Colada de Soplado/Inyección",
            category="SCRAP_FLASH",
            uom="KG",
            weight_kg=1.0,
            min_stock=0.0,
            standard_cost=12.0,
        ),
    )
    crate = await InventoryService.create_product(
        db_session,
        tenant_context,
        ProductCreate(
            sku="CAJA-AGRO-20KG",
            name="Caja Agrícola Cosechera Calada 20kg",
            category="FINISHED_CRATE",
            uom="PCS",
            weight_kg=2.0,
            min_stock=500.0,
            standard_cost=65.0,
        ),
    )

    # 3. Seed raw materials in PRODUCTION location
    for prod, qty, cost in [
        (resin_virgen, 500.0, 28.0),
        (regrind, 200.0, 15.0),
        (masterbatch_uv, 50.0, 95.0),
    ]:
        await InventoryService.create_stock_move(
            db_session,
            tenant_context,
            StockMoveCreate(
                product_id=prod.id,
                source_place_id=vendor_loc.id,
                dest_place_id=prod_loc.id,
                qty=qty,
                uom="KG",
                unit_cost=cost,
                reference=f"SEED-{prod.sku}",
            ),
        )

    # 4. Create Work Centers (Injection Molder + Granulator Mill)
    molder = await MRPService.create_work_center(
        db_session,
        tenant_context,
        WorkCenterCreate(
            code="INY-HAITIAN-01",
            name="Inyectora 450T Caja Agrícola",
            center_type="INJECTION_MOLDER",
            mold_code="MOLDE-CAJA-20KG",
            cavities=2,
            cycle_time_seconds=35,
        ),
    )
    mill = await MRPService.create_work_center(
        db_session,
        tenant_context,
        WorkCenterCreate(
            code="MOLINO-GRAN-01",
            name="Molino Granulador de Rebaba 50HP",
            center_type="GRANULATOR_MILL",
            mold_code=None,
            cavities=1,
            cycle_time_seconds=10,
        ),
    )

    # 5. Create BOM for 1 FINISHED_CRATE (2.0 kg):
    # - 1.40 kg RAW_RESIN (with 10% scrap_return_ratio -> 0.14 kg SCRAP_FLASH per crate)
    # - 0.56 kg REGRIND
    # - 0.04 kg MASTERBATCH_UV
    await MRPService.create_bom_line(
        db_session,
        tenant_context,
        BOMStructureCreate(
            parent_product_id=crate.id,
            child_product_id=resin_virgen.id,
            qty_ratio=1.40,
            scrap_return_ratio=0.10,
            scrap_product_id=scrap_flash.id,
        ),
    )
    await MRPService.create_bom_line(
        db_session,
        tenant_context,
        BOMStructureCreate(
            parent_product_id=crate.id,
            child_product_id=regrind.id,
            qty_ratio=0.56,
            scrap_return_ratio=0.0,
            scrap_product_id=None,
        ),
    )
    await MRPService.create_bom_line(
        db_session,
        tenant_context,
        BOMStructureCreate(
            parent_product_id=crate.id,
            child_product_id=masterbatch_uv.id,
            qty_ratio=0.04,
            scrap_return_ratio=0.0,
            scrap_product_id=None,
        ),
    )

    # 6. Test Recursive SQL CTE BOM Explosion for 100 crates
    explosion = await MRPService.explode_bom_recursive(
        db_session, tenant_context, parent_product_id=crate.id, target_qty=100.0
    )
    req_by_sku = {item["sku"]: item for item in explosion}
    assert pytest.approx(req_by_sku["HDPE-INJ-VIRGEN"]["required_qty"]) == 140.0
    assert pytest.approx(req_by_sku["HDPE-INJ-VIRGEN"]["expected_scrap_qty"]) == 14.0
    assert pytest.approx(req_by_sku["HDPE-MOLIDO-REC"]["required_qty"]) == 56.0
    assert pytest.approx(req_by_sku["MB-VERDE-UV"]["required_qty"]) == 4.0

    # 7. Execute Production Order for 100 crates
    mo = await MRPService.create_and_complete_production_order(
        db_session,
        tenant_context,
        ProductionOrderCreate(
            product_id=crate.id,
            work_center_id=molder.id,
            qty_planned=100.0,
            source_place_id=prod_loc.id,
            finished_dest_place_id=wh_loc.id,
            scrap_dest_place_id=scrap_loc.id,
        ),
    )
    await db_session.commit()

    assert mo.status == "DONE"
    assert mo.qty_produced == 100.0
    assert pytest.approx(mo.scrap_generated_kg) == 14.0

    # Verify finished crates in warehouse = 100 PCS and flash scrap in mill hopper = 14.0 KG
    assert (
        await InventoryService.get_stock_balance(
            db_session, tenant_context, product_id=crate.id, place_id=wh_loc.id
        )
        == 100.0
    )
    assert (
        pytest.approx(
            await InventoryService.get_stock_balance(
                db_session,
                tenant_context,
                product_id=scrap_flash.id,
                place_id=scrap_loc.id,
            )
        )
        == 14.0
    )

    # 8. Execute Granulator Mill Unbuild Order: grind 14.0 KG of SCRAP_FLASH -> 13.5 KG REGRIND + 0.5 KG dust loss
    # First test invalid mass balance raises DomainValidationError
    with pytest.raises(DomainValidationError):
        await MRPService.execute_regrind_unbuild(
            db_session,
            tenant_context,
            UnbuildOrderCreate(
                work_center_id=mill.id,
                scrap_product_id=scrap_flash.id,
                regrind_product_id=regrind.id,
                source_scrap_place_id=scrap_loc.id,
                dest_regrind_place_id=prod_loc.id,
                input_qty_kg=14.0,
                output_regrind_qty_kg=13.5,
                process_loss_kg=2.0,  # 13.5 + 2.0 != 14.0 -> invalid!
            ),
        )

    # Valid mass balance: 13.5 + 0.5 == 14.0 KG
    unbuild = await MRPService.execute_regrind_unbuild(
        db_session,
        tenant_context,
        UnbuildOrderCreate(
            work_center_id=mill.id,
            scrap_product_id=scrap_flash.id,
            regrind_product_id=regrind.id,
            source_scrap_place_id=scrap_loc.id,
            dest_regrind_place_id=prod_loc.id,
            input_qty_kg=14.0,
            output_regrind_qty_kg=13.5,
            process_loss_kg=0.5,
        ),
    )
    await db_session.commit()

    assert unbuild.status == "DONE"
    # Scrap hopper is now empty (0.0 KG)
    assert (
        pytest.approx(
            await InventoryService.get_stock_balance(
                db_session,
                tenant_context,
                product_id=scrap_flash.id,
                place_id=scrap_loc.id,
            )
        )
        == 0.0
    )
    # Regrind in production is 200 - 56 + 13.5 = 157.5 KG
    assert (
        pytest.approx(
            await InventoryService.get_stock_balance(
                db_session, tenant_context, product_id=regrind.id, place_id=prod_loc.id
            )
        )
        == 157.5
    )
