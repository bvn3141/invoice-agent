"""Pydantic models for invoice records and validation outcomes.

These are the internal types we keep in our own code — separate from the
JSON-via-MCP tool I/O. The tool layer hands dicts back and forth with Claude;
when we persist data to Excel or review folders, we normalize through these
models so the on-disk shape is consistent.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


ReviewReasonType = Literal[
    "duplicate",
    "math_error",
    "unknown_vendor",
    "currency_mismatch",
    "extraction_failed",
    "other",
]


class LineItem(BaseModel):
    description: str
    qty: float
    unit_price: float
    line_total: float


class Invoice(BaseModel):
    """Canonical invoice shape. Used for Excel rows and review payloads."""

    filename: str
    invoice_no: str
    vendor_name: str
    vendor_id: str | None = None
    invoice_date: date
    due_date: date | None = None
    currency: str
    netto: float
    ust: float
    brutto: float
    ust_rate: float = 0.0
    category: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)


class ReviewReason(BaseModel):
    type: ReviewReasonType
    explanation: str
    field: str | None = None
