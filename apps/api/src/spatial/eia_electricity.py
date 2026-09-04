"""EIA Form 861 / retail electricity rate leaf module (US-423, NO spine edits).

Client + pure parsing helpers for the EIA API v2 retail-sales endpoint
(``/v2/electricity/retail-sales/data``), which is the commercial/industrial
operating-cost context series identified in
``docs/research/federal-mobility-energy-financial-signals-2026-08-30.md``.

Leaf module only, mirroring the established convention for this wave of
federal context feeds (``epa_echo.py`` US-170, ``hmda_metrics.py`` US-165,
``hpms_context.py`` US-171): it imports nothing from ``config``,
``city_registry``, ``geo_utils``, ``submarkets``, or ``producers``, so it can
land without an interlock/spine change. Registering EIA rates as a live
national feed (a ``NationalFeedSpec`` entry, a scheduled producer, a macro
context-series table) is a follow-up spine change, deliberately out of scope
here — see the module docstring precedent in ``national_feeds.py``.

EIA's grain is state x sector x month/year, not a point or a polygon, so
there is no H3 mapping in this module: a commercial/industrial rate is a
macro covariate looked up by ``(state, sector, period)`` and joined onto a
metro's H3 cells by the metro's state (or, for a future producer, by
utility-service-territory polygon overlay per the research doc). That overlay
step is explicitly deferred; this module only covers the "Wave 1 Series" half
of the recommendation (EIA API v2 time-series retrieval + normalization).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import httpx

EIA_RETAIL_SALES_ENDPOINT = "https://api.eia.gov/v2/electricity/retail-sales/data"

# Sectors this ticket cares about: commercial and industrial operating cost.
# EIA also reports RES (residential) and ALL (total); those pass through
# unfiltered by default but are not the ticket's analytical target.
COMMERCIAL_SECTOR = "COM"
INDUSTRIAL_SECTOR = "IND"
RESIDENTIAL_SECTOR = "RES"
ALL_SECTORS = "ALL"

DEFAULT_FREQUENCY = "monthly"  # "monthly" | "annual"

# EIA reports price in cents per kWh; the ticket wants $/kWh.
CENTS_PER_DOLLAR = 100.0


@dataclass
class ElectricityRateRecord:
    """One normalized EIA retail-sales row: state x sector x period."""

    period: str  # "YYYY-MM" (monthly) or "YYYY" (annual)
    state_id: str  # two-letter state code, e.g. "TX"
    sector_id: str  # "RES" | "COM" | "IND" | "TRA" | "ALL"
    price_per_kwh: Optional[float]  # $/kWh, converted from EIA's c/kWh
    revenue_thousand_usd: Optional[float]
    sales_mwh: Optional[float]
    customers: Optional[int]


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    parsed = _to_float(value)
    return int(parsed) if parsed is not None else None


def cents_to_dollars_per_kwh(cents_per_kwh: Optional[float]) -> Optional[float]:
    """Convert EIA's native c/kWh price to $/kWh. ``None`` passes through."""
    if cents_per_kwh is None:
        return None
    return cents_per_kwh / CENTS_PER_DOLLAR


def parse_retail_sales_row(row: Dict[str, Any]) -> ElectricityRateRecord:
    """Normalize one raw EIA API v2 retail-sales row into a typed record.

    EIA's JSON keys are lowercase already (``period``, ``stateid``,
    ``sectorid``, ``price``, ``revenue``, ``sales``, ``customers``); this
    tolerates missing/None values (EIA omits `customers` for some
    sector/period combinations) rather than raising.
    """
    return ElectricityRateRecord(
        period=str(row.get("period", "")),
        state_id=str(row.get("stateid", "")).upper(),
        sector_id=str(row.get("sectorid", "")).upper(),
        price_per_kwh=cents_to_dollars_per_kwh(_to_float(row.get("price"))),
        revenue_thousand_usd=_to_float(row.get("revenue")),
        sales_mwh=_to_float(row.get("sales")),
        customers=_to_int(row.get("customers")),
    )


def parse_retail_sales_rows(rows: Iterable[Dict[str, Any]]) -> List[ElectricityRateRecord]:
    """Normalize a batch of raw EIA API v2 retail-sales rows."""
    return [parse_retail_sales_row(row) for row in rows]


