"""Esquemas Pydantic para el módulo account."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class AccountCreate(BaseModel):
    code: str
    name: str
    account_type: str  # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE


class AccountResponse(AccountCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None


class VendorBillLineCreate(BaseModel):
    product_id: uuid.UUID
    qty_billed: float
    unit_price: float


class VendorBillLineResponse(VendorBillLineCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bill_id: uuid.UUID


class VendorBillCreate(BaseModel):
    supplier_id: uuid.UUID
    purchase_order_id: uuid.UUID
    grn_id: uuid.UUID
    invoice_number: str
    debit_account_id: uuid.UUID
    credit_account_id: uuid.UUID
    lines: list[VendorBillLineCreate]


class VendorBillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    supplier_id: uuid.UUID
    purchase_order_id: uuid.UUID
    grn_id: uuid.UUID
    invoice_number: str
    debit_account_id: uuid.UUID
    credit_account_id: uuid.UUID
    total_amount: float
    status: str
    created_at: datetime.datetime
    lines: list[VendorBillLineResponse] = []


class JournalLineCreate(BaseModel):
    account_id: uuid.UUID
    debit: float = 0.0
    credit: float = 0.0


class JournalEntryCreate(BaseModel):
    reference: str
    lines: list[JournalLineCreate]


class GLEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    account_id: uuid.UUID
    reference: str
    debit: float
    credit: float
    created_at: datetime.datetime
