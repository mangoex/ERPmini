import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DomainValidationError,
    ImmutableRecordError,
    RBACPermissionDeniedError,
)
from app.core.security import TenantContext
from app.core.uuid7 import ensure_uuid7, generate_uuid7
from app.modules.inventory.models import (
    InventoryProduct,
    InventoryStockMove,
    InventoryStockPlace,
)
from app.modules.system.models import SystemAuditLog
from app.modules.system.service import AuditService, OutboxService, RBACService


@pytest.mark.asyncio
async def test_uuid7_monotonicity_and_uuid4_rejection():
    """Validates that UUIDv7 is strictly monotonic and UUIDv4 is rejected with DomainValidationError."""
    generated = [generate_uuid7() for _ in range(100)]
    for u in generated:
        assert u.version == 7
        assert ensure_uuid7(u) == u

    # Check strictly increasing lexicographical/byte order
    assert generated == sorted(generated)
    assert len(set(generated)) == 100

    # Reject UUIDv4
    bad_uuid = uuid.uuid4()
    with pytest.raises(DomainValidationError):
        ensure_uuid7(bad_uuid)


@pytest.mark.asyncio
async def test_audit_log_immutability_and_transactional_outbox(
    db_session: AsyncSession, tenant_context: TenantContext
):
    """Validates atomic creation of audit logs and outbox events, and prevents UPDATE/DELETE on audit logs."""
    entity_id = generate_uuid7()

    audit_entry = await AuditService.log_change(
        session=db_session,
        ctx=tenant_context,
        entity_name="inventory_products",
        entity_id=entity_id,
        action="CREATE",
        previous_value=None,
        new_value={"sku": "HDPE-VIRGEN-01", "uom": "KG"},
    )
    outbox_event = await OutboxService.publish(
        session=db_session,
        ctx=tenant_context,
        event_type="product.created",
        aggregate_type="inventory_products",
        aggregate_id=entity_id,
        payload={"sku": "HDPE-VIRGEN-01"},
    )
    await db_session.commit()

    assert audit_entry.id.version == 7
    assert outbox_event.status == "PENDING"

    # Attempt to mutate audit log -> must raise ImmutableRecordError
    audit_entry.action = "TAMPERED"
    with pytest.raises(ImmutableRecordError):
        await db_session.commit()
    await db_session.rollback()

    # Reload and attempt to delete audit log -> must raise ImmutableRecordError
    persisted_audit = await db_session.get(SystemAuditLog, audit_entry.id)
    assert persisted_audit is not None
    await db_session.delete(persisted_audit)
    with pytest.raises(ImmutableRecordError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_rbac_permission_enforcement(tenant_context: TenantContext):
    """Validates deterministic RBAC permission checks."""
    restricted_ctx = TenantContext(
        tenant_id=tenant_context.tenant_id,
        branch_id=tenant_context.branch_id,
        user_id=tenant_context.user_id,
        roles=["OPERADOR_BASCULA"],
        permissions=["purchase:create_grn"],
    )

    # Allowed permission passes
    RBACService.check_permission(restricted_ctx, "purchase:create_grn")

    # Forbidden permission raises RBACPermissionDeniedError
    with pytest.raises(RBACPermissionDeniedError):
        RBACService.check_permission(restricted_ctx, "account:approve_invoice")


@pytest.mark.asyncio
async def test_on_delete_restrict_foreign_key(
    db_session: AsyncSession, tenant_context: TenantContext
):
    """Validates that ON DELETE RESTRICT prevents deleting referenced master records."""
    loc_src = InventoryStockPlace(
        id=generate_uuid7(),
        tenant_id=tenant_context.tenant_id,
        branch_id=tenant_context.branch_id,
        code="LOC-VENDOR-TEST",
        name="Proveedor Resina",
        place_type="VENDOR",
    )
    loc_dst = InventoryStockPlace(
        id=generate_uuid7(),
        tenant_id=tenant_context.tenant_id,
        branch_id=tenant_context.branch_id,
        code="LOC-SILO-TEST",
        name="Silo 1",
        place_type="INTERNAL",
    )
    product = InventoryProduct(
        id=generate_uuid7(),
        tenant_id=tenant_context.tenant_id,
        branch_id=tenant_context.branch_id,
        sku="RESIN-TEST-FK",
        name="Resina FK Test",
        category="RAW_RESIN",
        uom="KG",
        weight_kg=1.0,
        min_stock=100.0,
        standard_cost=25.0,
    )
    db_session.add_all([loc_src, loc_dst, product])
    await db_session.flush()

    move = InventoryStockMove(
        id=generate_uuid7(),
        tenant_id=tenant_context.tenant_id,
        branch_id=tenant_context.branch_id,
        product_id=product.id,
        source_place_id=loc_src.id,
        dest_place_id=loc_dst.id,
        qty=50.0,
        uom="KG",
        unit_cost=25.0,
        reference="INIT-LOAD",
        status="DONE",
    )
    db_session.add(move)
    await db_session.commit()

    # Attempt to delete product referenced by stock move -> must fail due to ON DELETE RESTRICT
    await db_session.delete(product)
    with pytest.raises((IntegrityError, ImmutableRecordError)):
        await db_session.commit()
    await db_session.rollback()
