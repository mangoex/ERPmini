import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CreditLimitExceededError,
    ImmutableRecordError,
    ThreeWayMatchError,
    UnbalancedJournalError,
)
from app.core.security import TenantContext
from app.modules.account.schemas import (
    AccountCreate,
    JournalEntryCreate,
    JournalLineCreate,
    VendorBillCreate,
    VendorBillLineCreate,
)
from app.modules.account.service import AccountService
from app.modules.inventory.schemas import (
    ProductCreate,
    StockMoveCreate,
    StockPlaceCreate,
)
from app.modules.inventory.service import InventoryService
from app.modules.mrp.schemas import WorkCenterCreate
from app.modules.mrp.service import MRPService
from app.modules.purchase.schemas import (
    GoodsReceiptCreate,
    GoodsReceiptLineCreate,
    PurchaseOrderCreate,
    PurchaseOrderLineCreate,
    SupplierCreate,
)
from app.modules.purchase.service import PurchaseService
from app.modules.sales.schemas import (
    CustomerCreate,
    SalesOrderCreate,
    SalesOrderLineCreate,
)
from app.modules.sales.service import SalesService


@pytest.mark.asyncio
async def test_sales_credit_limit_and_auto_mrp_trigger(
    db_session: AsyncSession, tenant_context: TenantContext
):
    """Validates credit limit enforcement and automatic MRP production order creation when finished crate stock is insufficient."""
    vendor_loc = await InventoryService.create_place(
        db_session,
        tenant_context,
        StockPlaceCreate(code="VEND-AGRO", name="Vendor", place_type="VENDOR"),
    )
    wh_loc = await InventoryService.create_place(
        db_session,
        tenant_context,
        StockPlaceCreate(code="ALM-CAJAS", name="Almacén Cajas", place_type="INTERNAL"),
    )
    crate = await InventoryService.create_product(
        db_session,
        tenant_context,
        ProductCreate(
            sku="CAJA-EXPORT-15KG",
            name="Caja Agrícola Exportación 15kg",
            category="FINISHED_CRATE",
            uom="PCS",
            weight_kg=1.5,
            min_stock=100.0,
            standard_cost=50.0,
        ),
    )
    wc = await MRPService.create_work_center(
        db_session,
        tenant_context,
        WorkCenterCreate(
            code="SOPLADORA-01",
            name="Sopladora Industrial 01",
            center_type="BLOW_MOLDER",
            mold_code="MOLDE-EXP-15",
            cavities=1,
            cycle_time_seconds=40,
        ),
    )

    # Seed 100 crates in warehouse
    await InventoryService.create_stock_move(
        db_session,
        tenant_context,
        StockMoveCreate(
            product_id=crate.id,
            source_place_id=vendor_loc.id,
            dest_place_id=wh_loc.id,
            qty=100.0,
            uom="PCS",
            unit_cost=50.0,
            reference="INIT-CRATES",
        ),
    )

    customer = await SalesService.create_customer(
        db_session,
        tenant_context,
        CustomerCreate(
            code="CLI-AGRO-SINALOA",
            name="Agroexportadora de Sinaloa S.A.",
            tax_id="ASI010101AAA",
            credit_limit=50000.0,
        ),
    )

    # 1. Order exceeding credit limit (1,000 crates * 80 MXN = 80,000 > 50,000) -> raises CreditLimitExceededError
    over_order = await SalesService.create_sales_order(
        db_session,
        tenant_context,
        SalesOrderCreate(
            customer_id=customer.id,
            warehouse_place_id=wh_loc.id,
            lines=[
                SalesOrderLineCreate(
                    product_id=crate.id,
                    qty=1000.0,
                    unit_price=80.0,
                )
            ],
        ),
    )
    with pytest.raises(CreditLimitExceededError):
        await SalesService.confirm_sales_order(
            db_session,
            tenant_context,
            sales_order_id=over_order.id,
            default_work_center_id=wc.id,
        )

    # 2. Order within credit limit (500 crates * 80 MXN = 40,000 <= 50,000), stock = 100 -> triggers MRP order for deficit of 400 crates
    valid_order = await SalesService.create_sales_order(
        db_session,
        tenant_context,
        SalesOrderCreate(
            customer_id=customer.id,
            warehouse_place_id=wh_loc.id,
            lines=[
                SalesOrderLineCreate(
                    product_id=crate.id,
                    qty=500.0,
                    unit_price=80.0,
                )
            ],
        ),
    )
    confirmation = await SalesService.confirm_sales_order(
        db_session,
        tenant_context,
        sales_order_id=valid_order.id,
        default_work_center_id=wc.id,
    )
    await db_session.commit()

    assert confirmation["status"] == "CONFIRMED"
    assert len(confirmation["triggered_production_orders"]) == 1
    assert confirmation["triggered_production_orders"][0]["qty_planned"] == 400.0


