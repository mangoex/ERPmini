# language: es
Característica: ERPmini — Monolito Modular para Planta Industrial de Soplado e Inyección de Plástico para el Agro
  Como Dirección de Planta y Operaciones de Manufactura Plástica Agrícola
  Quiero un sistema ERP modular transaccional con trazabilidad inmutable de lotes, báscula, molienda, partida doble y nómina 24/7
  Para garantizar cero fugas de inventario de resina, cumplimiento contable estricto y gobernanza operativa con IA

  Antecedentes:
    Dado un entorno multi-tenant con un "tenant_id" y "branch_id" válidos codificados en UUIDv7
    Y la integridad referencial activa con restricción "ON DELETE RESTRICT" en todas las entidades

  # ============================================================================
  # 1. MÓDULO CORE & SYSTEM (UUIDv7, Auditoría Inmutable, Outbox Transaccional, RBAC)
  # ============================================================================
  Escenario: Generación monótona temporal de UUIDv7 y rechazo estricto de UUIDv4
    Dado el generador de claves primarias "generate_uuid7" conforme a RFC 9562
    Cuando se generan 100 identificadores secuenciales en milisegundos consecutivos
    Entonces todos los identificadores tienen versión 7 y están estrictamente ordenados de forma creciente
    Y cuando se intenta validar o registrar una entidad con un identificador "UUIDv4"
    Entonces el sistema rechaza la operación lanzando "DomainValidationError"

  Escenario: Inmutabilidad de la pista de auditoría y registro atómico en Outbox Transaccional
    Dado un evento de negocio ejecutado por un usuario autenticado en el módulo "system"
    Cuando se registra un cambio de estado con "AuditService.log_change" y un evento en "OutboxService.publish"
    Entonces se persiste un registro en "system_audit_logs" con "previous_value" y "new_value" y un evento "PENDING" en "system_transactional_outbox"
    Y cuando se intenta ejecutar un "UPDATE" o "DELETE" sobre "system_audit_logs"
    Entonces el sistema bloquea la mutación lanzando "ImmutableRecordError"

  # ============================================================================
  # 2. MÓDULO INVENTORY & PURCHASE (Doble Entrada, Báscula GRN, Inmutabilidad)
  # ============================================================================
  Escenario: Recepción de Resina Virgen HDPE en Báscula (GRN) y cálculo de inventario por doble entrada
    Dado un proveedor de petroquímica registrado y una Orden de Compra aprobada por 1000.0 KG de "RAW_RESIN" (HDPE Virgen)
    Y las ubicaciones "VENDOR" (Proveedor) e "INTERNAL" (Silo de Resina 01) creadas
    Cuando el camión ingresa a báscula con ticket "TICKET-001", peso bruto 25000.0 KG y tara 24000.0 KG
    Entonces la Recepción de Mercancía (GRN) calcula un peso neto de 1000.0 KG y genera un movimiento en "inventory_stock_moves" desde "VENDOR" hacia "INTERNAL"
    Y el saldo de stock calculado como Suma(Inbound) - Suma(Outbound) en "INTERNAL" es exactamente 1000.0 KG

  Escenario: Prohibición de mutación destructiva en movimientos de inventario y prevención de stock negativo
    Dado un movimiento de inventario confirmado en "inventory_stock_moves" por 1000.0 KG en el Silo de Resina 01
    Cuando un proceso intenta modificar ("UPDATE") la cantidad o eliminar ("DELETE") el registro de "inventory_stock_moves"
    Entonces el sistema rechaza la operación lanzando "ImmutableRecordError"
    Y cuando se solicita transferir 1500.0 KG desde el Silo de Resina 01 hacia "PRODUCTION"
    Entonces el sistema aborta la transferencia lanzando "InsufficientStockError"

  # ============================================================================
  # 3. MÓDULO MRP: SOPLADO/INYECCIÓN, BOM RECURSIVO, REBABA Y MOLIENDA (REGRIND)
  # ============================================================================
  Escenario: Explosión recursiva de BOM y ejecución de orden de producción con generación automática de rebaba
    Dado el Centro de Trabajo "INJECTION_MOLDER" con molde "MOLDE-CAJA-20KG", 2 cavidades y ciclo de 35 segundos
    Y una estructura BOM para fabricar 1 unidad de "FINISHED_CRATE" (Caja Agrícola Cosechera 20kg) que requiere:
      | componente       | qty_ratio | scrap_return_ratio |
      | RAW_RESIN        | 1.40      | 0.10               |
      | REGRIND          | 0.56      | 0.00               |
      | MASTERBATCH_UV   | 0.04      | 0.00               |
    Cuando se ejecuta la explosión recursiva mediante SQL CTE para una orden de 100 cajas agrícolas
    Entonces los requerimientos netos calculados son 140.0 KG de "RAW_RESIN", 56.0 KG de "REGRIND" y 4.0 KG de "MASTERBATCH_UV"
    Y cuando se completa la Orden de Producción por 100 cajas agrícolas
    Entonces se descuentan los insumos de "PRODUCTION", ingresan 100.0 PCS de "FINISHED_CRATE" a almacén y se genera automáticamente un lote de 14.0 KG de "SCRAP_FLASH" (Rebaba/Colada) en la ubicación "SCRAP"

  Escenario: Orden de molienda (Unbuild Order) en Molino Granulador con balance de masa estricto
    Dado un lote acumulado de 100.0 KG de "SCRAP_FLASH" (Rebaba/Colada) en la ubicación "SCRAP"
    Cuando el operador ejecuta una Orden de Molienda en el centro "GRANULATOR_MILL" con 98.5 KG de "REGRIND" recuperado y 1.5 KG de merma por polvo ("process_loss_kg")
    Entonces el sistema valida que "input_qty_kg == output_regrind_qty_kg + process_loss_kg"
    Y consume los 100.0 KG de "SCRAP_FLASH" e ingresa 98.5 KG de "REGRIND" listos para reincorporarse al proceso productivo
    Y si se intenta registrar una molienda donde la salida más la merma no cuadra con la entrada
    Entonces el sistema lanza "DomainValidationError"

  # ============================================================================
  # 4. MÓDULO SALES & ACCOUNT (Control de Crédito, 3-Way Match, Partida Doble)
  # ============================================================================
  Escenario: Bloqueo por límite de crédito y disparo automático de manufactura por déficit de cajas agrícolas
    Dado un cliente agrícola con límite de crédito de 50000.00 MXN y saldo disponible
    Cuando intenta confirmar un pedido de venta que excede su límite de crédito disponible
    Entonces el sistema rechaza la confirmación lanzando "CreditLimitExceededError"
    Y cuando confirma un pedido dentro de su límite de crédito por 500 cajas agrícolas habiendo solo 100 en stock
    Entonces el sistema confirma la orden de venta y dispara automáticamente una Orden de Producción ("mrp_production_orders") por el déficit de 400 cajas

  Escenario: Coincidencia de 3 Vías (3-Way Matching: PO vs GRN vs Factura) y Partida Doble Contable Inmutable
    Dada una Orden de Compra por 1000.0 KG de resina a 25.00 MXN/KG y una Recepción en Báscula (GRN) por 1000.0 KG netos
    Cuando el proveedor envía una factura cobrando 1050.0 KG (discrepancia contra báscula)
    Entonces el motor de validación contable rechaza la factura lanzando "ThreeWayMatchError"
    Y cuando se intenta registrar una póliza contable en "account_gl_entries" donde Suma(Debe) != Suma(Haber)
    Entonces el sistema rechaza el asiento lanzando "UnbalancedJournalError"
    Y una vez asentada una póliza cuadrada, cualquier intento de "UPDATE" o "DELETE" sobre "account_gl_entries" lanza "ImmutableRecordError"

  # ============================================================================
  # 5. MÓDULO HR, BOT & API (Effective-Dating, Turnos 24/7, Nómina, GrokBot RBAC)
  # ============================================================================
  Escenario: Historial laboral inmutable con Effective-Dating, turnos 24/7 y nómina congelada
    Dado un operador de sopladora con salario inicial de 450.00 MXN/día vigente desde "2026-01-01"
    Cuando recibe un incremento salarial a 520.00 MXN/día efectivo el "2026-06-01"
    Entonces el sistema cierra la vigencia anterior ("effective_to = 2026-05-31") e inserta un nuevo registro en "hr_compensation_records" sin sobrescribir el historial
    Y cuando se registra su asistencia biométrica en los turnos "MATUTINO", "VESPERTINO" o "NOCTURNO" y se aprueba la nómina ("hr_pay_runs")
    Entonces los recibos ("hr_paychecks") quedan congelados y cualquier intento de modificación lanza "ImmutableRecordError"

  Escenario: Gobernanza RBAC en Webhook de WhatsApp / GrokBot y disponibilidad de API/UI Industrial
    Dado un mensaje entrante al Webhook de WhatsApp para ejecutar una herramienta crítica de aprobación de factura
    Cuando el empleado remitente tiene rol "OPERADOR_PLANTA" sin permiso "account:approve_invoice"
    Entonces el orquestador del Bot bloquea la ejecución lanzando "RBACPermissionDeniedError" y registra el intento en auditoría
    Y los endpoints REST "/api/v1/..." y el Dashboard Industrial "/" responden satisfactoriamente con telemetría en tiempo real
