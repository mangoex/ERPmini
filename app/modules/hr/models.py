"""Modelos del módulo hr: Departamentos, Puestos, Empleados, Compensación y Nómina."""

import datetime
import uuid

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.uuid7 import generate_uuid7


class HRDepartment(Base):
    """Departamentos de la planta (Soplado, Inyección, Mantenimiento, Almacén, etc.)."""

    __tablename__ = "hr_departments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class HRJobTitle(Base):
    """Puestos y categorías de mano de obra industrial."""

    __tablename__ = "hr_job_titles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)


class HREmployee(Base):
    """Maestro de empleados."""

    __tablename__ = "hr_employees"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    employee_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    whatsapp_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("hr_departments.id", ondelete="RESTRICT"), nullable=False
    )
    job_title_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("hr_job_titles.id", ondelete="RESTRICT"), nullable=False
    )


class HRCompensationRecord(Base):
    """Historial inmutable de salarios con Effective-Dating."""

    __tablename__ = "hr_compensation_records"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("hr_employees.id", ondelete="RESTRICT"), nullable=False
    )
    daily_wage: Mapped[float] = mapped_column(Float, nullable=False)
    effective_from: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)


class HRBiometricPunch(Base):
    """Checadas biométricas de torniquete para 3 turnos rotativos 24/7."""

    __tablename__ = "hr_biometric_punches"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("hr_employees.id", ondelete="RESTRICT"), nullable=False
    )
    shift: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # MATUTINO, VESPERTINO, NOCTURNO
    punch_in: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    punch_out: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    device_id: Mapped[str] = mapped_column(String(50), nullable=False)


class HRPayRun(Base):
    """Corrida de nómina semanal o quincenal."""

    __tablename__ = "hr_pay_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    period_code: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )

    paychecks: Mapped[list["HRPaycheck"]] = relationship(
        "HRPaycheck",
        back_populates="pay_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class HRPaycheck(Base):
    """Recibo de nómina individual congelado e inmutable tras aprobación."""

    __tablename__ = "hr_paychecks"
    __immutable__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    pay_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("hr_pay_runs.id", ondelete="RESTRICT"), nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("hr_employees.id", ondelete="RESTRICT"), nullable=False
    )
    gross_amount: Mapped[float] = mapped_column(Float, nullable=False)
    net_amount: Mapped[float] = mapped_column(Float, nullable=False)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    pay_run: Mapped["HRPayRun"] = relationship("HRPayRun", back_populates="paychecks")
