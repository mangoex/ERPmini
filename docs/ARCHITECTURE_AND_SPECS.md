# DOCUMENTO DE ARQUITECTURA Y ESPECIFICACIÓN TÉCNICA (SBD): ERPmini — Planta Industrial de Soplado e Inyección de Plástico para el Agro

## 1. Visión Arquitectónica y Gobernanza (Contexto, Ecosistema y Clasificación de Certeza)

### 1.1 Matriz de Certidumbre de Hallazgos (CEO Discovery)
| Hallazgo / Regla de Diseño | Estado | Fuente / Justificación |
| :--- | :--- | :--- |
| **Arquitectura de Monolito Modular Estricto** | `Confirmado` | PRD §1 y §2. Prohibición de imports cruzados de modelos internos y joins directos inter-módulo; validado por `import-linter`. |
| **Claves Primarias `UUIDv7` Monótonas Temporales** | `Confirmado` | PRD §2 y §5. Prohibido `UUIDv4`; prefijo de timestamp de 48 bits en milisegundos evita fragmentación de índices B-Tree. |
| **Integridad Referencial `ON DELETE RESTRICT`** | `Confirmado` | PRD §5. Todas las llaves foráneas declaran `ON DELETE RESTRICT` para impedir orfandad histórica. |
| **Pista de Auditoría Universal (`system_audit_logs`)** | `Confirmado` | PRD §2 y §5. Captura atómica inmutable con `previous_value` y `new_value` en JSONB. |
| **Patrón Outbox Transaccional (`system_transactional_outbox`)** | `Confirmado` | PRD §2 y §6. Erradica el *dual-write problem*; eventos insertados en la misma transacción ACID de negocio. |
| **RBAC + PostgreSQL RLS (`tenant_id` / `branch_id`)** | `Confirmado` | PRD §2. `SET LOCAL app.current_tenant_id` y `SET LOCAL app.current_branch_id` por transacción para evitar *context leaking*. |
| **Inventario Inmutable por Doble Entrada (`stock_moves`)** | `Confirmado` | PRD §3, §4.3 y §5. Prohibido `UPDATE` sobre saldos; $\text{Stock} = \sum \text{Inbound} - \sum \text{Outbound}$. |
| **Dominio Plástico/Agro (Resina, Molido, Masterbatch UV, Rebaba, Cajas, Molienda)** | `Confirmado` | Requerimiento de dominio industrial + conceptos de manufactura abierta AureusERP (`work_centers`, `bom_structures` con `scrap_return_ratio`, `unbuild_orders`). |
| **Coincidencia de 3 Vías (`3-Way Matching`: PO vs GRN vs Invoice)** | `Confirmado` | PRD §4.2, §4.5 y §5. Validación obligatoria en báscula (GRN) antes de aprobar/postear factura de proveedor. |
| **Partida Doble Contable Estricta (`gl_entries`)** | `Confirmado` | PRD §4.5 y §5. $\sum \text{Debe} = \sum \text{Haber}$ verificado atómicamente por asiento/transacción. |
| **RRHH con `Effective-Dating` y Turnos 24/7** | `Confirmado` | PRD §3, §4.6 y §5. `job_assignments` y `compensation_records` inmutables con `effective_from`/`effective_to`; turnos Matutino/Vespertino/Nocturno. |
| **Compatibilidad Dual PostgreSQL + SQLite Async (`aiosqlite`) para Suite Pytest** | `Inferido` | `pyproject.toml` incluye `asyncpg` y `aiosqlite`. Se usan nombres de tabla con prefijo de módulo (`system_audit_logs`, `inventory_stock_moves`, etc.) para operar sin fricción tanto en SQLite (tests rápidos TDD) como en PostgreSQL (producción con RLS). |

---

## 2. Estructura del Monolito Modular Estricto

El sistema se organiza bajo `app/` con fronteras lógicas infranqueables verificadas mediante `import-linter`:

