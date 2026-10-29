"""Esquemas Pydantic para el módulo hr."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class DepartmentCreate(BaseModel):
    code: str
    name: str


class DepartmentResponse(DepartmentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None


class JobTitleCreate(BaseModel):
    code: str
    title: str


class JobTitleResponse(JobTitleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None


class EmployeeCreate(BaseModel):
    employee_number: str
    full_name: str
    whatsapp_phone: str
    department_id: uuid.UUID
    job_title_id: uuid.UUID
    daily_wage: float
    effective_from: datetime.date


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    employee_number: str
    full_name: str
    whatsapp_phone: str
    department_id: uuid.UUID
    job_title_id: uuid.UUID


class CompensationUpdate(BaseModel):
    employee_id: uuid.UUID
    new_daily_wage: float
    effective_from: datetime.date
    reason: str | None = None


class CompensationRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    employee_id: uuid.UUID
    daily_wage: float
    effective_from: datetime.date
    effective_to: datetime.date | None = None
    reason: str | None = None


class BiometricPunchCreate(BaseModel):
    employee_id: uuid.UUID
    shift: str  # MATUTINO, VESPERTINO, NOCTURNO
    punch_in: datetime.datetime
    punch_out: datetime.datetime | None = None
    device_id: str


class BiometricPunchResponse(BiometricPunchCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None


class PaycheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    pay_run_id: uuid.UUID
    employee_id: uuid.UUID
    gross_amount: float
    net_amount: float
    is_frozen: bool


class PayRunCreate(BaseModel):
    period_code: str
    start_date: datetime.date
    end_date: datetime.date
    days_worked: int = 7


class PayRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    period_code: str
    start_date: datetime.date
    end_date: datetime.date
    status: str
    created_at: datetime.datetime
    paychecks: list[PaycheckResponse] = []
