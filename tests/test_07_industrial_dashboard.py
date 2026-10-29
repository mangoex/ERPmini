import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TenantContext


@pytest.mark.asyncio
async def test_industrial_dashboard_html_and_demo_endpoints(
    client: AsyncClient, db_session: AsyncSession, tenant_context: TenantContext
):
    """Prueba completa del dashboard industrial servido en GET / y las 4 estaciones de operación en tiempo real."""

    # 1. Verificar que GET / sirve el Dashboard HTML accesible y contiene las marcas requeridas
    resp_dash = await client.get("/")
    assert resp_dash.status_code == 200
    assert "text/html" in resp_dash.headers["content-type"]
    assert "ERPmini" in resp_dash.text
    assert "Báscula Camionera" in resp_dash.text
    assert "Piso de Planta" in resp_dash.text
    assert "Molino Granulador" in resp_dash.text
    assert "GrokBot" in resp_dash.text
    assert "data-theme=" in resp_dash.text

    # 2. Sembrar datos demo mediante POST /api/v1/seed
    seed_resp = await client.post("/api/v1/seed")
    assert seed_resp.status_code == 200
    seed_data = seed_resp.json()
    assert seed_data["status"] == "seeded"
    assert seed_data["work_centers"] == 3
    assert seed_data["products"] == 7

    # 3. Consultar estado en vivo del dashboard (KPIs iniciales)
    state_resp = await client.get("/api/v1/demo/dashboard-state")
    assert state_resp.status_code == 200
    state = state_resp.json()
    assert state["is_seeded"] is True
    kpis = state["kpis"]
    assert kpis["resin_virgin_total_kg"] >= 45000.0
    assert kpis["regrind_hopper_kg"] >= 5000.0
    assert kpis["masterbatch_uv_kg"] >= 1000.0
    assert kpis["finished_crates_total_pcs"] >= 1500.0

    # 4. Estación 1: Registrar Pesaje en Báscula Camionera (Quick GRN)
    # Entrada: Bruto 38,500 - Tara 14,500 = 24,000 kg hacia Silo 1
    grn_resp = await client.post(
        "/api/v1/demo/quick-grn",
        json={
            "ticket_number": "TKT-TEST-001",
            "product_sku": "HDPE-SOPLADO-5502",
            "gross_weight_kg": 38500.0,
            "tare_weight_kg": 14500.0,
            "silo_code": "LOC-SILO-01",
        },
    )
    assert grn_resp.status_code == 200
    grn_data = grn_resp.json()
    assert grn_data["status"] == "SUCCESS"
    assert grn_data["net_weight_kg"] == 24000.0
    assert grn_data["new_silo_balance_kg"] == 25000.0 + 24000.0  # 49,000 kg

    # 5. Estación 2: Lanzar Corrida de Producción en Piso de Planta (Quick Production)
    # 100 Cajas de 20kg generan +14 kg de Rebaba Flash hacia la Tolva del Molino
    prod_resp = await client.post(
        "/api/v1/demo/quick-production",
        json={
            "work_center_code": "ENGEL-DUO-450",
            "product_sku": "CAJA-AGRO-20KG",
            "qty_planned": 100.0,
        },
    )
    assert prod_resp.status_code == 200
    prod_data = prod_resp.json()
    assert prod_data["status"] == "SUCCESS"
    assert prod_data["qty_produced"] == 100.0
    assert prod_data["scrap_generated_kg"] == 14.0

    # Verificar que el stock de rebaba en molino se actualizó en el dashboard
    state_after_prod = (await client.get("/api/v1/demo/dashboard-state")).json()
    assert state_after_prod["kpis"]["scrap_mill_hopper_kg"] == 14.0
    assert state_after_prod["kpis"]["finished_crates_total_pcs"] == 1600.0

    # 6. Estación 3: Molino Granulador (Quick Regrind con Balance de Masa)
    # Moler 14.0 kg de rebaba con 3.5% de pérdida
    regrind_resp = await client.post(
        "/api/v1/demo/quick-regrind",
        json={
            "work_center_code": "PAGANI-GR-50",
            "input_qty_kg": 14.0,
            "loss_percent": 3.5,
        },
    )
    assert regrind_resp.status_code == 200
    regrind_data = regrind_resp.json()
    assert regrind_data["status"] == "SUCCESS"
    assert regrind_data["input_scrap_kg"] == 14.0
    assert regrind_data["output_regrind_kg"] == 13.51
    assert regrind_data["process_loss_kg"] == 0.49
    # Balance de masa estricto: 13.51 + 0.49 == 14.00
    assert (
        abs(
            (regrind_data["output_regrind_kg"] + regrind_data["process_loss_kg"]) - 14.0
        )
        < 1e-4
    )

    # 7. Estación 4: Simulador WhatsApp / GrokBot con RBAC
    # 7.1 Como Gerente de Planta (ADMIN_PLANTA): Ejecuta herramienta restringida exitosamente
    bot_admin_resp = await client.post(
        "/api/v1/bot/whatsapp/webhook",
        headers={"X-User-Roles": "ADMIN_PLANTA"},
        json={
            "from_phone": "+5216671000001",
            "message_text": "Aprobar factura FAC-PROV-1000-OK",
            "requested_tool": "account:approve_invoice",
            "tool_args": {"invoice_number": "FAC-PROV-1000-OK"},
        },
    )
    assert bot_admin_resp.status_code == 200
    assert bot_admin_resp.json()["status"] == "EXECUTED"

    # 7.2 Como Operador de Planta (OPERADOR_PLANTA): Intento de herramienta restringida es bloqueado con 403
    bot_op_resp = await client.post(
        "/api/v1/bot/whatsapp/webhook",
        headers={"X-User-Roles": "OPERADOR_PLANTA"},
        json={
            "from_phone": "+5216671234567",
            "message_text": "Aprobar factura FAC-PROV-1000-OK",
            "requested_tool": "account:approve_invoice",
            "tool_args": {"invoice_number": "FAC-PROV-1000-OK"},
        },
    )
    assert bot_op_resp.status_code == 403
    assert "RBAC Bloqueado" in bot_op_resp.json()["detail"]

    # 7.3 Verificar que el evento bloqueado y las acciones operativas quedaron registradas en la auditoría inmutable
    state_final = (await client.get("/api/v1/demo/dashboard-state")).json()
    actions = [log["action"] for log in state_final["recent_audit_logs"]]
    assert any("SCALE_RECEIVE_RESIN" in a for a in actions)
    assert any("PRODUCTION_COMPLETED" in a for a in actions)
    assert any("REGRIND_MILL_COMPLETED" in a for a in actions)
    assert any("RBAC_BLOCKED" in a for a in actions)
