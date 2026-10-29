import pytest
from app.modules.inventory.schemas import (
    ProductCreate,
    StockMoveCreate,
    StockPlaceCreate,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ImmutableRecordError, InsufficientStockError
from app.core.security import TenantContext
from app.modules.inventory.service import InventoryService
from app.modules.purchase.schemas import (
    GoodsReceiptCreate,
    GoodsReceiptLineCreate,
    PurchaseOrderCreate,
    PurchaseOrderLineCreate,
    SupplierCreate,
)
from app.modules.purchase.service import PurchaseService


@pytest.mark.asyncio
async def test_double_entry_inventory_and_scale_grn(
    db_session: AsyncSession, tenant_context: TenantContext
):
    """Validates scale GRN reception (gross - tare = net), double-entry stock calculation, and immutability."""
    # 1. Create locations (VENDOR, INTERNAL Silo, PRODUCTION)
    vendor_loc = await InventoryService.create_place(
        db_session,
        tenant_context,
        StockPlaceCreate(
            code="VENDOR-PETRO", name="Proveedor Petroquímica", place_type="VENDOR"
        ),
    )
    silo_loc = await InventoryService.create_place(
        db_session,
        tenant_context,
        StockPlaceCreate(
            code="SILO-HDPE-01", name="Silo Resina HDPE 01", place_type="INTERNAL"
        ),
    )
    prod_loc = await InventoryService.create_place(
        db_session,
        tenant_context,
        StockPlaceCreate(
            code="NAVE-SOPLADO",
            name="Nave de Soplado e Inyección",
            place_type="PRODUCTION",
        ),
    )

    # 2. Create RAW_RESIN product
    resin = await InventoryService.create_product(
        db_session,
        tenant_context,
        ProductCreate(
            sku="HDPE-SOPLADO-5502",
            name="Polietileno Alta Densidad Grado Soplado",
            category="RAW_RESIN",
            uom="KG",
            weight_kg=1.0,
            min_stock=500.0,
            standard_cost=26.50,
        ),
    )

    # 3. Create Supplier and Purchase Order for 1,000 KG
    supplier = await PurchaseService.create_supplier(
        db_session,
        tenant_context,
        SupplierCreate(
            code="PROV-POLIMEROS-01",
            name="Polímeros del Golfo S.A. de C.V.",
            tax_id="PGO990101AAA",
        ),
    )
    po = await PurchaseService.create_purchase_order(
        db_session,
        tenant_context,
        PurchaseOrderCreate(
            supplier_id=supplier.id,
            lines=[
                PurchaseOrderLineCreate(
                    product_id=resin.id,
                    qty_ordered=1000.0,
                    unit_price=26.50,
                )
            ],
        ),
    )
    await PurchaseService.approve_purchase_order(db_session, tenant_context, po.id)

    # 4. Receive resin on truck scale (GRN): Gross 25,000 kg - Tare 24,000 kg = Net 1,000 kg
    grn = await PurchaseService.receive_goods_at_scale(
        db_session,
        tenant_context,
        GoodsReceiptCreate(
            purchase_order_id=po.id,
            scale_ticket_number="BASCULA-2026-0001",
            gross_weight_kg=25000.0,
            tare_weight_kg=24000.0,
            source_place_id=vendor_loc.id,
            dest_place_id=silo_loc.id,
            lot_code="LOTE-HDPE-202610",
            lines=[
                GoodsReceiptLineCreate(
                    po_line_id=po.lines[0].id,
                    product_id=resin.id,
                    qty_received_kg=1000.0,
                )
            ],
        ),
    )
    await db_session.commit()

    assert grn.net_weight_kg == 1000.0
    assert grn.status == "DONE"

    # 5. Verify Double-Entry Stock in Silo = 1,000 KG
    silo_stock = await InventoryService.get_stock_balance(
        db_session, tenant_context, product_id=resin.id, place_id=silo_loc.id
    )
    assert silo_stock == 1000.0

    # 6. Prevent Negative Stock -> Requesting 1,500 KG from Silo must raise InsufficientStockError
    with pytest.raises(InsufficientStockError):
        await InventoryService.create_stock_move(
            db_session,
            tenant_context,
            StockMoveCreate(
                product_id=resin.id,
                source_place_id=silo_loc.id,
                dest_place_id=prod_loc.id,
                qty=1500.0,
                uom="KG",
                unit_cost=26.50,
                reference="OVERDRAFT-TEST",
            ),
        )

    # 7. Transfer 300 KG to Production -> Silo = 700 KG, Production = 300 KG
    move = await InventoryService.create_stock_move(
        db_session,
        tenant_context,
        StockMoveCreate(
            product_id=resin.id,
            source_place_id=silo_loc.id,
            dest_place_id=prod_loc.id,
            qty=300.0,
            uom="KG",
            unit_cost=26.50,
            reference=" CONSUMO-SOPLADO-01",
        ),
    )
    await db_session.commit()

    assert (
        await InventoryService.get_stock_balance(
            db_session, tenant_context, product_id=resin.id, place_id=silo_loc.id
        )
        == 700.0
    )
    assert (
        await InventoryService.get_stock_balance(
            db_session, tenant_context, product_id=resin.id, place_id=prod_loc.id
        )
        == 300.0
    )

    # 8. Attempt to UPDATE or DELETE a stock move -> must raise ImmutableRecordError
    move.qty = 9999.0
    with pytest.raises(ImmutableRecordError):
        await db_session.commit()
    await db_session.rollback()
