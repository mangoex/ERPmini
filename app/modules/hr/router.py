"""Rutas REST para el módulo hr."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import TenantContext, get_tenant_context
from app.modules.hr.models import (
    HRBiometricPunch,
    HRDepartment,
    HREmployee,
    HRJobTitle,
    HRPayRun,
)
from app.modules.hr.schemas import (
    BiometricPunchCreate,
    BiometricPunchResponse,
    CompensationRecordResponse,
    CompensationUpdate,
    DepartmentCreate,
    DepartmentResponse,
    EmployeeCreate,
    EmployeeResponse,
    JobTitleCreate,
    JobTitleResponse,
    PayRunCreate,
    PayRunResponse,
)
from app.modules.hr.service import HRService

router = APIRouter(prefix="/api/v1/hr", tags=["HR & Biometric"])


@router.post("/departments", response_model=DepartmentResponse)
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    dept = await HRService.create_department(db, ctx, data)
    await db.commit()
    return dept


@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = select(HRDepartment).where(HRDepartment.tenant_id == ctx.tenant_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/job-titles", response_model=JobTitleResponse)
async def create_job_title(
    data: JobTitleCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    job = await HRService.create_job_title(db, ctx, data)
    await db.commit()
    return job


@router.get("/job-titles", response_model=list[JobTitleResponse])
async def list_job_titles(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = select(HRJobTitle).where(HRJobTitle.tenant_id == ctx.tenant_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/employees", response_model=EmployeeResponse)
async def create_employee(
    data: EmployeeCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    emp = await HRService.create_employee(db, ctx, data)
    await db.commit()
    return emp


@router.get("/employees", response_model=list[EmployeeResponse])
async def list_employees(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = select(HREmployee).where(HREmployee.tenant_id == ctx.tenant_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/compensations", response_model=CompensationRecordResponse)
async def update_compensation(
    data: CompensationUpdate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    comp = await HRService.update_compensation_effective_dated(db, ctx, data)
    await db.commit()
    return comp


@router.get(
    "/compensations/{employee_id}", response_model=list[CompensationRecordResponse]
)
async def get_compensation_history(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    return await HRService.get_compensation_history(db, ctx, employee_id)


@router.post("/biometric/punches", response_model=BiometricPunchResponse)
async def record_punch(
    data: BiometricPunchCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    punch = await HRService.record_biometric_punch(db, ctx, data)
    await db.commit()
    return punch


@router.get("/biometric/punches", response_model=list[BiometricPunchResponse])
async def list_punches(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = (
        select(HRBiometricPunch)
        .where(HRBiometricPunch.tenant_id == ctx.tenant_id)
        .order_by(HRBiometricPunch.punch_in.desc())
        .limit(100)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/pay-runs", response_model=PayRunResponse)
async def create_pay_run(
    data: PayRunCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    pay_run = await HRService.create_and_approve_pay_run(db, ctx, data)
    await db.commit()
    return pay_run


@router.get("/pay-runs", response_model=list[PayRunResponse])
async def list_pay_runs(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = (
        select(HRPayRun)
        .where(HRPayRun.tenant_id == ctx.tenant_id)
        .order_by(HRPayRun.created_at.desc())
        .limit(50)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
