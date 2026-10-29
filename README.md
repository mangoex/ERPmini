# ERPmini: Modular Monolith Enterprise ERP

**ERPmini** es una plataforma ERP empresarial de arquitectura modular monolítica estricta, desarrollada en **Python 3.12**, **FastAPI**, **SQLAlchemy 2.0 (async)** y **Pydantic v2**. Diseñada específicamente para industrias de manufactura y transformación (ej. inyección y soplado de plástico), incluye trazabilidad completa, partidas dobles, control de lotes y merma/molino, 3-way matching en compras, contabilidad inmutable, gestión de turnos 24/7 de nómina congelada y bot omnicanal con RBAC.

---

## 🏛️ Arquitectura Modular Monolítica

El sistema implementa límites estrictos entre módulos:
- **`app/core/`**: Infraestructura común, base de datos asíncrona, generador monótono RFC 9562 UUIDv7, FSM genérico determinista, seguridad RBAC multi-tenant, listeners de inmutabilidad y excepciones de dominio.
- **`app/modules/`**:
  1. **`system`**: Auditoría inmutable (`SystemAuditLog`), outbox transaccional (`SystemTransactionalOutbox`), control de acceso RBAC.
  2. **`inventory`**: Partida doble de inventario (`InventoryStockMove`), ubicaciones físicas y virtuales, lotes (`InventoryStockLot`), pesaje de báscula en recepción.
  3. **`purchase`**: Proveedores, órdenes de compra (`PurchaseOrder`), notas de recepción de mercancía (`PurchaseGoodsReceiptNote`).
  4. **`mrp`**: Centros de trabajo, lista de materiales recursiva (BOM multinivel), órdenes de producción (`MRPProductionOrder`), recuperación de merma/regrind y desensamble (`MRPUnbuildOrder`).
  5. **`sales`**: Clientes con límite de crédito estricto, leads de CRM, órdenes de venta y detonación automática de producción MRP.
  6. **`account`**: Facturación de proveedor con validación 3-Way Matching (PO vs GRN vs Factura), pólizas de diario contable balanceadas e inmutables (`AccountGLEntry`).
  7. **`hr`**: Empleados, departamentos, puestos, compensaciones con vigencia histórica (effective dating), registro biométrico 24/7 y nómina congelada (`HRPayRun`).
  8. **`bot`**: Orquestador de chat omnicanal (ej. WhatsApp / GrokBot) con ejecución de herramientas y RBAC.

> **Regla de oro de modularidad:** Ningún módulo puede importar modelos SQLAlchemy de otro módulo (`app.modules.<A>` nunca importa `app.modules.<B>.models`). La interacción entre módulos se realiza exclusivamente mediante servicios y esquemas tipados. Esto es verificado automáticamente mediante `import-linter` y AST en los tests.

---

## 🚀 Requisitos y Puesta en Marcha

### Requisitos previos
- Python 3.12+
- Gestor de paquetes [`uv`](https://docs.astral.sh/uv/) (recomendado) o `pip`
- Docker y Docker Compose (opcional para ejecución en contenedores)

### 1. Clonar e Instalar Dependencias

```bash
uv sync
```

### 2. Configurar Variables de Entorno

```bash
cp .env.example .env
```

Por defecto, en desarrollo local utiliza SQLite en memoria o `./erpmini.db`. Para producción, utiliza PostgreSQL 16 con `asyncpg`.

### 3. Ejecutar la Suite de Pruebas y Linters

```bash
# Ejecutar todas las pruebas unitarias y de integración (100% aprobación)
uv run pytest -v

# Verificar el cumplimiento estricto de límites arquitectónicos
uv run lint-imports
```

### 4. Iniciar el Servidor de Desarrollo

```bash
uv run uvicorn app.main:app --reload --port 8000
```

- **Dashboard Principal**: `http://localhost:8000/`
- **Documentación Interactiva (Swagger UI)**: `http://localhost:8000/docs`
- **Documentación ReDoc**: `http://localhost:8000/redoc`
- **Healthcheck**: `http://localhost:8000/health`
- **Poblar Datos Demo (Semilla Industrial de Plásticos)**: `POST http://localhost:8000/api/v1/seed`
- **Resumen del Sistema**: `GET http://localhost:8000/api/v1/summary`

---

## 🐳 Despliegue con Docker y Docker Compose

### Levantar con Docker Compose (PostgreSQL 16 + ERPmini)

```bash
docker compose up --build -d
```

Esto levantará:
- `erpmini-db`: Contenedor PostgreSQL 16 Alpine con healthcheck integrado y persistencia en volumen `postgres_data`.
- `erpmini-web`: Contenedor ERPmini FastAPI con imagen ultra-ligera basada en `uv` y Python 3.12 slim.

### Despliegue en Railway o Easypanel

1. Conectar el repositorio de Git en el panel de **Railway** o **Easypanel**.
2. Agregar un servicio de base de datos **PostgreSQL 16**.
3. Configurar las variables de entorno en el servicio web:
   - `DATABASE_URL`: `postgresql+asyncpg://<USER>:<PASSWORD>@<HOST>:<PORT>/<DATABASE>`
   - `ENVIRONMENT`: `production`
   - `SECRET_KEY`: `<cadena_aleatoria_segura_min_32_caracteres>`
   - `PORT`: `8000`
4. El `Dockerfile` se detectará y compilará automáticamente en multi-stage con compilación de bytecode y verificación de healthcheck en `/health`.

---

## 🧪 Estructura de Pruebas

- `tests/test_01_core_and_system.py`: Monotonía estricta de UUIDv7, inmutabilidad de logs de auditoría, outbox transaccional, RBAC y cascada restrictiva de claves foráneas.
- `tests/test_02_inventory_and_purchase.py`: Movimientos de inventario por partida doble y pesaje con báscula en notas de recepción de mercancía.
- `tests/test_03_mrp_plastics_and_regrind.py`: Listas de materiales multinivel recursivas, orden de producción de cajas plásticas con merma y molino de regrind.
- `tests/test_04_sales_and_account_3way.py`: Verificación de límite de crédito en ventas con auto-trigger MRP, conciliación 3-Way Matching e inmutabilidad contable de asientos GL.
- `tests/test_05_hr_bot_and_api.py`: Recursos Humanos con vigencia histórica de sueldos, turnos continuos 24/7, nómina congelada, webhook de bot con RBAC y endpoints de la API industrial.
- `tests/test_06_architecture_boundaries.py`: Validación sintáctica por AST e Import-Linter para garantizar que no existan importaciones cruzadas entre modelos.
