"""Small display contracts for a traveller's invoices."""

from pydantic import BaseModel, Field


class InvoiceLine(BaseModel):
    label: str
    qty: int
    total_mnt: int


class InvoiceView(BaseModel):
    id: str
    trip_id: str
    trip_title: str
    checkout_id: str | None = None
    reference: str
    amount_mnt: int
    status: str
    provider: str
    paid_at: str | None = None
    lines: list[InvoiceLine] = Field(default_factory=list)
