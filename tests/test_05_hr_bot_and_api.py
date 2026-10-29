from datetime import UTC, date, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ImmutableRecordError, RBACPermissionDeniedError
from app.core.security import TenantContext
from app.modules.bot.schemas import WhatsAppWebhookPayload
from app.modules.bot.service import BotOrchestratorService
from app.modules.hr.schemas import (
    BiometricPunchCreate,
    CompensationUpdate,
    DepartmentCreate,
    EmployeeCreate,
    JobTitleCreate,
    PayRunCreate,
)
from app.modules.hr.service import HRService


@pytest.mark.asyncio
async def test_hr_effective_dating_24_7_shifts_and_frozen_payroll(
    db_session: AsyncSession, tenant_context: TenantContext
):
    """Validates Effective-Dating on compensation without overwriting history, 3-shift biometric attendance, and immutable approved paychecks."""
    dept = await HRService.create_department(
        db_session,
        tenant_context,
        DepartmentCreate(code="DEP-SOPLADO", name="Operaciones de Soplado 24/7"),
    )
    job = await HRService.create_job_title(
        db_session,
        tenant_context,
        JobTitleCreate(code="OP-SOPLADORA-A", title="Operador de Sopladora Nivel A"),
    )

    # 1. Hire employee with initial compensation effective 2026-01-01
    emp = await HRService.create_employee(
        db_session,
        tenant_context,
        EmployeeCreate(
            employee_number="EMP-0042",
            full_name="Juan Pérez Mendoza",
            whatsapp_phone="+5216671234567",
            department_id=dept.id,
            job_title_id=job.id,
            daily_wage=450.0,
            effective_from=date(2026, 1, 1),
        ),
    )

    # 2. Promote compensation effective 2026-06-01 -> closes previous record at 2026-05-31 and inserts new record
    await HRService.update_compensation_effective_dated(
        db_session,
        tenant_context,
        CompensationUpdate(
            employee_id=emp.id,
            new_daily_wage=520.0,
            effective_from=date(2026, 6, 1),
            reason="Ajuste anual y certificación en cambio de molde",
        ),
    )
    await db_session.commit()

    comp_history = await HRService.get_compensation_history(
        db_session, tenant_context, employee_id=emp.id
    )
    assert len(comp_history) == 2
    assert comp_history[0].daily_wage == 450.0
    assert comp_history[0].effective_from == date(2026, 1, 1)
    assert comp_history[0].effective_to == date(2026, 5, 31)
    assert comp_history[1].daily_wage == 520.0
    assert comp_history[1].effective_from == date(2026, 6, 1)
    assert comp_history[1].effective_to is None

    # 3. Record biometric punches across 3 shifts (MATUTINO, VESPERTINO, NOCTURNO)
    for shift_name in ["MATUTINO", "VESPERTINO", "NOCTURNO"]:
        await HRService.record_biometric_punch(
            db_session,
            tenant_context,
            BiometricPunchCreate(
                employee_id=emp.id,
                shift=shift_name,
                punch_in=datetime(2026, 6, 10, 6, 0, tzinfo=UTC),
                punch_out=datetime(2026, 6, 10, 14, 0, tzinfo=UTC),
                device_id="BIO-TORNIQUETE-01",
            ),
        )

    # 4. Generate and approve PayRun -> freezes paychecks
    pay_run = await HRService.create_and_approve_pay_run(
        db_session,
        tenant_context,
        PayRunCreate(
            period_code="2026-S24",
            start_date=date(2026, 6, 8),
            end_date=date(2026, 6, 14),
            days_worked=7,
        ),
    )
    await db_session.commit()
    assert pay_run.status == "APPROVED"
    assert len(pay_run.paychecks) == 1
    paycheck = pay_run.paychecks[0]
    assert paycheck.gross_amount == 520.0 * 7

    # Attempt to modify frozen paycheck -> must raise ImmutableRecordError
    paycheck.gross_amount = 99999.0
    with pytest.raises(ImmutableRecordError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_whatsapp_grokbot_rbac_and_industrial_api(
    client: AsyncClient, db_session: AsyncSession, tenant_context: TenantContext
):
    """Validates WhatsApp/GrokBot RBAC enforcement and FastAPI industrial dashboard & REST endpoints."""
    # 1. Operator without 'account:approve_invoice' attempts privileged tool via WhatsApp bot -> raises RBACPermissionDeniedError
    operator_ctx = TenantContext(
        tenant_id=tenant_context.tenant_id,
        branch_id=tenant_context.branch_id,
        user_id=tenant_context.user_id,
        roles=["OPERADOR_PLANTA"],
        permissions=["mrp:view_work_centers"],
    )

    with pytest.raises(RBACPermissionDeniedError):
        await BotOrchestratorService.handle_whatsapp_command(
            db_session,
            operator_ctx,
            WhatsAppWebhookPayload(
                from_phone="+5216671234567",
                message_text="Aprobar factura FAC-PROV-1000-OK",
                requested_tool="account:approve_invoice",
                tool_args={"invoice_number": "FAC-PROV-1000-OK"},
            ),
        )

    # 2. Allowed tool execution via WhatsApp Bot succeeds
    bot_res = await BotOrchestratorService.handle_whatsapp_command(
        db_session,
        operator_ctx,
        WhatsAppWebhookPayload(
            from_phone="+5216671234567",
            message_text="Consultar estado de centros de trabajo",
            requested_tool="mrp:view_work_centers",
            tool_args={},
        ),
    )
    assert bot_res["status"] == "EXECUTED"

    # 3. Verify HTTP endpoints (/health, /, and /api/v1/summary)
    health_resp = await client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    dashboard_resp = await client.get("/")
    assert dashboard_resp.status_code == 200
    assert "ERPmini" in dashboard_resp.text

    summary_resp = await client.get("/api/v1/summary")
    assert summary_resp.status_code == 200
    data = summary_resp.json()
    assert "modules" in data
    assert len(data["modules"]) == 8
