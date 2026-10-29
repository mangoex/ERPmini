"""Modelos del módulo inventory: Ubicaciones, Productos, Lotes y Movimientos."""

import datetime
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.uuid7 import generate_uuid7


class InventoryStockPlace(Base):
    """Ubicación de stock (almacenes, silos, líneas, proveedores, clientes)."""

    __tablename__ = "inventory_stock_places"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    place_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # INTERNAL, VENDOR, CUSTOMER, SCRAP, PRODUCTION


class InventoryProduct(Base):
    """Catálogo maestro de productos plásticos y agrícolas."""

    __tablename__ = "inventory_products"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    sku: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # RAW_RESIN, REGRIND, MASTERBATCH_UV, FINISHED_CRATE, SCRAP_FLASH
    uom: Mapped[str] = mapped_column(String(20), nullable=False)  # KG, PCS
    weight_kg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    min_stock: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    standard_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class InventoryStockLot(Base):
    """Lote de trazabilidad de materia prima o lote de producción."""

    __tablename__ = "inventory_stock_lots"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    lot_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("inventory_products.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )


class InventoryStockMove(Base):
    """Libro mayor de inventario inmutable por doble entrada."""

    __tablename__ = "inventory_stock_moves"
    __immutable__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("inventory_products.id", ondelete="RESTRICT"), nullable=False
    )
    source_place_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_stock_places.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dest_place_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_stock_places.id", ondelete="RESTRICT"),
        nullable=False,
    )
    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("inventory_stock_lots.id", ondelete="RESTRICT"), nullable=True
    )
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DONE", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )
