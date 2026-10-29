"""Rutas REST para el módulo account."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import TenantContext, get_tenant_context
from app.modules.account.models import AccountAccount, AccountGLEntry, AccountVendorBill
from app.modules.account.schemas import (
    AccountCreate,
    AccountResponse,
    GLEntryResponse,
    JournalEntryCreate,
    VendorBillCreate,
    VendorBillResponse,
)
from app.modules.account.service import AccountService

router = APIRouter(prefix="/api/v1/account", tags=["Account & GL"])


@router.post("/accounts", response_model=AccountResponse)
async def create_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    acc = await AccountService.create_account(db, ctx, data)
    await db.commit()
    return acc


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = select(AccountAccount).where(AccountAccount.tenant_id == ctx.tenant_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/vendor-bills", response_model=VendorBillResponse)
async def create_vendor_bill(
    data: VendorBillCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    bill = await AccountService.create_and_validate_vendor_bill(db, ctx, data)
    await db.commit()
    return bill


@router.get("/vendor-bills", response_model=list[VendorBillResponse])
async def list_vendor_bills(
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    query = (
        select(AccountVendorBill)
        .where(AccountVendorBill.tenant_id == ctx.tenant_id)
        .order_by(AccountVendorBill.created_at.desc())
        .limit(100)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/journal-entries", response_model=list[GLEntryResponse])
async def post_journal_entry(
    data: JournalEntryCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    entries = await AccountService.post_journal_entry(db, ctx, data)
    await db.commit()
    return entries


@router.get("/gl-entries", response_model=list[GLEntryResponse])
async def list_gl_entries(
    reference: str | None = None,
    db: AsyncSession = Depends(get_db_session),
    ctx: TenantContext = Depends(get_tenant_context),
):
    if reference:
        return await AccountService.get_gl_entries_by_reference(db, ctx, reference)
    query = (
        select(AccountGLEntry)
        .where(AccountGLEntry.tenant_id == ctx.tenant_id)
        .order_by(AccountGLEntry.created_at.desc())
        .limit(100)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