@pytest.mark.asyncio
async def test_three_way_matching_and_double_entry_gl_immutability(
    db_session: AsyncSession, tenant_context: TenantContext
):
    """Validates 3-Way Matching (PO vs Scale GRN vs Vendor Bill) and strict double-entry general ledger invariants."""
    vendor_loc = await InventoryService.create_place(
        db_session,
        tenant_context,
        StockPlaceCreate(code="VEND-3W", name="Proveedor", place_type="VENDOR"),
    )
    silo_loc = await InventoryService.create_place(
        db_session,
        tenant_context,
        StockPlaceCreate(code="SILO-3W", name="Silo", place_type="INTERNAL"),
    )
    resin = await InventoryService.create_product(
        db_session,
        tenant_context,
        ProductCreate(
            sku="RESIN-3WAY",
            name="Resina 3-Way Match",
            category="RAW_RESIN",
            uom="KG",
            weight_kg=1.0,
            min_stock=100.0,
            standard_cost=25.0,
        ),
    )
    supplier = await PurchaseService.create_supplier(
        db_session,
        tenant_context,
        SupplierCreate(
            code="SUP-3W", name="Química Plástica S.A.", tax_id="QPL010101AAA"
        ),
    )

    # Create PO for 1,000 KG @ 25.00 MXN
    po = await PurchaseService.create_purchase_order(
        db_session,
        tenant_context,
        PurchaseOrderCreate(
            supplier_id=supplier.id,
            lines=[
                PurchaseOrderLineCreate(
                    product_id=resin.id, qty_ordered=1000.0, unit_price=25.0
                )
            ],
        ),
    )
    await PurchaseService.approve_purchase_order(db_session, tenant_context, po.id)

    # Receive 1,000 KG net at scale
    grn = await PurchaseService.receive_goods_at_scale(
        db_session,
        tenant_context,
        GoodsReceiptCreate(
            purchase_order_id=po.id,
            scale_ticket_number="TICKET-3WAY-01",
            gross_weight_kg=15000.0,
            tare_weight_kg=14000.0,
            source_place_id=vendor_loc.id,
            dest_place_id=silo_loc.id,
            lot_code="LOT-3W-01",
            lines=[
                GoodsReceiptLineCreate(
                    po_line_id=po.lines[0].id,
                    product_id=resin.id,
                    qty_received_kg=1000.0,
                )
            ],
        ),
    )

    # Create GL Accounts
    acc_inventory = await AccountService.create_account(
        db_session,
        tenant_context,
        AccountCreate(
            code="1150", name="Inventario de Materia Prima Resina", account_type="ASSET"
        ),
    )
    acc_ap = await AccountService.create_account(
        db_session,
        tenant_context,
        AccountCreate(
            code="2110", name="Proveedores Nacionales", account_type="LIABILITY"
        ),
    )

    # 1. Vendor Bill with quantity discrepancy (1,050 KG billed vs 1,000 KG received at scale) -> must raise ThreeWayMatchError
    with pytest.raises(ThreeWayMatchError):
        await AccountService.create_and_validate_vendor_bill(
            db_session,
            tenant_context,
            VendorBillCreate(
                supplier_id=supplier.id,
                purchase_order_id=po.id,
                grn_id=grn.id,
                invoice_number="FAC-PROV-999-BAD",
                debit_account_id=acc_inventory.id,
                credit_account_id=acc_ap.id,
                lines=[
                    VendorBillLineCreate(
                        product_id=resin.id,
                        qty_billed=1050.0,
                        unit_price=25.0,
                    )
                ],
            ),
        )

    # 2. Vendor Bill matching PO and Scale GRN (1,000 KG @ 25.00 = 25,000.00 MXN) -> succeeds and posts balanced GL entries
    bill = await AccountService.create_and_validate_vendor_bill(
        db_session,
        tenant_context,
        VendorBillCreate(
            supplier_id=supplier.id,
            purchase_order_id=po.id,
            grn_id=grn.id,
            invoice_number="FAC-PROV-1000-OK",
            debit_account_id=acc_inventory.id,
            credit_account_id=acc_ap.id,
            lines=[
                VendorBillLineCreate(
                    product_id=resin.id,
                    qty_billed=1000.0,
                    unit_price=25.0,
                )
            ],
        ),
    )
    await db_session.commit()
    assert bill.status == "POSTED"
    assert bill.total_amount == 25000.0

    # 3. Unbalanced manual journal entry (Debit 100 != Credit 90) -> must raise UnbalancedJournalError
    with pytest.raises(UnbalancedJournalError):
        await AccountService.post_journal_entry(
            db_session,
            tenant_context,
            JournalEntryCreate(
                reference="POLIZA-DESCUADRADA",
                lines=[
                    JournalLineCreate(
                        account_id=acc_inventory.id, debit=100.0, credit=0.0
                    ),
                    JournalLineCreate(account_id=acc_ap.id, debit=0.0, credit=90.0),
                ],
            ),
        )

    # 4. Attempt to mutate an existing GL entry -> must raise ImmutableRecordError
    gl_entries = await AccountService.get_gl_entries_by_reference(
        db_session, tenant_context, reference="FAC-PROV-1000-OK"
    )
    assert len(gl_entries) == 2
    gl_entries[0].debit = 999999.0
    with pytest.raises(ImmutableRecordError):
        await db_session.commit()
    await db_session.rollback()
