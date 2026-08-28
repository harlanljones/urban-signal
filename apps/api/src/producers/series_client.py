"""SeriesClient — aggregate market series -> the macro/context store (US-363 §1.1).

Every market-series source is either a static bulk CSV (Zillow, FHFA) or a
keyed, non-paginating REST series API (HUD, Census). Neither fits
``PaginatingClient``: there is no watermark column to page on, no stable row
id, and no point geometry. Rows are keyed ``(geography, period)`` and carry a
number, so the per-topic producers cannot classify or H3-tag them and there is
no event to emit — the output is an upsert into ``macro_series``.

Three profiles, one contract:

``bulk_csv``
    A whole file republished on a cadence. Two layouts:

    * ``wide_dates_as_columns`` — Zillow. Identity columns
      (``RegionID``/``RegionName``/``Metro``/...) followed by one column per
      month; the header's trailing date columns are the periods. Verified live
      2026-08-28: ``Zip_zori_uc_sfrcondomfr_sm_month.csv`` runs through
      ``2026-07-31``.
    * ``long_rows`` — FHFA ``hpi_master.csv``: one row per
      (place, year, period) with the value in ``index_nsa``/``index_sa`` and a
      ``filter`` narrowing to one series (``hpi_type``, ``hpi_flavor``,
      ``frequency``, ``level``).

``rest_api``
    HUD SAFMR — Bearer token, 60 req/min, one request per geography.

``census_api``
    ACS ZCTA tables — API key now required (verified 401/redirect without one).

**Revision handling is mandatory, not optional.** Zillow and FHFA reissue and
revise full history with every release: a value for 2019-03 can change in the
2026-08 file. Ingestion is therefore ``full`` — whole-file diff, upsert of
changed history, prior values retained as vintages — and the per-series
watermark is a *freshness* signal only, never an append-only cursor. Treating
these feeds as append-only silently freezes the first vintage of every revised
month.

**Civility.** Cadence is aligned to the publisher (Zillow the 16th, FHFA's
release calendar, HUD each October) and every fetch is a single whole-file
GET. Zillow's ToU §4.C permits derivative works from the aggregate data with
attribution on every surface; ``SeriesSpec.attribution`` carries the required
string so a surface cannot render the series without it.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Dict, Iterable, Iterator, List, Optional

logger = logging.getLogger(__name__)

WIDE_DATES_AS_COLUMNS = "wide_dates_as_columns"
LONG_ROWS = "long_rows"

PROFILE_BULK_CSV = "bulk_csv"
PROFILE_REST_API = "rest_api"
PROFILE_CENSUS_API = "census_api"

_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_ISO_MONTH = re.compile(r"^(\d{4})-(\d{2})$")


@dataclass(frozen=True)
class SeriesSpec:
    """Declarative description of one aggregate series feed."""

    series_id: str
    source: str  # zillow | fhfa | hud | census | fred
    dataset_id: str  # URL, or a series/entity id for keyed APIs
    profile: str = PROFILE_BULK_CSV
    layout: str = WIDE_DATES_AS_COLUMNS
    geography_level: str = "zip"  # metro | city | county | zip | neighborhood
    geography_col: str = "RegionName"
    metro_col: Optional[str] = None  # secondary column used to resolve city_id
    value_col: Optional[str] = None  # long_rows only
    period_cols: List[str] = field(default_factory=list)  # long_rows only
    period_type: str = "month"  # month | quarter | fiscal_year | year
    auth: str = "none"  # none | bearer | api_key
    auth_env: Optional[str] = None
    row_filter: Dict[str, str] = field(default_factory=dict)
    value_scale: float = 1.0
    unit: str = ""
    cadence_days: int = 30
    attribution: Optional[str] = None
    ingestion_mode: str = "full"
    notes: str = ""

    def token(self) -> Optional[str]:
        """Read this spec's credential from the environment, if it needs one."""
        if self.auth == "none" or not self.auth_env:
            return None
        return os.environ.get(self.auth_env) or None


@dataclass(frozen=True)
class SeriesObservation:
    """One (series, geography, period) datum."""

    series_id: str
    geography_level: str
    geography_id: str
    period: date
    value: float
    source_vintage: str
    city_id: Optional[str] = None
    unit: str = ""


class SeriesFetchError(RuntimeError):
    """Raised when a series source is unreachable or unusable as declared."""