```text
app/
├── core/
│   ├── config.py           # Settings (Pydantic Settings v2)
│   ├── database.py         # AsyncEngine, AsyncSession, RLS Context Manager (SET LOCAL)
│   ├── uuid7.py            # Generador determinista/monótono RFC 9562 UUIDv7
│   ├── exceptions.py       # DomainError, FSMTransitionError, InsufficientStockError, CreditLimitExceededError, ThreeWayMatchError, UnbalancedJournalError, RBACPermissionDeniedError, ImmutableRecordError
│   ├── fsm.py              # Motor de Máquinas de Estados Finitos Deterministas
│   └── security.py         # Contexto de Tenant/Branch, evaluación RBAC y decoradores
├── modules/
│   ├── system/             # RBAC, RLS Context, Audit Logs, Transactional Outbox
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py      # Public Contract (AuditService, OutboxService, RBACService)
│   │   └── router.py
│   ├── inventory/          # WMS Doble Entrada, Ubicaciones, Productos Plástico/Agro, Lotes, Movimientos
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py      # Public Contract (InventoryService)
│   │   └── router.py
│   ├── purchase/           # Proveedores, Órdenes de Compra (PO), Recepción en Báscula (GRN)
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py      # Public Contract (PurchaseService)
│   │   └── router.py
│   ├── mrp/                # Centros de Trabajo (Sopladoras/Inyectoras), BOM Recursivo + Rebaba, Producción, Molienda (Unbuild)
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py      # Public Contract (MRPService)
│   │   └── router.py
│   ├── sales/              # Clientes, CRM Leads, Cotizaciones/Órdenes de Venta, Control de Crédito
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py      # Public Contract (SalesService)
│   │   └── router.py
│   ├── account/            # Plan de Cuentas, Facturas (Cliente/Proveedor con 3-Way Match), Libro Mayor (GL Entries)
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py      # Public Contract (AccountService)
│   │   └── router.py
│   ├── hr/                 # Departamentos, Puestos, Empleados, Effective-Dating, Biométricos 24/7, Nómina Inmutable
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py      # Public Contract (HRService)
│   │   └── router.py
│   └── bot/                # Webhook WhatsApp + GrokBot Tool-Calling + Consumidor Outbox con RBAC
│       ├── models.py
│       ├── schemas.py
│       ├── service.py      # Public Contract (BotOrchestratorService)
│       └── router.py
└── main.py                 # FastAPI App Factory + Middleware RLS & Auditoría + UI Industrial
```

### Reglas de Frontera (`import-linter`)
1. **Prohibición de acceso a modelos ajenos**: Ningún módulo `app.modules.<A>` puede importar `app.modules.<B>.models`.
2. **Comunicación exclusiva por Contratos Públicos o Eventos Outbox**: La interacción entre módulos se realiza únicamente invocando `service.py` (pasando DTOs Pydantic/primitivos dentro de la misma `AsyncSession` transaccional) o reaccionando a eventos de `system_transactional_outbox`.
3. **Prohibición de `DELETE` físico y `UPDATE` destructivo**: Los asientos de inventario (`stock_moves`), asientos contables (`gl_entries`), registros históricos (`job_assignments`, `compensation_records` liquidados, `paychecks` aprobados) y pistas de auditoría (`system_audit_logs`) rechazan mutaciones destructivas a nivel de servicio y mediante *event listeners* de SQLAlchemy (`before_update`, `before_delete`).

---

## 3. Especificación Transversal del Sistema (`app/core` y `app/modules/system`)

### 3.1 Estándar `UUIDv7` Obligatorio
- Toda clave primaria `id` utiliza `UUIDv7` (128 bits: 48 bits `unix_ts_ms` big-endian + 4 bits `ver=0111` + 12 bits `rand_a`/secuencia monótona + 2 bits `var=10` + 62 bits `rand_b`).
- Validador de dominio: Si cualquier entidad recibe un `UUID` cuya versión sea distinta de `7` (por ejemplo, `UUIDv4`), el sistema lanza `ValueError` / `DomainValidationError`.

