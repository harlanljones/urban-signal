"""CFPB HMDA LAR ingestion leaf module (US-423, NO spine edits).

Row-level parsing and per-tract aggregation for the FFIEC HMDA Modified Loan
Application Register (LAR), completing the ingestion half of the HMDA
feasibility work landed in ``hmda_metrics.py`` (US-165): that module proved
tract-level HMDA metrics (investor-purchase share, denial rate,
government-backed share) can be rolled up to H3 via areal apportionment, but
took pre-aggregated counts as input. This module is the missing piece that
turns raw LAR rows (one row per loan application) into those per-tract counts,
per ``docs/research/federal-mobility-energy-financial-signals-2026-08-30.md``
Ticket Spec 5 (US-424 in that doc's proposed numbering; consolidated into
this ticket, US-423, per the actual Linear scope).

Leaf module only, matching the established convention for this wave
(``epa_echo.py``, ``eia_electricity.py``, ``hmda_metrics.py`` itself): no
imports from ``config`` / ``city_registry`` / ``geo_utils`` / ``submarkets``
/ ``producers``. Registering HMDA as a live scored signal (a NationalFeedSpec
entry, a scheduled producer, a macro/feature-store table) remains a
follow-up spine change — this module only produces the tract-aggregated
counts that ``hmda_metrics.rollup_tract_to_h3`` already knows how to place
onto the spatial feature store's H3 grid.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import httpx

FFIEC_DATA_BROWSER_CSV_ENDPOINT = "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv"

# action_taken codes (LAR data dictionary).
ACTION_ORIGINATED = 1
ACTION_APPROVED_NOT_ACCEPTED = 2
ACTION_DENIED = 3
ACTION_WITHDRAWN = 4
ACTION_CLOSED_INCOMPLETE = 5
# Codes 6 (purchased loan) and 7/8 (preapproval) exist in the dictionary but
# are not "decisions" for denial-rate purposes and are excluded below.
DECIDED_ACTIONS = {
    ACTION_ORIGINATED,
    ACTION_APPROVED_NOT_ACCEPTED,
    ACTION_DENIED,
    ACTION_WITHDRAWN,
    ACTION_CLOSED_INCOMPLETE,
}

# loan_purpose codes: 1=Home purchase, 2=Home improvement, 31/32=Refinance,
# 4=Other/not applicable.
PURPOSE_HOME_PURCHASE = 1
PURPOSE_HOME_IMPROVEMENT = 2

# occupancy_type codes: 1=Principal residence, 2=Second residence,
# 3=Investment property.
OCCUPANCY_INVESTMENT = 3

# Government-backed loan_type codes: 1=Conventional, 2=FHA, 3=VA, 4=RHS/FSA.
GOVERNMENT_BACKED_LOAN_TYPES = {2, 3, 4}


@dataclass
class TractHmdaAggregate:
    """Per-tract LAR aggregate counts, shaped for ``hmda_metrics`` rollups."""

    census_tract: str
    total_applications: int = 0
    purchase: int = 0
    investor_purchase: int = 0
    home_improvement_volume: float = 0.0
    decided: int = 0
    denied: int = 0
    government_backed: int = 0
    loan_amount_total: float = 0.0

    def as_metrics(self) -> Dict[str, float]:
        """The counts dict shape ``hmda_metrics.rollup_tract_to_h3`` expects."""
        return {
            "total_applications": float(self.total_applications),
            "purchase": float(self.purchase),
            "investor_purchase": float(self.investor_purchase),
            "home_improvement_volume": float(self.home_improvement_volume),
            "decided": float(self.decided),
            "denied": float(self.denied),
            "government_backed": float(self.government_backed),
            "loan_amount_total": float(self.loan_amount_total),
        }


def _to_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_census_tract(raw: Any) -> Optional[str]:
    """Validate/normalize an 11-digit census tract FIPS string.

    Returns ``None`` for missing, "NA", or malformed values (LAR ships an
    "Exempt" / blank tract for some records) rather than raising — callers
    should drop those rows from tract aggregation.
    """
    if raw is None:
        return None
    tract = str(raw).strip()
    if not tract or not tract.isdigit() or len(tract) != 11:
        return None
    return tract


def aggregate_lar_rows(rows: Iterable[Dict[str, Any]]) -> Dict[str, TractHmdaAggregate]:
    """Fold raw LAR rows into per-tract aggregates.

    Rows with an unresolvable ``census_tract`` are skipped (they cannot be
    placed on the spatial feature store). Every other row contributes to
    ``total_applications`` regardless of ``action_taken``; the
    purchase/investor/denial/government-backed counters only increment for
    the action/purpose/occupancy/loan-type codes that define them, matching
    the LAR data dictionary semantics documented in the research probe.
    """
    out: Dict[str, TractHmdaAggregate] = {}
    for row in rows:
        tract = normalize_census_tract(row.get("census_tract"))
        if tract is None:
            continue
        agg = out.setdefault(tract, TractHmdaAggregate(census_tract=tract))
        agg.total_applications += 1

        action = _to_int(row.get("action_taken"))
        purpose = _to_int(row.get("loan_purpose"))
        occupancy = _to_int(row.get("occupancy_type"))
        loan_type = _to_int(row.get("loan_type"))
        loan_amount = _to_float(row.get("loan_amount")) or 0.0
        agg.loan_amount_total += loan_amount

        if purpose == PURPOSE_HOME_PURCHASE:
            agg.purchase += 1
            if occupancy == OCCUPANCY_INVESTMENT:
                agg.investor_purchase += 1
        elif purpose == PURPOSE_HOME_IMPROVEMENT:
            agg.home_improvement_volume += loan_amount

        if action in DECIDED_ACTIONS:
            agg.decided += 1
            if action == ACTION_DENIED:
                agg.denied += 1
            if loan_type in GOVERNMENT_BACKED_LOAN_TYPES:
                agg.government_backed += 1

    return out


def tract_metrics_for_rollup(
    aggregates: Dict[str, TractHmdaAggregate],
) -> Dict[str, Dict[str, float]]:
    """Convert tract aggregates into the dict shape ``rollup_tract_to_h3`` expects."""
    return {tract: agg.as_metrics() for tract, agg in aggregates.items()}


class HmdaLarClient:
    """Thin client over the FFIEC HMDA Data Browser API v2 CSV export.

    The Data Browser streams CSV (not JSON) for bulk views, so this mirrors
    ``SbaLoanClient``'s streamed-CSV shape rather than the offset-paginated
    JSON shape used by FDIC/EIA: HMDA's modified LAR is an annual census, not
    an incrementally paginated resource.
    """

    def __init__(self, http_client: Optional[httpx.Client] = None):
        self.http = http_client or httpx.Client(timeout=300, follow_redirects=True)

    def fetch_csv(
        self,
        states: Iterable[str],
        years: Iterable[int],
        base_url: str = FFIEC_DATA_BROWSER_CSV_ENDPOINT,
    ) -> str:
        """Fetch the raw CSV text for the given states/years filter."""
        params = {
            "states": ",".join(s.upper() for s in states),
            "years": ",".join(str(y) for y in years),
        }
        response = self.http.get(base_url, params=params)
        response.raise_for_status()
        return response.text

    def lar_rows(
        self,
        states: Iterable[str],
        years: Iterable[int],
        base_url: str = FFIEC_DATA_BROWSER_CSV_ENDPOINT,
    ) -> List[Dict[str, Any]]:
        """Fetch and parse LAR rows for the given states/years into dicts."""
        import csv
        import io

        text = self.fetch_csv(states, years, base_url=base_url)
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