def parse_period(raw: Any, period_type: str = "month") -> Optional[date]:
    """Parse a period cell into the first day of its period.

    Accepts ``2026-07-31`` (Zillow's month-end column headers),
    ``2026-07`` and a bare year. Every period is normalized to its first day so
    that a publisher switching from month-end to month-start labels does not
    fork the key space.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    m = _ISO_DATE.match(text)
    if m:
        year, month, _day = (int(g) for g in m.groups())
        return date(year, month, 1) if period_type != "year" else date(year, 1, 1)
    m = _ISO_MONTH.match(text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), 1)
    if text.isdigit() and len(text) == 4:
        return date(int(text), 1, 1)
    return None


def build_period(values: List[Any], period_type: str) -> Optional[date]:
    """Compose a period from separate year / period columns (FHFA's shape)."""
    if not values:
        return None
    try:
        year = int(str(values[0]).strip())
    except (TypeError, ValueError):
        return None
    if not (1800 <= year <= 2200):
        return None
    if len(values) == 1 or period_type in ("year", "fiscal_year"):
        return date(year, 1, 1)
    try:
        index = int(str(values[1]).strip())
    except (TypeError, ValueError):
        return None
    if period_type == "month":
        return date(year, index, 1) if 1 <= index <= 12 else None
    if period_type == "quarter":
        return date(year, 3 * index - 2, 1) if 1 <= index <= 4 else None
    return None


def to_float(value: Any) -> Optional[float]:
    """Coerce a series cell; blanks and non-numerics are absent, not zero."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("$", "")
    if not text or text in {".", "-", "NA", "N/A", "null", "None"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


class SeriesClient:
    """Fetches aggregate series and yields typed observations."""

    def __init__(self, timeout_seconds: float = 120.0, crosswalk: Any = None):
        self.timeout = timeout_seconds
        self._crosswalk = crosswalk

    # ----------------------------------------------------------------- #
    # geography                                                          #
    # ----------------------------------------------------------------- #
    @property
    def crosswalk(self):
        if self._crosswalk is None:
            from src.spatial.geography_crosswalk import default_crosswalk

            self._crosswalk = default_crosswalk()
        return self._crosswalk

    def resolve_city(
        self,
        spec: SeriesSpec,
        geography_id: str,
        metro_hint: Optional[str] = None,
    ) -> Optional[str]:
        """Map a series row's geography to a registered city, or None.

        A national file covers thousands of geographies we do not register.
        Rows outside every registered metro resolve to ``None`` and are
        dropped by the caller — never attached to the nearest city.
        """
        if spec.geography_level == "zip":
            resolved = self.crosswalk.city_for_zip(geography_id)
            if resolved:
                return resolved
            # A ZIP outside every metro bbox can still be placed by the file's
            # own metro label when it carries one (Zillow's `Metro` column).
            return self.crosswalk.city_for_metro_name(metro_hint) if metro_hint else None
        if spec.geography_level in ("metro", "city"):
            if metro_hint:
                resolved = self.crosswalk.city_for_metro_name(metro_hint)
                if resolved:
                    return resolved
            if geography_id.isdigit() and len(geography_id) == 5:
                return self.crosswalk.city_for_cbsa(geography_id)
            return self.crosswalk.city_for_metro_name(geography_id)
        return None

    # ----------------------------------------------------------------- #
    # transport                                                          #
    # ----------------------------------------------------------------- #
    def _get_text(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        import httpx

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(url, headers=headers or {})
                resp.raise_for_status()
                return resp.text
        except Exception as exc:  # httpx.HTTPError and friends
            raise SeriesFetchError(f"{url}: {exc}") from exc

    def _get_json(self, url: str, headers: Optional[Dict[str, str]] = None) -> Any:
        import httpx

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(url, headers=headers or {})
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            raise SeriesFetchError(f"{url}: {exc}") from exc

    # ----------------------------------------------------------------- #
    # parsing                                                            #
    # ----------------------------------------------------------------- #
    def parse_wide_csv(
        self,
        spec: SeriesSpec,
        text: str,
        vintage: str,
    ) -> Iterator[SeriesObservation]:
        """Wide layout: identity columns, then one column per period."""
        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames or []
        period_columns: list[tuple[str, date]] = []
        for header in headers:
            period = parse_period(header, spec.period_type)
            if period is not None:
                period_columns.append((header, period))
        if not period_columns:
            raise SeriesFetchError(
                f"{spec.series_id}: no period columns in header — layout is not "
                f"{WIDE_DATES_AS_COLUMNS} (first headers: {headers[:6]})"
            )
        for row in reader:
            geography_id = str(row.get(spec.geography_col) or "").strip()
            if not geography_id:
                continue
            if spec.geography_level == "zip":
                from src.spatial.geography_crosswalk import normalize_zcta

                geography_id = normalize_zcta(geography_id)
                if not geography_id:
                    continue
            metro_hint = str(row.get(spec.metro_col) or "").strip() if spec.metro_col else None
            city_id = self.resolve_city(spec, geography_id, metro_hint)
            if city_id is None:
                continue
            for header, period in period_columns:
                value = to_float(row.get(header))
                if value is None:
                    continue
                yield SeriesObservation(
                    series_id=spec.series_id,
                    geography_level=spec.geography_level,
                    geography_id=geography_id,
                    period=period,
                    value=value * spec.value_scale,
                    source_vintage=vintage,
                    city_id=city_id,
                    unit=spec.unit,
                )

    def parse_long_csv(
        self,
        spec: SeriesSpec,
        text: str,
        vintage: str,
    ) -> Iterator[SeriesObservation]:
        """Long layout: one row per (geography, period), filtered to one series."""
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            if any(str(row.get(k, "")).strip() != v for k, v in spec.row_filter.items()):
                continue
            geography_id = str(row.get(spec.geography_col) or "").strip()
            if not geography_id:
                continue
            period = (
                build_period([row.get(c) for c in spec.period_cols], spec.period_type)
                if spec.period_cols
                else parse_period(row.get(spec.geography_col), spec.period_type)
            )
            if period is None:
                continue
            value = to_float(row.get(spec.value_col)) if spec.value_col else None
            if value is None:
                continue
            metro_hint = str(row.get(spec.metro_col) or "").strip() if spec.metro_col else None
            city_id = self.resolve_city(spec, geography_id, metro_hint)
            if city_id is None:
                continue
            yield SeriesObservation(
                series_id=spec.series_id,
                geography_level=spec.geography_level,
                geography_id=geography_id,
                period=period,
                value=value * spec.value_scale,
                source_vintage=vintage,
                city_id=city_id,
                unit=spec.unit,
            )

    def parse_census_rows(
        self,
        spec: SeriesSpec,
        payload: Any,
        vintage: str,
        period: date,
    ) -> Iterator[SeriesObservation]:
        """Census API returns [header, *rows]; the value column is the table id."""
        if not isinstance(payload, list) or len(payload) < 2:
            return
        header = [str(h) for h in payload[0]]
        try:
            value_idx = header.index(spec.value_col or "")
        except ValueError as exc:
            raise SeriesFetchError(
                f"{spec.series_id}: value column {spec.value_col!r} absent from {header}"
            ) from exc
        geo_idx = header.index(spec.geography_col) if spec.geography_col in header else -1
        for row in payload[1:]:
            geography_id = str(row[geo_idx]).strip() if geo_idx >= 0 else ""
            if spec.geography_level == "zip":
                from src.spatial.geography_crosswalk import normalize_zcta

                geography_id = normalize_zcta(geography_id)
            if not geography_id:
                continue
            value = to_float(row[value_idx])
            # Census encodes suppressed/unavailable cells as large negatives
            # (-666666666 and friends); they are absent, not a rent of minus
            # six hundred million.
            if value is None or value <= -100000:
                continue
            city_id = self.resolve_city(spec, geography_id)
            if city_id is None:
                continue
            yield SeriesObservation(
                series_id=spec.series_id,
                geography_level=spec.geography_level,
                geography_id=geography_id,
                period=period,
                value=value * spec.value_scale,
                source_vintage=vintage,
                city_id=city_id,
                unit=spec.unit,
            )

    # ----------------------------------------------------------------- #
    # fetch                                                              #
    # ----------------------------------------------------------------- #
    def fetch(self, spec: SeriesSpec, vintage: Optional[str] = None) -> List[SeriesObservation]:
        """Fetch one series in full and return its observations."""
        stamp = vintage or datetime.now(UTC).date().isoformat()
        if spec.profile == PROFILE_BULK_CSV:
            headers = {}
            token = spec.token()
            if token and spec.auth == "bearer":
                headers["Authorization"] = f"Bearer {token}"
            text = self._get_text(spec.dataset_id, headers)
            parser = self.parse_wide_csv if spec.layout == WIDE_DATES_AS_COLUMNS else self.parse_long_csv
            return list(parser(spec, text, stamp))
        if spec.profile == PROFILE_CENSUS_API:
            token = spec.token()
            url = spec.dataset_id + (f"&key={token}" if token else "")
            payload = self._get_json(url)
            period = build_period([spec.row_filter.get("year")], "year") or date(
                datetime.now(UTC).year - 2, 1, 1
            )
            return list(self.parse_census_rows(spec, payload, stamp, period))
        if spec.profile == PROFILE_REST_API:
            token = spec.token()
            if spec.auth == "bearer" and not token:
                raise SeriesFetchError(
                    f"{spec.series_id}: {spec.auth_env} is unset; HUD's API returns 401 "
                    f"without a Bearer token"
                )
            payload = self._get_json(
                spec.dataset_id,
                {"Authorization": f"Bearer {token}"} if token else None,
            )
            return list(self.parse_hud_payload(spec, payload, stamp))
        raise SeriesFetchError(f"{spec.series_id}: unknown profile {spec.profile!r}")

    def parse_hud_payload(
        self,
        spec: SeriesSpec,
        payload: Any,
        vintage: str,
    ) -> Iterator[SeriesObservation]:
        """HUD wraps its rows in ``{"data": {...}}`` with a year on the envelope."""
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            return
        rows = data.get("basicdata")
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            return
        period = build_period([data.get("year") or spec.row_filter.get("year")], "year")
        if period is None:
            return
        for row in rows:
            if not isinstance(row, dict):
                continue
            from src.spatial.geography_crosswalk import normalize_zcta

            geography_id = normalize_zcta(row.get(spec.geography_col))
            if not geography_id:
                continue
            value = to_float(row.get(spec.value_col))
            if value is None:
                continue
            city_id = self.resolve_city(spec, geography_id)
            if city_id is None:
                continue
            yield SeriesObservation(
                series_id=spec.series_id,
                geography_level=spec.geography_level,
                geography_id=geography_id,
                period=period,
                value=value * spec.value_scale,
                source_vintage=vintage,
                city_id=city_id,
                unit=spec.unit,
            )