### 3.2 Multi-Tenancy y Seguridad a Nivel de Fila (RLS)
Todas las tablas operativas incluyen:
- `tenant_id: UUID` (`NOT NULL`, indexado)
- `branch_id: UUID` (`NULLABLE` o `NOT NULL` según entidad, indexado)
- En cada transacción SQL en PostgreSQL, el gestor de sesión ejecuta:
  ```sql
  SET LOCAL app.current_tenant_id = '<tenant_uuid>';
  SET LOCAL app.current_branch_id = '<branch_uuid>';
  ```

---

## 4. Especificación de Dominio: Planta de Plástico y Agro

1. **Módulo `inventory`**:
   - Ubicaciones (`inventory_stock_places`): `INTERNAL`, `VENDOR`, `CUSTOMER`, `SCRAP`, `PRODUCTION`.
   - Productos (`inventory_products`): `RAW_RESIN`, `REGRIND`, `MASTERBATCH_UV`, `FINISHED_CRATE`, `SCRAP_FLASH`, `uom` (`KG` o `PCS`), `weight_kg`, `min_stock`, `standard_cost`.
   - Lotes (`inventory_stock_lots`) y Libro Mayor Inmutable (`inventory_stock_moves`): Prohibido `UPDATE` o `DELETE` sobre `inventory_stock_moves`. Stock disponible calculado por $\sum \text{Inbound} - \sum \text{Outbound}$.
2. **Módulo `purchase`**:
   - Proveedores (`purchase_suppliers`), Órdenes de Compra (`purchase_orders`, `purchase_order_lines`), Recepción en Báscula (`purchase_goods_receipt_notes`, `purchase_goods_receipt_lines`) con `scale_ticket_number`, `gross_weight_kg`, `tare_weight_kg`, `net_weight_kg`.
3. **Módulo `mrp`**:
   - Centros de Trabajo (`mrp_work_centers`): `INJECTION_MOLDER`, `BLOW_MOLDER`, `GRANULATOR_MILL`, con `mold_code`, `cavities`, `cycle_time_seconds`.
   - Lista de Materiales Recursiva (`mrp_bom_structures`): `parent_product_id`, `child_product_id`, `qty_ratio`, `scrap_return_ratio`, `scrap_product_id`. Explosión con SQL CTE recursiva (`WITH RECURSIVE bom_explosion`).
   - Órdenes de Producción (`mrp_production_orders`): Consume resina virgen + molido + masterbatch UV, ingresa cajas agrícolas terminadas y genera automáticamente el subproducto de rebaba (`SCRAP_FLASH`) hacia molino.
   - Órdenes de Molienda (`mrp_unbuild_orders`): Transforma `SCRAP_FLASH` o cajas defectuosas en `REGRIND` validando balance de masa (`input_qty_kg == output_regrind_qty_kg + process_loss_kg`).
4. **Módulo `sales` & `crm`**:
   - Clientes (`sales_customers` con `credit_limit`), Oportunidades (`crm_leads`), Órdenes de Venta (`sales_orders`, `sales_order_lines`). Validación de límite de crédito al confirmar y creación automática de `mrp_production_order` si hay déficit de stock.
5. **Módulo `account`**:
   - Cuentas (`account_accounts`), Facturas (`account_invoices`, `account_invoice_lines`) con algoritmo de Coincidencia de 3 Vías (`3-Way Matching`: PO vs GRN vs Vendor Bill), y Libro Mayor (`account_gl_entries`) inmutable con $\sum \text{Debe} = \sum \text{Haber}$.
6. **Módulo `hr`**:
   - Departamentos (`hr_departments`), Puestos (`hr_job_titles`), Empleados (`hr_employees`), Asignaciones de Puesto (`hr_job_assignments`) y Compensaciones (`hr_compensation_records`) con `Effective-Dating` (`effective_from`, `effective_to`), Asistencia Biométrica 24/7 en 3 turnos (`MATUTINO`, `VESPERTINO`, `NOCTURNO`) y Nómina (`hr_pay_runs`, `hr_paychecks`) congelada al aprobarse.
7. **Módulo `bot`**:
   - Webhook de WhatsApp + GrokBot Tool-Calling gobernado por RBAC (`RBACPermissionDeniedError` si el empleado carece de permiso) + Despachador de eventos desde `system_transactional_outbox`.
