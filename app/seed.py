"""Población de datos de demostración para Planta de Soplado e Inyección de Plástico."""

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TenantContext
from app.modules.account.schemas import AccountCreate
from app.modules.account.service import AccountService
from app.modules.hr.schemas import DepartmentCreate, EmployeeCreate, JobTitleCreate
from app.modules.hr.service import HRService
from app.modules.inventory.schemas import (
    ProductCreate,
    StockMoveCreate,
    StockPlaceCreate,
)
from app.modules.inventory.service import InventoryService
from app.modules.mrp.schemas import BOMStructureCreate, WorkCenterCreate
from app.modules.mrp.service import MRPService
from app.modules.purchase.schemas import SupplierCreate
from app.modules.purchase.service import PurchaseService
from app.modules.sales.schemas import CustomerCreate
from app.modules.sales.service import SalesService


async def seed_demo_data(session: AsyncSession, ctx: TenantContext) -> dict:
    """Siembra completa de datos maestros y operativos de la planta plástica."""

    # 1. Ubicaciones WMS
    loc_prov = await InventoryService.create_place(
        session,
        ctx,
        StockPlaceCreate(
            code="LOC-PROV-PETRO", name="Proveedor Petroquímica", place_type="VENDOR"
        ),
    )
    loc_silo1 = await InventoryService.create_place(
        session,
        ctx,
        StockPlaceCreate(
            code="LOC-SILO-01", name="Silo 1 Resina HDPE Soplado", place_type="INTERNAL"
        ),
    )
    loc_silo2 = await InventoryService.create_place(
        session,
        ctx,
        StockPlaceCreate(
            code="LOC-SILO-02",
            name="Silo 2 Resina HDPE Inyección",
            place_type="INTERNAL",
        ),
    )
    loc_molido = await InventoryService.create_place(
        session,
        ctx,
        StockPlaceCreate(
            code="LOC-TOLVA-MOLIDO",
            name="Tolva de Regrind Recuperado",
            place_type="INTERNAL",
        ),
    )
    loc_pigmento = await InventoryService.create_place(
        session,
        ctx,
        StockPlaceCreate(
            code="LOC-ALM-PIGMENTO",
            name="Almacén Masterbatch UV",
            place_type="INTERNAL",
        ),
    )
    loc_planta = await InventoryService.create_place(
        session,
        ctx,
        StockPlaceCreate(
            code="LOC-PISO-PLANTA",
            name="Nave Industrial Soplado e Inyección",
            place_type="PRODUCTION",
        ),
    )
    loc_molino = await InventoryService.create_place(
        session,
        ctx,
        StockPlaceCreate(
            code="LOC-TOLVA-REBABA",
            name="Tolva de Molino para Rebaba",
            place_type="SCRAP",
        ),
    )
    loc_pt = await InventoryService.create_place(
        session,
        ctx,
        StockPlaceCreate(
            code="LOC-ALM-PT",
            name="Almacén Producto Terminado Cajas",
            place_type="INTERNAL",
        ),
    )
    loc_cliente = await InventoryService.create_place(
        session,
        ctx,
        StockPlaceCreate(
            code="LOC-CLI-AGRO", name="Cliente Agroexportadora", place_type="CUSTOMER"
        ),
    )

    # 2. Productos
    resin_soplado = await InventoryService.create_product(
        session,
        ctx,
        ProductCreate(
            sku="HDPE-SOPLADO-5502",
            name="Resina HDPE Grado Soplado 5502",
            category="RAW_RESIN",
            uom="KG",
            weight_kg=1.0,
            min_stock=2000.0,
            standard_cost=26.50,
        ),
    )
    resin_inyeccion = await InventoryService.create_product(
        session,
        ctx,
        ProductCreate(
            sku="HDPE-INJ-6070",
            name="Resina HDPE Grado Inyección 6070",
            category="RAW_RESIN",
            uom="KG",
            weight_kg=1.0,
            min_stock=2000.0,
            standard_cost=28.00,
        ),
    )
    regrind = await InventoryService.create_product(
        session,
        ctx,
        ProductCreate(
            sku="HDPE-MOLIDO-REC",
            name="Polietileno Molido Regrind Recuperado",
            category="REGRIND",
            uom="KG",
            weight_kg=1.0,
            min_stock=500.0,
            standard_cost=15.00,
        ),
    )
    mb_verde = await InventoryService.create_product(
        session,
        ctx,
        ProductCreate(
            sku="MB-VERDE-UV",
            name="Masterbatch Verde Agrícola Protección UV",
            category="MASTERBATCH_UV",
            uom="KG",
            weight_kg=1.0,
            min_stock=200.0,
            standard_cost=95.00,
        ),
    )
    scrap_rebaba = await InventoryService.create_product(
        session,
        ctx,
        ProductCreate(
            sku="SCRAP-REBABA-HDPE",
            name="Rebaba y Coladas HDPE Limpias",
            category="SCRAP_FLASH",
            uom="KG",
            weight_kg=1.0,
            min_stock=0.0,
            standard_cost=12.00,
        ),
    )
    caja_20kg = await InventoryService.create_product(
        session,
        ctx,
        ProductCreate(
            sku="CAJA-AGRO-20KG",
            name="Caja Agrícola Cosechera Calada 20kg",
            category="FINISHED_CRATE",
            uom="PCS",
            weight_kg=2.0,
            min_stock=1000.0,
            standard_cost=65.00,
        ),
    )
    caja_15kg = await InventoryService.create_product(
        session,
        ctx,
        ProductCreate(
            sku="CAJA-EXPORT-15KG",
            name="Caja Agrícola Exportación 15kg",
            category="FINISHED_CRATE",
            uom="PCS",
            weight_kg=1.5,
            min_stock=500.0,
            standard_cost=50.00,
        ),
    )

    # 3. Stock inicial
    for prod, target_loc, qty, cost in [
        (resin_soplado, loc_silo1, 25000.0, 26.50),
        (resin_inyeccion, loc_silo2, 20000.0, 28.00),
        (regrind, loc_molido, 5000.0, 15.00),
        (mb_verde, loc_pigmento, 1000.0, 95.00),
        (caja_20kg, loc_pt, 1500.0, 65.00),
    ]:
        await InventoryService.create_stock_move(
            session,
            ctx,
            StockMoveCreate(
                product_id=prod.id,
                source_place_id=loc_prov.id,
                dest_place_id=target_loc.id,
                qty=qty,
                uom=prod.uom,
                unit_cost=cost,
                reference="CARGA-INICIAL-PLANTA",
            ),
        )

    # 4. Centros de Trabajo
    wc_sopladora = await MRPService.create_work_center(
        session,
        ctx,
        WorkCenterCreate(
            code="KAUTEX-KBS-20",
            name="Sopladora Kautex KBS Cajas Agrícolas",
            center_type="BLOW_MOLDER",
            mold_code="MOLDE-KAUTEX-15KG",
            cavities=1,
            cycle_time_seconds=42,
        ),
    )
    wc_inyectora = await MRPService.create_work_center(
        session,
        ctx,
        WorkCenterCreate(
            code="ENGEL-DUO-450",
            name="Inyectora Engel duo 450T Cosechera",
            center_type="INJECTION_MOLDER",
            mold_code="MOLDE-ENGEL-20KG",
            cavities=2,
            cycle_time_seconds=36,
        ),
    )
    wc_molino = await MRPService.create_work_center(
        session,
        ctx,
        WorkCenterCreate(
            code="PAGANI-GR-50",
            name="Molino Granulador Pagani 50HP",
            center_type="GRANULATOR_MILL",
            mold_code=None,
            cavities=1,
            cycle_time_seconds=10,
        ),
    )

    # 5. BOM Recursivo con Rebaba
    await MRPService.create_bom_line(
        session,
        ctx,
        BOMStructureCreate(
            parent_product_id=caja_20kg.id,
            child_product_id=resin_inyeccion.id,
            qty_ratio=1.40,
            scrap_return_ratio=0.10,
            scrap_product_id=scrap_rebaba.id,
        ),
    )
    await MRPService.create_bom_line(
        session,
        ctx,
        BOMStructureCreate(
            parent_product_id=caja_20kg.id,
            child_product_id=regrind.id,
            qty_ratio=0.56,
            scrap_return_ratio=0.0,
            scrap_product_id=None,
        ),
    )
    await MRPService.create_bom_line(
        session,
        ctx,
        BOMStructureCreate(
            parent_product_id=caja_20kg.id,
            child_product_id=mb_verde.id,
            qty_ratio=0.04,
            scrap_return_ratio=0.0,
            scrap_product_id=None,
        ),
    )

    # 6. Proveedor y Cliente
    supplier = await PurchaseService.create_supplier(
        session,
        ctx,
        SupplierCreate(
            code="PROV-PETRO-MEX",
            name="Petroquímica de México S.A. de C.V.",
            tax_id="PME850101AAA",
        ),
    )
    customer = await SalesService.create_customer(
        session,
        ctx,
        CustomerCreate(
            code="CLI-AGRO-VALLES",
            name="Agrícola Los Valles S.P.R. de R.L.",
            tax_id="AVA980202BBB",
            credit_limit=250000.0,
        ),
    )

    # 7. Cuentas Contables
    await AccountService.create_account(
        session,
        ctx,
        AccountCreate(
            code="1150", name="Inventario Materia Prima", account_type="ASSET"
        ),
    )
    await AccountService.create_account(
        session,
        ctx,
        AccountCreate(
            code="1151", name="Inventario Producto Terminado", account_type="ASSET"
        ),
    )
    await AccountService.create_account(
        session,
        ctx,
        AccountCreate(
            code="1120", name="Clientes Agroexportadores", account_type="ASSET"
        ),
    )
    await AccountService.create_account(
        session,
        ctx,
        AccountCreate(
            code="2110", name="Proveedores Petroquímicos", account_type="LIABILITY"
        ),
    )
    await AccountService.create_account(
        session,
        ctx,
        AccountCreate(
            code="4100", name="Venta Cajas Agrícolas", account_type="REVENUE"
        ),
    )
    await AccountService.create_account(
        session,
        ctx,
        AccountCreate(
            code="5100", name="Costo de Producción y Molienda", account_type="EXPENSE"
        ),
    )

    # 8. RRHH y Turnos 24/7
    dept = await HRService.create_department(
        session,
        ctx,
        DepartmentCreate(code="DEP-PLANTA-24-7", name="Operaciones de Planta 24/7"),
    )
    job_op = await HRService.create_job_title(
        session,
        ctx,
        JobTitleCreate(
            code="PUESTO-OP-MAQUINA", title="Operador Técnico de Soplado/Inyección"
        ),
    )

    for emp_code, name, phone, wage in [
        ("EMP-001", "Carlos Mendoza López", "+5216671000001", 480.0),
        ("EMP-002", "Roberto Sánchez Vega", "+5216671000002", 480.0),
        ("EMP-003", "Luis Fernando Beltrán", "+5216671000003", 520.0),
    ]:
        await HRService.create_employee(
            session,
            ctx,
            EmployeeCreate(
                employee_number=emp_code,
                full_name=name,
                whatsapp_phone=phone,
                department_id=dept.id,
                job_title_id=job_op.id,
                daily_wage=wage,
                effective_from=datetime.date(2026, 1, 1),
            ),
        )

    await session.commit()
    return {
        "status": "seeded",
        "work_centers": 3,
        "products": 7,
        "locations": 9,
        "employees": 3,
        "accounts": 6,
    }
