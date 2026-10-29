"""Modelos del módulo mrp: Centros de Trabajo, Estructuras BOM, Órdenes de Producción y Molienda."""

import datetime
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.uuid7 import generate_uuid7


class MRPWorkCenter(Base):
    """Centros de trabajo industriales (Sopladoras, Inyectoras, Molinos)."""

    __tablename__ = "mrp_work_centers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    center_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # INJECTION_MOLDER, BLOW_MOLDER, GRANULATOR_MILL
    mold_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cavities: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    cycle_time_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class MRPBOMStructure(Base):
    """Lista de materiales con ratio de rebaba recuperable."""

    __tablename__ = "mrp_bom_structures"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    parent_product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, index=True, nullable=False
    )
    child_product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, index=True, nullable=False
    )
    qty_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    scrap_return_ratio: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    scrap_product_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class MRPProductionOrder(Base):
    """Orden de producción que consume resinas/pigmentos y genera cajas y rebaba."""

    __tablename__ = "mrp_production_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    work_center_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("mrp_work_centers.id", ondelete="RESTRICT"), nullable=True
    )
    qty_planned: Mapped[float] = mapped_column(Float, nullable=False)
    qty_produced: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    scrap_generated_kg: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    source_place_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    finished_dest_place_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    scrap_dest_place_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )


class MRPUnbuildOrder(Base):
    """Orden de molienda / reciclaje que transforma rebaba en regrind con balance de masa."""

    __tablename__ = "mrp_unbuild_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    work_center_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("mrp_work_centers.id", ondelete="RESTRICT"), nullable=False
    )
    scrap_product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    regrind_product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_scrap_place_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    dest_regrind_place_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    input_qty_kg: Mapped[float] = mapped_column(Float, nullable=False)
    output_regrind_qty_kg: Mapped[float] = mapped_column(Float, nullable=False)
    process_loss_kg: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DONE", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )
