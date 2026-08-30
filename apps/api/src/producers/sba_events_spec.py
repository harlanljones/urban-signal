"""``SbaLoanEvent`` field set as leaf data (US-378)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

SBA_TOPIC = "raw.sba.loans"
SBA_DATASET_PAGE = "https://data.sba.gov/dataset/7a-504-foia"
SBA_PROGRAM_504 = "504"
SBA_PROGRAM_7A = "7a"
SBA_PROGRAMS = (SBA_PROGRAM_504, SBA_PROGRAM_7A)
SBA_FIXED_ASSET = {SBA_PROGRAM_7A: False, SBA_PROGRAM_504: True}
SBA_STATUS_MAP = {"PIF": "pif", "P I F": "pif", "CHGOFF": "chgoff", "EXEMPT": "exempt", "CANCLD": "cancld"}


def normalize_location_id(raw: Any) -> str | None:
    if not raw:
        return None
    try:
        return str(int(float(str(raw).strip())))
    except (ValueError, TypeError):
        return None


def normalize_program(raw: Any) -> str | None:
    text = str(raw or "").strip().lower()
    if "504" in text:
        return SBA_PROGRAM_504
    if "7a" in text:
        return SBA_PROGRAM_7A
    return None


def normalize_status(raw: Any) -> str | None:
    text = str(raw or "").strip().upper()
    return SBA_STATUS_MAP.get(text, text or None)


def naics_sector_of(row: dict[str, Any]) -> int | None:
    """Extract the 2-digit NAICS sector from the row's NAICS code."""
    for col in ("naics", "naicscode", "naics_code", "primarynaics"):
        raw = row.get(col)
        if raw:
            try:
                code = str(int(float(str(raw).strip())))[:2]
                if code.isdigit() and len(code) == 2:
                    return int(code)
            except (ValueError, TypeError):
                pass
    return None


class SbaLoanEvent(BaseModel):
    """An SBA 7(a) or 504 loan approval (US-378).

    Every row in the cumulative FOIA file is inventory. The watermark is the
    file as-of date; there is no per-row watermark. Status repeats across
    program runs for the same LocationID (a 504 PIF and a 7a CHGOFF are
    separate events sharing the borrower address).

    The borrower address is SBA-truncated (up to 49 chars, ending with a
    literal ``.``), so the geocode contract is street-first with a zip+city
    fallback; 504 rows additionally carry ``project_county`` for county-join
    downstream.
    """

    city_id: str = Field(default="national")
    program: str = Field(..., description="504 | 7a")
    location_id: str = Field(..., description="SBA LocationID, float-string normalized to integer digits")
    approval_date: datetime | None = Field(default=None, description="ApprovalDate")
    gross_approval: float | None = Field(default=None, ge=0.0)
    sba_guaranteed_approval: float | None = Field(default=None, ge=0.0)
    naics_sector: int | None = Field(default=None, ge=0, le=99)
    fixed_asset: bool = Field(default=False, description="504 = True (real estate/machinery), 7a = False (working capital)")
    status: str | None = Field(default=None, description="pif | chgoff | exempt | cancld | raw text")
    borrower_name: str | None = None
    borrower_street: str | None = Field(default=None, description="SBA-truncated street (up to 49 chars)")
    borrower_city: str | None = None
    borrower_state: str | None = None
    borrower_zip: str | None = None
    project_county: str | None = Field(default=None, description="504-only: project county for fallback precision")
    latitude: float | None = None
    longitude: float | None = None
    as_of_date: datetime | None = Field(default=None, description="File as-of date parsed from the FOIA filename")
    h3_res7: str | None = None
    h3_res8: str | None = None
    h3_res9: str | None = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("program")
    @classmethod
    def _program_vocab(cls, value: str) -> str:
        if value not in SBA_PROGRAMS:
            raise ValueError(f"program must be one of {SBA_PROGRAMS}, got {value!r}")
        return value
