"""Modelos del módulo account: Cuentas, Facturas 3-Way Match y Libro Mayor."""

import datetime
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.uuid7 import generate_uuid7


class AccountAccount(Base):
    """Catálogo contable / Plan de cuentas."""

    __tablename__ = "account_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE


class AccountVendorBill(Base):
    """Factura de proveedor validada por 3-Way Match."""

    __tablename__ = "account_vendor_bills"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    grn_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    debit_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("account_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    credit_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("account_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    total_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )

    lines: Mapped[list["AccountVendorBillLine"]] = relationship(
        "AccountVendorBillLine",
        back_populates="bill",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AccountVendorBillLine(Base):
    """Líneas facturadas por el proveedor."""

    __tablename__ = "account_vendor_bill_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("account_vendor_bills.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    qty_billed: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)

    bill: Mapped["AccountVendorBill"] = relationship(
        "AccountVendorBill", back_populates="lines"
    )


class AccountGLEntry(Base):
    """Asiento de Libro Mayor General inmutable con partida doble estricta."""

    __tablename__ = "account_gl_entries"
    __immutable__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("account_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    reference: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    debit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    credit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )
