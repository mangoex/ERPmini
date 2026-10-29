"""Servicio público del módulo account: Contabilidad, 3-Way Match y Libro Mayor."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ThreeWayMatchError, UnbalancedJournalError
from app.core.security import TenantContext
from app.core.uuid7 import generate_uuid7
from app.modules.account.models import (
    AccountAccount,
    AccountGLEntry,
    AccountVendorBill,
    AccountVendorBillLine,
)
from app.modules.account.schemas import (
    AccountCreate,
    JournalEntryCreate,
    VendorBillCreate,
)
from app.modules.purchase.service import PurchaseService


class AccountService:
    """Contrato público de contabilidad general y auditoría financiera."""

    @staticmethod
    async def create_account(
        session: AsyncSession,
        ctx: TenantContext,
        data: AccountCreate,
    ) -> AccountAccount:
        acc = AccountAccount(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            code=data.code,
            name=data.name,
            account_type=data.account_type,
        )
        session.add(acc)
        await session.flush()
        return acc

    @staticmethod
    async def get_account(
        session: AsyncSession,
        ctx: TenantContext,
        account_id: uuid.UUID,
    ) -> AccountAccount | None:
        query = select(AccountAccount).where(
            AccountAccount.id == account_id,
            AccountAccount.tenant_id == ctx.tenant_id,
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def create_and_validate_vendor_bill(
        session: AsyncSession,
        ctx: TenantContext,
        data: VendorBillCreate,
    ) -> AccountVendorBill:
        """Valida Coincidencia de 3 Vías (PO vs GRN de Báscula vs Factura) y postea póliza contable balanceada."""
        po = await PurchaseService.get_purchase_order(
            session, ctx, data.purchase_order_id
        )
        if not po:
            raise ThreeWayMatchError(
                f"Purchase order {data.purchase_order_id} not found"
            )

        grn = await PurchaseService.get_goods_receipt(session, ctx, data.grn_id)
        if not grn:
            raise ThreeWayMatchError(f"Goods receipt {data.grn_id} not found")

        po_lines_by_prod = {line.product_id: line for line in po.lines}
        grn_lines_by_prod = {line.product_id: line for line in grn.lines}

        for bill_line in data.lines:
            grn_line = grn_lines_by_prod.get(bill_line.product_id)
            if (
                not grn_line
                or abs(bill_line.qty_billed - grn_line.qty_received_kg) > 1e-4
            ):
                received_qty = grn_line.qty_received_kg if grn_line else 0.0
                raise ThreeWayMatchError(
                    f"3-Way Match discrepancy for product {bill_line.product_id}: "
                    f"billed {bill_line.qty_billed} kg vs received at scale {received_qty} kg"
                )

            po_line = po_lines_by_prod.get(bill_line.product_id)
            if not po_line or abs(bill_line.unit_price - po_line.unit_price) > 1e-4:
                ordered_price = po_line.unit_price if po_line else 0.0
                raise ThreeWayMatchError(
                    f"3-Way Match price discrepancy for product {bill_line.product_id}: "
                    f"billed {bill_line.unit_price} MXN vs PO price {ordered_price} MXN"
                )

        total_amount = sum(l.qty_billed * l.unit_price for l in data.lines)

        bill = AccountVendorBill(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            supplier_id=data.supplier_id,
            purchase_order_id=data.purchase_order_id,
            grn_id=data.grn_id,
            invoice_number=data.invoice_number,
            debit_account_id=data.debit_account_id,
            credit_account_id=data.credit_account_id,
            total_amount=total_amount,
            status="POSTED",
        )
        for line_data in data.lines:
            b_line = AccountVendorBillLine(
                id=generate_uuid7(),
                bill_id=bill.id,
                product_id=line_data.product_id,
                qty_billed=line_data.qty_billed,
                unit_price=line_data.unit_price,
            )
            bill.lines.append(b_line)

        session.add(bill)

        # Generar póliza de diario con partida doble exacta
        debit_entry = AccountGLEntry(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            account_id=data.debit_account_id,
            reference=data.invoice_number,
            debit=total_amount,
            credit=0.0,
        )
        credit_entry = AccountGLEntry(
            id=generate_uuid7(),
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            account_id=data.credit_account_id,
            reference=data.invoice_number,
            debit=0.0,
            credit=total_amount,
        )
        session.add_all([debit_entry, credit_entry])
        await session.flush()
        return bill

    @staticmethod
    async def post_journal_entry(
        session: AsyncSession,
        ctx: TenantContext,
        data: JournalEntryCreate,
    ) -> list[AccountGLEntry]:
        """Postea un asiento en el libro mayor validando invariante de partida doble Debe == Haber."""
        sum_debit = sum(line.debit for line in data.lines)
        sum_credit = sum(line.credit for line in data.lines)

        if abs(sum_debit - sum_credit) > 1e-4:
            raise UnbalancedJournalError(
                f"Double-entry violation in journal entry '{data.reference}': "
                f"total debit ({sum_debit:.2f}) != total credit ({sum_credit:.2f})"
            )

        entries = []
        for line in data.lines:
            entry = AccountGLEntry(
                id=generate_uuid7(),
                tenant_id=ctx.tenant_id,
                branch_id=ctx.branch_id,
                account_id=line.account_id,
                reference=data.reference,
                debit=line.debit,
                credit=line.credit,
            )
            session.add(entry)
            entries.append(entry)

        await session.flush()
        return entries

    @staticmethod
    async def get_gl_entries_by_reference(
        session: AsyncSession,
        ctx: TenantContext,
        reference: str,
    ) -> list[AccountGLEntry]:
        query = select(AccountGLEntry).where(
            AccountGLEntry.tenant_id == ctx.tenant_id,
            AccountGLEntry.reference == reference,
        )
        result = await session.execute(query)
        return list(result.scalars().all())
