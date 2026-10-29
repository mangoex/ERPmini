"""Modelos del módulo sales: Clientes, CRM y Órdenes de Venta."""

import datetime
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.uuid7 import generate_uuid7


class SalesCustomer(Base):
    """Clientes agroindustriales y empaques."""

    __tablename__ = "sales_customers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    tax_id: Mapped[str] = mapped_column(String(50), nullable=False)
    credit_limit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class CRMLead(Base):
    """Oportunidades comerciales y cotizaciones tempranas."""

    __tablename__ = "crm_leads"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sales_customers.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default="NEW", nullable=False)


class SalesOrder(Base):
    """Orden de venta comercial formal."""

    __tablename__ = "sales_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sales_customers.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_place_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )

    lines: Mapped[list["SalesOrderLine"]] = relationship(
        "SalesOrderLine",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SalesOrderLine(Base):
    """Partidas de orden de venta."""

    __tablename__ = "sales_order_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    sales_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sales_orders.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)

    order: Mapped["SalesOrder"] = relationship("SalesOrder", back_populates="lines")
