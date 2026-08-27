"""Typed acquisition spec + engine for municipal dataset ingestion.

US-182 (expand phase): consolidates the dataset-acquisition knowledge that
today lives as an undocumented vocabulary inside ``DatasetSpec`` and is
decoded inconsistently across the scheduler, the backfill loader, the staleness
probe, and the five per-platform clients.  This module is strictly ADDITIVE:
it changes no caller, and ``DatasetSpec`` remains the live input
everywhere.  The ``AcquisitionEngine`` reimplements, behavior-for-behavior, the
endpoint resolution, WHERE construction, high-watermark bookkeeping, and
platform pagination-key translation that those callers perform today, so a
future routing change is a drop-in.

Behavior is preserved against these oracles:

* endpoint resolution            -> ``src.spatial.city_registry.resolve_endpoint``
* WHERE construction             -> ``MunicipalIngestionScheduler.poll_job``
* watermark rendering helpers    -> ``src.producers.watermarks``
* US-111 future-watermark guard  -> scheduler ``poll_job``,
  ``scripts.backfill_loader.backfill_job``,
  ``scripts.feed_staleness_probe.newest_watermark``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.producers.watermarks import (
    ANSI_DATE_LITERAL_HOSTS,
    parse_watermark,
    typed_watermark_entry,
    watermark_comparison,
    watermark_exclude_clause,
)


# Event attributes the scheduler's non-text watermark path reads, in priority
# order. Mirrors the chained ``or`` in MunicipalIngestionScheduler.poll_job.
_EVENT_WM_ATTRS = ("issuance_date", "created_date", "effective_date", "recorded_date")


@dataclass
class AcquisitionSpec:
    """Typed view over a ``DatasetSpec``'s meaningful acquisition keys.

    ``endpoint`` / ``platform`` / ``watermark_col`` / ``id_keys`` / ``topic`` /
    ``interval_seconds`` / ``producer_key`` are lifted verbatim from the
    ``DatasetSpec`` fields.  The remaining attributes are the typed acquisition
    keys that live directly on ``DatasetSpec`` (US-186 promoted them out of the
    old free-form ``extra`` dict); the attribute names match the registry
    vocabulary so the mapping is self-documenting.

    ``oid_field`` / ``max_record_count`` are retained typed fields (declared by
    several ArcGIS specs and asserted by the interlock gate at
    ``test_interlock_gate.py``) even though no query path currently consumes
    them.
    """

    # --- identity / contract carried over from DatasetSpec (unchanged upstream) ---
    endpoint: str = ""
    platform: str = "socrata"
    watermark_col: str = ""
    id_keys: List[str] = field(default_factory=list)
    topic: str = ""
    interval_seconds: float = 300.0
    producer_key: str = ""

    # --- typed acquisition keys (formerly ``DatasetSpec``) ---
    endpoint_by_year: Dict[str, str] = field(default_factory=dict)
    watermark_type: Optional[str] = None
    watermark_format: Optional[str] = None
    watermark_exclude: List[str] = field(default_factory=list)
    order_by: Optional[str] = None
    id_col: Optional[str] = None
    select: Optional[str] = None
    fallback_endpoints: List[str] = field(default_factory=list)
    where: Optional[str] = None
    needs_geocode: bool = False
    geocode_context: Optional[str] = None
    field_map: Dict[str, Any] = field(default_factory=dict)
    ingestion_mode: str = "incremental"
    oid_field: Optional[str] = None
    max_record_count: Optional[int] = None
    expected_cadence_days: Optional[int] = None
    alarm_exempt: bool = False
    alarm_exempt_reason: Optional[str] = None
    annual_rotation: bool = False
    companion_endpoints: Dict[str, Any] = field(default_factory=dict)
    proxy_for: Optional[str] = None
    retention_days: Optional[int] = None
    rolling_window_days: Optional[int] = None
    rollover: Optional[str] = None
    state_plane_crs: Optional[str] = None
    state_plane_units: Optional[str] = None
    state_plane_x_col: Optional[str] = None
    state_plane_y_col: Optional[str] = None
    parcel_join: Dict[str, Any] = field(default_factory=dict)
    non_spatial: Optional[bool] = None

    @classmethod
    def from_dataset_spec(cls, ds: "DatasetSpec") -> "AcquisitionSpec":
        """Parse a ``DatasetSpec`` into a typed ``AcquisitionSpec``.

        Every meaningful acquisition key is read directly off the typed
        ``DatasetSpec`` fields (US-186); ``DatasetSpec`` is not modified.
        """
        return cls(
            endpoint=ds.endpoint,
            platform=ds.platform,
            watermark_col=ds.watermark_col,
            id_keys=list(ds.id_keys or []),
            topic=ds.topic,
            interval_seconds=ds.interval_seconds,
            producer_key=ds.producer_key or "",
            endpoint_by_year=dict(ds.endpoint_by_year or {}),
            watermark_type=ds.watermark_type,
            watermark_format=ds.watermark_format,
            watermark_exclude=list(ds.watermark_exclude or []),
            order_by=ds.order_by,
            id_col=ds.id_col,
            select=ds.select,
            fallback_endpoints=list(ds.fallback_endpoints or []),
            where=ds.where,
            needs_geocode=bool(ds.needs_geocode),
            geocode_context=ds.geocode_context,
            field_map=dict(ds.field_map or {}),
            ingestion_mode=ds.ingestion_mode or "incremental",
            oid_field=ds.oid_field,
            max_record_count=ds.max_record_count,
            expected_cadence_days=ds.expected_cadence_days,
            alarm_exempt=bool(ds.alarm_exempt),
            alarm_exempt_reason=ds.alarm_exempt_reason,
            annual_rotation=bool(ds.annual_rotation),
            companion_endpoints=dict(ds.companion_endpoints or {}),
            proxy_for=ds.proxy_for,
            retention_days=ds.retention_days,
            rolling_window_days=ds.rolling_window_days,
            rollover=ds.rollover,
            state_plane_crs=ds.state_plane_crs,
            state_plane_units=ds.state_plane_units,
            state_plane_x_col=ds.state_plane_x_col,
            state_plane_y_col=ds.state_plane_y_col,
            parcel_join=dict(ds.parcel_join or {}),
            non_spatial=ds.non_spatial,
        )

    def to_dataset_spec(self) -> "DatasetSpec":
        """Reconstruct an equivalent ``DatasetSpec`` with the typed fields set."""
        from src.spatial.city_registry import DatasetSpec

        return DatasetSpec(
            endpoint=self.endpoint,
            platform=self.platform,
            watermark_col=self.watermark_col,
            id_keys=list(self.id_keys),
            topic=self.topic,
            interval_seconds=self.interval_seconds,
            producer_key=self.producer_key,
            endpoint_by_year=dict(self.endpoint_by_year),
            watermark_type=self.watermark_type,
            watermark_format=self.watermark_format,
            watermark_exclude=list(self.watermark_exclude),
            order_by=self.order_by,
            id_col=self.id_col,
            select=self.select,
            fallback_endpoints=list(self.fallback_endpoints),
            where=self.where,
            needs_geocode=self.needs_geocode,
            geocode_context=self.geocode_context,
            field_map=dict(self.field_map),
            ingestion_mode=self.ingestion_mode,
            oid_field=self.oid_field,
            max_record_count=self.max_record_count,
            expected_cadence_days=self.expected_cadence_days,
            alarm_exempt=self.alarm_exempt,
            alarm_exempt_reason=self.alarm_exempt_reason,
            annual_rotation=self.annual_rotation,
            companion_endpoints=dict(self.companion_endpoints),
            proxy_for=self.proxy_for,
            retention_days=self.retention_days,
            rolling_window_days=self.rolling_window_days,
            rollover=self.rollover,
            state_plane_crs=self.state_plane_crs,
            state_plane_units=self.state_plane_units,
            state_plane_x_col=self.state_plane_x_col,
            state_plane_y_col=self.state_plane_y_col,
            parcel_join=dict(self.parcel_join),
            non_spatial=self.non_spatial,
        )


# --------------------------------------------------------------------------- #
# Endpoint resolution                                                         #
# --------------------------------------------------------------------------- #
def resolve_endpoint(spec: AcquisitionSpec, today: Optional[Any] = None) -> str:
    """Resolve a spec's endpoint for "today", honoring year-sliced datasets.

    Behavior-preserving reimplementation of
    ``src.spatial.city_registry.resolve_endpoint``.  Some jurisdictions publish
    one layer/resource per calendar year (``endpoint_by_year``); this returns
    the current year's entry, else the newest year not in the future, else the
    lexicographically latest entry.
    """
    by_year = spec.endpoint_by_year
    if not by_year:
        return spec.endpoint
    if today is None:
        today = datetime.now(UTC).date()
    year = getattr(today, "year", None)
    if year is None:
        year = int(str(today)[:4])
    for candidate in range(year, -1, -1):
        key = str(candidate)
        if key in by_year:
            return by_year[key]
    return by_year[max(by_year)]


# --------------------------------------------------------------------------- #
# WHERE construction                                                          #
# --------------------------------------------------------------------------- #
def build_where(
    *,
    base_where: Optional[str],
    watermark_col: str,
    high_watermark: Optional[str],
    endpoint: str,
    watermark_type: Optional[str] = None,
    watermark_format: Optional[str] = None,
    watermark_exclude: Optional[List[str]] = None,
    watermark_op: str = ">",
    incremental: bool = True,
    snapshot: bool = False,
    override_where: Optional[str] = None,
) -> Optional[str]:
    """Build the incremental/backfill WHERE clause for a polling pass.

    Faithful reimplementation of the clause assembly in
    ``MunicipalIngestionScheduler.poll_job`` (plus the ``">="`` op the backfill
    loader uses).  Composition, in order:

    1. ``(base_where)`` when a registry ``where`` filter is declared.
    2. ``(override_where)`` when a runtime override is supplied.
    3. ``watermark_comparison(...)`` when incremental, not a snapshot, a high
       watermark exists, and a watermark column is declared.
    4. ``watermark_exclude_clause(...)`` when a watermark column is declared and
       sentinels are excluded (ADR 0005).

    Returns ``None`` when no parts are present.
    """
    where_parts: List[str] = []
    if base_where:
        where_parts.append(f"({base_where})")
    if override_where:
        where_parts.append(f"({override_where})")
    if incremental and not snapshot and high_watermark and watermark_col:
        where_parts.append(
            watermark_comparison(
                watermark_col,
                watermark_op,
                high_watermark,
                endpoint,
                watermark_type=watermark_type,
                watermark_format=watermark_format,
            )
        )
    exclude_guard = (
        watermark_exclude_clause(watermark_col, watermark_exclude or [])
        if watermark_col
        else None
    )
    if exclude_guard:
        where_parts.append(exclude_guard)
    return " AND ".join(where_parts) if where_parts else None


# --------------------------------------------------------------------------- #
# High-watermark bookkeeping (US-111 future guard, unified)                    #
# --------------------------------------------------------------------------- #
def is_future_watermark(value: Any, now_dt: datetime) -> bool:
    """Whether a watermark datetime falls strictly after ``now_dt``.

    Mirrors the scheduler's ``_is_future_watermark``: a single future/sentinel
    row must not pin a feed's high watermark.  Naive datetimes are treated as
    UTC so the comparison never raises.
    """
    if value is None:
        return False
    ts = value
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts > now_dt


def parse_state_watermark(raw: str, fmt: Optional[str]) -> Optional[datetime]:
    """Parse a persisted high-watermark string for the future guard.

    Text-typed feeds (ADR 0005) store the raw declared-format string; all
    others store ISO.  Returns ``None`` when unparseable so an unknown format is
    never mistaken for the future.  Mirrors the scheduler's
    ``_parse_state_watermark``.
    """
    try:
        if fmt:
            return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def load_state_watermark(
    raw: Any, fmt: Optional[str], now_dt: datetime
) -> Optional[str]:
    """Apply the US-111 restore guard to a persisted high watermark.

    Returns the persisted string unless it parses to a future datetime, in which
    case ``None`` is returned (the watermark is treated as absent on restore).
    Mirrors ``MunicipalIngestionScheduler._load_state``.
    """
    parsed = parse_state_watermark(str(raw), fmt)
    if parsed is not None and is_future_watermark(parsed, now_dt):
        return None
    return str(raw)


def advance_text_watermark(
    spec: AcquisitionSpec,
    rows: Iterable[Dict[str, Any]],
    *,
    high_watermark: Optional[str],
    now_dt: datetime,
) -> Optional[str]:
    """Track a text-typed (ADR 0005) high watermark from raw rows.

    Mirrors the text-typed branch of ``MunicipalIngestionScheduler.poll_job``:
    the stored high watermark stays the raw declared-format string; each row's
    raw column value is validated via ``typed_watermark_entry`` (dropping
    sentinels and unparseable values), future values are skipped (US-111), and
    the calendar-newest valid value advances the watermark.  For non-text specs
    this is a no-op (the event-attribute path owns those).
    """
    if spec.watermark_type != "text":
        return high_watermark

    new_high_watermark: Optional[str] = high_watermark
    new_hw_parsed: Optional[datetime] = None
    if new_high_watermark:
        stored = typed_watermark_entry(new_high_watermark, fmt=spec.watermark_format)
        new_hw_parsed = stored[1] if stored else None

    for row in rows:
        entry = typed_watermark_entry(
            row.get(spec.watermark_col),
            fmt=spec.watermark_format,
            exclude=spec.watermark_exclude or [],
        )
        if entry and is_future_watermark(entry[1], now_dt):
            continue
        elif entry and (new_hw_parsed is None or entry[1] > new_hw_parsed):
            new_high_watermark = entry[0]
            new_hw_parsed = entry[1]
    return new_high_watermark


def advance_event_watermark(
    current_high: Optional[str],
    candidate_value: Any,
    now_dt: datetime,
) -> Optional[str]:
    """Advance a non-text high watermark from one event-attribute value.

    Mirrors the event-attribute branch of ``MunicipalIngestionScheduler.poll_job``:
    the watermark is the ISO ``strftime`` of the newest non-future value, and a
    future/sentinel value is skipped (US-111).  Feed callers extract the
    candidate via the same ``issuance_date`` / ``created_date`` /
    ``effective_date`` / ``recorded_date`` priority chain the scheduler uses.
    """
    if not candidate_value:
        return current_high
    # The scheduler reads the watermark from a parsed event attribute (a
    # datetime); callers may also pass a raw ISO/text string.  Normalize both
    # through the shared typed parser the rest of the pipeline uses.
    val = parse_watermark(candidate_value)
    if val is None:
        return current_high
    if val > now_dt:
        return current_high
    wm_str = val.strftime("%Y-%m-%dT%H:%M:%S")
    if current_high is None or wm_str > current_high:
        return wm_str
    return current_high


def newest_valid_watermark(
    entries: Iterable[Tuple[str, datetime]],
    now_dt: datetime,
) -> Optional[Tuple[str, datetime]]:
    """Return the newest valid (``<= now``) typed watermark entry.

    Mirrors ``scripts.feed_staleness_probe.newest_watermark``'s validity filter:
    future/sentinel rows are dropped before the max, so a feed's reported
    freshness is never pinned by a future row.
    """
    valid = [entry for entry in entries if entry[1] <= now_dt]
    return max(valid, key=lambda entry: entry[1]) if valid else None


# --------------------------------------------------------------------------- #
# Per-platform pagination-key translation                                     #
# --------------------------------------------------------------------------- #
# The kwargs each platform client's ``paginate`` accepts *beyond* the shared
# positional contract (``endpoint_url``, ``where_clause``, ``batch_size``,
# ``max_records``).  ``where`` is intentionally absent: callers forward it as
# the explicit ``where_clause`` argument, never a splatted kwarg.  CARTO takes
# ``id_col``/``select``; CSV additionally swallows the watermark_* kwargs via
# ``**kwargs`` (and ``fallback_endpoints``); the other three accept only
# ``order_by``.  US-185: this is the adapter-facing contract that replaces the
# prior 7-key truthy splat, which forwarded ``watermark_col`` /
# ``watermark_format`` / ``watermark_exclude`` (and ``id_col``/``select`` for
# non-CARTO platforms) to signatures that reject them — the latent
# ``TypeError`` crash reported against US-183's scheduler.
_ADAPTER_REQUEST_KEYS: Dict[str, Tuple[str, ...]] = {
    "socrata": ("order_by",),
    "arcgis": ("order_by",),
    "carto": ("order_by", "id_col", "select"),
    "ckan": ("order_by",),
    "csv": (
        "order_by",
        "id_col",
        "select",
        "fallback_endpoints",
        "watermark_col",
        "watermark_format",
        "watermark_exclude",
    ),
}


def build_adapter_request(platform: str, spec: AcquisitionSpec) -> Dict[str, Any]:
    """Return ONLY the kwargs the given platform's ``paginate`` accepts.

    Reproduces, per platform, exactly what the adapter expects — no
    ``TypeError``-prone forwarding of keys its signature rejects.  Values come
    from the typed ``AcquisitionSpec`` attributes and are included only when
    truthy (so an unset ``order_by`` or an empty ``fallback_endpoints`` list is
    never forwarded).  Unknown platforms yield an empty request.

    This is the ADAPTER-FACING counterpart to ``build_pagination_kwargs``: that
    function preserves the legacy 7-key splat for US-184's oracles, while this
    one is what the scheduler and the per-producer ``run_stream`` methods should
    use to avoid the latent crash.
    """
    if platform not in _ADAPTER_REQUEST_KEYS:
        return {}
    return {
        key: getattr(spec, key)
        for key in _ADAPTER_REQUEST_KEYS[platform]
        if getattr(spec, key)
    }


def build_pagination_kwargs(platform: str, spec: AcquisitionSpec) -> Dict[str, Any]:
    """Return the pagination kwargs forwarded to a platform client.

    Behavior-preserving reimplementation of the ``client_kwargs`` assembly in
    ``MunicipalIngestionScheduler.poll_job``: the same seven keys, filtered to
    truthy values, are forwarded to every platform's ``paginate`` call.  This
    matches exactly what the adapters currently receive.

    Note (latent upstream bug, out of scope for US-182): the scheduler forwards
    this identical dict to *every* platform even though socrata/arcgis/ckan/
    carto do not accept ``watermark_col`` / ``watermark_format`` /
    ``watermark_exclude`` on their ``paginate`` signatures (only csv swallows
    them via ``**kwargs``), so those platforms would raise ``TypeError`` at poll
    time.  The engine reproduces that exact output today; per-adapter signature
    correction is a follow-up routing change.  ``platform`` is accepted so the
    consolidated translation can branch per adapter in that follow-up without a
    signature change here.
    """
    candidate = {
        "order_by": spec.order_by,
        "id_col": spec.id_col,
        "select": spec.select,
        "fallback_endpoints": spec.fallback_endpoints,
        "watermark_col": spec.watermark_col,
        "watermark_format": spec.watermark_format,
        "watermark_exclude": spec.watermark_exclude,
    }
    return {k: v for k, v in candidate.items() if v}


class AcquisitionEngine:
    """Convenience wrapper that binds an ``AcquisitionSpec`` to the functions.

    The module-level functions above are the canonical API; this class simply
    binds a parsed spec so callers can write ``engine.build_where(...)`` instead
    of threading the spec through each call.
    """

    def __init__(self, spec: AcquisitionSpec):
        self.spec = spec

    def resolve_endpoint(self, today: Optional[Any] = None) -> str:
        return resolve_endpoint(self.spec, today)

    def build_where(
        self,
        *,
        high_watermark: Optional[str] = None,
        watermark_op: str = ">",
        incremental: bool = True,
        snapshot: bool = False,
        override_where: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> Optional[str]:
        return build_where(
            base_where=self.spec.where,
            watermark_col=self.spec.watermark_col,
            high_watermark=high_watermark,
            endpoint=endpoint if endpoint is not None else self.spec.endpoint,
            watermark_type=self.spec.watermark_type,
            watermark_format=self.spec.watermark_format,
            watermark_exclude=self.spec.watermark_exclude,
            watermark_op=watermark_op,
            incremental=incremental,
            snapshot=snapshot,
            override_where=override_where,
        )

    def build_pagination_kwargs(self, platform: Optional[str] = None) -> Dict[str, Any]:
        return build_pagination_kwargs(platform or self.spec.platform, self.spec)

    def build_adapter_request(self, platform: Optional[str] = None) -> Dict[str, Any]:
        return build_adapter_request(platform or self.spec.platform, self.spec)

    def advance_text_watermark(
        self,
        rows: Iterable[Dict[str, Any]],
        *,
        high_watermark: Optional[str],
        now_dt: datetime,
    ) -> Optional[str]:
        return advance_text_watermark(
            self.spec, rows, high_watermark=high_watermark, now_dt=now_dt
        )
