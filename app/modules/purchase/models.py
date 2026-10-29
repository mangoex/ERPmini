"""Modelos del módulo purchase: Proveedores, Órdenes de Compra y Recepción en Báscula."""

import datetime
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.uuid7 import generate_uuid7


class PurchaseSupplier(Base):
    """Catálogo de proveedores de resina, pigmentos y consumibles."""

    __tablename__ = "purchase_suppliers"

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


class PurchaseOrder(Base):
    """Orden de compra formal."""

    __tablename__ = "purchase_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("purchase_suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )

    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PurchaseOrderLine(Base):
    """Partidas de orden de compra."""

    __tablename__ = "purchase_order_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    qty_ordered: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)

    order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder", back_populates="lines"
    )


class PurchaseGoodsReceiptNote(Base):
    """Recepción de mercancía en báscula industrial (GRN)."""

    __tablename__ = "purchase_goods_receipt_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False
    )
    scale_ticket_number: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    gross_weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    tare_weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    net_weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    source_place_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    dest_place_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    lot_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DONE", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )

    lines: Mapped[list["PurchaseGoodsReceiptLine"]] = relationship(
        "PurchaseGoodsReceiptLine",
        back_populates="grn",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PurchaseGoodsReceiptLine(Base):
    """Líneas de pesaje y recepción efectiva."""

    __tablename__ = "purchase_goods_receipt_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    grn_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("purchase_goods_receipt_notes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    po_line_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    qty_received_kg: Mapped[float] = mapped_column(Float, nullable=False)

    grn: Mapped["PurchaseGoodsReceiptNote"] = relationship(
        "PurchaseGoodsReceiptNote", back_populates="lines"
    )
