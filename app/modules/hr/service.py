"""Servicio público del módulo hr: Recursos Humanos, Effective-Dating y Nómina."""

import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TenantContext
from app.core.uuid7 import generate_uuid7
from app.modules.hr.models import (
    HRBiometricPunch,
    HRCompensationRecord,
    HRDepartment,
    HREmployee,
    HRJobTitle,
    HRPaycheck,
    HRPayRun,
)
from app.modules.hr.schemas import (
    BiometricPunchCreate,
    CompensationUpdate,
    DepartmentCreate,
    EmployeeCreate,
    JobTitleCreate,
    PayRunCreate,
)


class HRService:
    """Contrato público de capital humano y nómina congelada."""

    @staticmethod
    async def create_department(
        session: AsyncSession,
        ctx: TenantContext,
        data: DepartmentCreate,
    ) -> HRDepartment:
        dept = HRDepartment(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            code=data.code,
            name=data.name,
        )
        session.add(dept)
        await session.flush()
        return dept

    @staticmethod
    async def create_job_title(
        session: AsyncSession,
        ctx: TenantContext,
        data: JobTitleCreate,
    ) -> HRJobTitle:
        job = HRJobTitle(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            code=data.code,
            title=data.title,
        )
        session.add(job)
        await session.flush()
        return job

    @staticmethod
    async def create_employee(
        session: AsyncSession,
        ctx: TenantContext,
        data: EmployeeCreate,
    ) -> HREmployee:
        emp = HREmployee(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            employee_number=data.employee_number,
            full_name=data.full_name,
            whatsapp_phone=data.whatsapp_phone,
            department_id=data.department_id,
            job_title_id=data.job_title_id,
        )
        session.add(emp)
        await session.flush()

        comp = HRCompensationRecord(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            employee_id=emp.id,
            daily_wage=data.daily_wage,
            effective_from=data.effective_from,
            effective_to=None,
            reason="Contratación inicial",
        )
        session.add(comp)
        await session.flush()
        return emp

    @staticmethod
    async def update_compensation_effective_dated(
        session: AsyncSession,
        ctx: TenantContext,
        data: CompensationUpdate,
    ) -> HRCompensationRecord:
        """Actualiza el salario cerrando el registro previo sin sobrescribir el pasado histórico."""
        query = (
            select(HRCompensationRecord)
            .where(
                HRCompensationRecord.tenant_id == ctx.tenant_id,
                HRCompensationRecord.employee_id == data.employee_id,
                HRCompensationRecord.effective_to.is_(None),
            )
            .order_by(HRCompensationRecord.effective_from.desc())
        )
        result = await session.execute(query)
        current_comp = result.scalars().first()

        if current_comp:
            # Cierra el registro previo el día anterior a la nueva fecha de efectividad
            current_comp.effective_to = data.effective_from - datetime.timedelta(days=1)

        new_comp = HRCompensationRecord(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            employee_id=data.employee_id,
            daily_wage=data.new_daily_wage,
            effective_from=data.effective_from,
            effective_to=None,
            reason=data.reason,
        )
        session.add(new_comp)
        await session.flush()
        return new_comp

    @staticmethod
    async def get_compensation_history(
        session: AsyncSession,
        ctx: TenantContext,
        employee_id: uuid.UUID,
    ) -> list[HRCompensationRecord]:
        query = (
            select(HRCompensationRecord)
            .where(
                HRCompensationRecord.tenant_id == ctx.tenant_id,
                HRCompensationRecord.employee_id == employee_id,
            )
            .order_by(HRCompensationRecord.effective_from.asc())
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def record_biometric_punch(
        session: AsyncSession,
        ctx: TenantContext,
        data: BiometricPunchCreate,
    ) -> HRBiometricPunch:
        punch = HRBiometricPunch(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            employee_id=data.employee_id,
            shift=data.shift,
            punch_in=data.punch_in,
            punch_out=data.punch_out,
            device_id=data.device_id,
        )
        session.add(punch)
        await session.flush()
        return punch

    @staticmethod
    async def create_and_approve_pay_run(
        session: AsyncSession,
        ctx: TenantContext,
        data: PayRunCreate,
    ) -> HRPayRun:
        """Calcula nómina para todos los empleados activos y congela los recibos de forma inmutable."""
        pay_run = HRPayRun(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            period_code=data.period_code,
            start_date=data.start_date,
            end_date=data.end_date,
            status="APPROVED",
        )
        session.add(pay_run)

        # Buscar todos los empleados del tenant
        emp_query = select(HREmployee).where(HREmployee.tenant_id == ctx.tenant_id)
        emp_res = await session.execute(emp_query)
        employees = list(emp_res.scalars().all())

        for emp in employees:
            # Buscar el salario vigente durante el periodo de nómina
            comp_query = (
                select(HRCompensationRecord)
                .where(
                    HRCompensationRecord.tenant_id == ctx.tenant_id,
                    HRCompensationRecord.employee_id == emp.id,
                    HRCompensationRecord.effective_from <= data.end_date,
                )
                .order_by(HRCompensationRecord.effective_from.desc())
            )
            comp_res = await session.execute(comp_query)
            comp = comp_res.scalars().first()

            daily_wage = comp.daily_wage if comp else 0.0
            gross = daily_wage * data.days_worked

            paycheck = HRPaycheck(
                id=generate_uuid7(),
                tenant_id=ctx.tenant_id,
                branch_id=ctx.branch_id,
                pay_run_id=pay_run.id,
                employee_id=emp.id,
                gross_amount=gross,
                net_amount=gross,
                is_frozen=True,
            )
            pay_run.paychecks.append(paycheck)

        await session.flush()
        return pay_run