def commercial_industrial_rate_index(
    records: Iterable[ElectricityRateRecord],
) -> Dict[str, Dict[str, Optional[float]]]:
    """Latest-period commercial and industrial $/kWh rate per state.

    Returns ``{state_id: {"commercial": rate_or_None, "industrial":
    rate_or_None}}``. "Latest" is the lexicographically greatest ``period``
    seen per (state, sector) — safe for both "YYYY-MM" and "YYYY" period
    strings since both sort chronologically as text. Records with a missing
    price are skipped for that (state, sector) rather than clobbering an
    earlier known value with ``None``.
    """
    latest_period: Dict[tuple, str] = {}
    latest_rate: Dict[tuple, Optional[float]] = {}
    for rec in records:
        if rec.sector_id not in (COMMERCIAL_SECTOR, INDUSTRIAL_SECTOR):
            continue
        if rec.price_per_kwh is None:
            continue
        key = (rec.state_id, rec.sector_id)
        if key not in latest_period or rec.period > latest_period[key]:
            latest_period[key] = rec.period
            latest_rate[key] = rec.price_per_kwh

    index: Dict[str, Dict[str, Optional[float]]] = {}
    for (state_id, sector_id), rate in latest_rate.items():
        bucket = index.setdefault(state_id, {"commercial": None, "industrial": None})
        if sector_id == COMMERCIAL_SECTOR:
            bucket["commercial"] = rate
        elif sector_id == INDUSTRIAL_SECTOR:
            bucket["industrial"] = rate
    return index


class EiaElectricityClient:
    """Thin REST client over EIA API v2's retail-sales endpoint.

    EIA API v2 paginates via ``offset``/``length`` with a hard 5000-row page
    cap and reports the total under ``response.total``. The client raises on
    a missing API key rather than sending an unauthenticated request that
    EIA will 403 on.
    """

    MAX_PAGE_LENGTH = 5000

    def __init__(
        self,
        api_key: str,
        base_url: str = EIA_RETAIL_SALES_ENDPOINT,
        page_length: int = MAX_PAGE_LENGTH,
        timeout_seconds: float = 60,
        http_client: Optional[httpx.Client] = None,
    ):
        if not api_key:
            raise ValueError("EiaElectricityClient requires a non-empty api_key")
        self.api_key = api_key
        self.base_url = base_url
        self.page_length = max(1, min(page_length, self.MAX_PAGE_LENGTH))
        self.timeout = timeout_seconds
        self._http = http_client

    def _client(self) -> httpx.Client:
        return self._http or httpx.Client(timeout=self.timeout, follow_redirects=True)

    @staticmethod
    def rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        response = payload.get("response")
        if isinstance(response, dict):
            data = response.get("data")
            if isinstance(data, list):
                return data
        return []

    @staticmethod
    def total(payload: Dict[str, Any]) -> int:
        response = payload.get("response")
        if isinstance(response, dict):
            total = response.get("total")
            if isinstance(total, str) and total.isdigit():
                return int(total)
            if isinstance(total, int):
                return total
        return 0

    def build_params(
        self,
        frequency: str = DEFAULT_FREQUENCY,
        state: Optional[str] = None,
        sectorid: Optional[Iterable[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        offset: int = 0,
        length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build the EIA API v2 query-string params for one page request."""
        params: Dict[str, Any] = {
            "api_key": self.api_key,
            "frequency": frequency,
            "data[0]": "price",
            "data[1]": "revenue",
            "data[2]": "sales",
            "data[3]": "customers",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "offset": offset,
            "length": self.page_length if length is None else length,
        }
        if state:
            params["facets[stateid][]"] = state.upper()
        if sectorid:
            for i, sector in enumerate(sectorid):
                params[f"facets[sectorid][{i}]"] = sector.upper()
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return params

    def fetch_page(self, **kwargs: Any) -> Dict[str, Any]:
        """Fetch one raw JSON page. ``kwargs`` forwards to ``build_params``."""
        params = self.build_params(**kwargs)
        client = self._client()
        owns_client = self._http is None
        try:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        finally:
            if owns_client:
                client.close()

    def retail_sales(
        self,
        frequency: str = DEFAULT_FREQUENCY,
        state: Optional[str] = None,
        sectorid: Optional[Iterable[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        max_records: Optional[int] = None,
    ) -> List[ElectricityRateRecord]:
        """Page through the retail-sales endpoint, returning parsed records."""
        offset = 0
        out: List[ElectricityRateRecord] = []
        while True:
            limit = self.page_length if max_records is None else min(self.page_length, max_records - len(out))
            if limit <= 0:
                break
            payload = self.fetch_page(
                frequency=frequency,
                state=state,
                sectorid=sectorid,
                start=start,
                end=end,
                offset=offset,
                length=limit,
            )
            page = self.rows(payload)
            if not page:
                break
            out.extend(parse_retail_sales_rows(page))
            offset += len(page)
            if len(page) < limit:
                break
        return out
