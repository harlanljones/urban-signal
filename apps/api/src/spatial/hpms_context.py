"""HPMS roadway/traffic → H3 validation helpers (US-171, NO spine edits).

Leaf module only — no spine file is imported or edited. This is a building block
for a *future* spine-gated REGISTER of HPMS (Highway Performance Monitoring
System) roadway-inventory / traffic context as a baseline infrastructure layer
(see docs/research/hpms-validation.md). It is intentionally self-contained: it
depends only on the leaf ``H3SpatialIndexer`` (via h3).

HPMS rows are **road-section lines** (polyline geometry, linear referencing
``ROUTE_ID`` + ``BEGIN_POINT``/``END_POINT``, plus ``URBAN_CODE``/
``STATE_CODE``/``COUNTY_CODE``) with attributes such as ``AADT``,
``F_SYSTEM``, ``THROUGH_LANES``, ``SPEED_LIMIT``, ``IRI``. The future producer
will need a full line→H3 covering step (geopandas + h3.polyfill). This leaf
implements the **cheap midpoint approximation** — map each segment's midpoint to
H3 — plus the four metrics proposed on US-171:

1. Attribute completeness (fraction of segments carrying a given attribute)
2. Release lag (reporting year vs. publication / now)
3. H3 coverage fraction (fraction of metro tiles that have ≥1 HPMS segment)
4. Segment→H3 rollup (midpoint assignment, the leaf-feasible variant)

This is a feasibility proof for the four-metric validation; it is not a
replacement for the geopandas line→H3 producer that a REGISTER would need.
"""

from collections.abc import Iterable

from src.spatial.h3_indexer import H3SpatialIndexer

# Resolution choices — the memo proposes H3-5 as the primary context tile
# (the dashboard's metro tiles), with res-7 as the honest macro rollup.
DEFAULT_CONTEXT_RESOLUTION = 5
DEFAULT_ROLLUP_RESOLUTION = 7

# HPMS attributes of interest (2018 schema, from the US-171 evidence memo).
HPMS_TRAFFIC_ATTRS = ("AADT", "AADT_COMBINATION", "AADT_SINGLE_UNIT", "TRUCK")
HPMS_CAPACITY_ATTRS = ("F_SYSTEM", "THROUGH_LANES", "SPEED_LIMIT")
HPMS_CONDITION_ATTRS = ("IRI", "PSR")


def attribute_completeness(records: list[dict], field: str) -> float:
    """Fraction of HPMS records that carry a non-null, non-zero value for *field*.

    Missing is defined as: field absent, ``None``, empty string, or (for numeric
    fields) ``0``/``0.0`` where the FHWA dictionary treats 0 as "not collected".
    The caller decides the zero semantics — this helper treats numeric zero as
    missing by default, matching HPMS's common convention for AADT/IRI/lanes.
    Returns 0.0 for an empty input (never divide-by-zero).
    """
    if not records:
        return 0.0
    present = 0
    for rec in records:
        val = rec.get(field)
        if val is None:
            continue
        if isinstance(val, str) and (val.strip() == "" or val.strip() == "0"):
            continue
        if isinstance(val, (int, float)) and val == 0:
            continue
        present += 1
    return present / len(records)


def release_lag_years(
    reporting_year: int,
    publication_year: int | None = None,
    now_year: int | None = None,
) -> dict[str, int | None]:
    """Compute HPMS publication lag and age-vs-now.

    * ``publication_lag`` — years between the reported traffic year and the
      public geospatial release year (the memo's 7–8-year lag).
    * ``age_vs_now`` — years between the reported traffic year and today
      (how stale the baseline is as context).

    Either ``publication_year`` or ``now_year`` may be ``None`` (field not
    known) — the corresponding lag is reported as ``None`` rather than
    fabricated.
    """
    out: dict[str, int | None] = {
        "publication_lag": None,
        "age_vs_now": None,
    }
    if publication_year is not None:
        out["publication_lag"] = publication_year - reporting_year
    if now_year is not None:
        out["age_vs_now"] = now_year - reporting_year
    return out


def coverage_fraction(
    cells_with_hpms: set[str],
    metro_cells: set[str],
) -> float:
    """Fraction of metro H3 tiles/cells that have ≥1 HPMS segment covering them.

    Both arguments are sets of H3 cell tokens at the **same** resolution
    (typically 5 for the dashboard context, or 7 for the macro rollup).
    Returns 0.0 for an empty metro (degenerate bbox) rather than raising.
    """
    if not metro_cells:
        return 0.0
    return len(cells_with_hpms & metro_cells) / len(metro_cells)


def segment_midpoint_to_h3(
    lat: float,
    lng: float,
    resolution: int = DEFAULT_ROLLUP_RESOLUTION,
) -> str:
    """Map a single HPMS segment's midpoint (lat/lng) to one H3 cell."""
    return H3SpatialIndexer.latlng_to_h3(lat, lng, resolution=resolution)


def rollup_segments_to_h3(
    segments: Iterable[dict],
    lat_key: str = "mid_lat",
    lng_key: str = "mid_lng",
    resolution: int = DEFAULT_ROLLUP_RESOLUTION,
) -> dict[str, dict[str, float | int]]:
    """Group HPMS segment midpoints into H3 cells and aggregate selected attrs.

    * ``segments`` — each dict must carry ``lat_key``/``lng_key`` (midpoint) and
      may carry any of the HPMS attrs (AADT, THROUGH_LANES, SPEED_LIMIT, IRI,
      F_SYSTEM). Missing attrs are not counted.
    * Returns ``{h3_cell: {"segment_count": int, "aadt_sum": float,
      "aadt_count": int, "aadt_mean": float | None, ...}}`` for each occupied cell.

    This is the **midpoint approximation** of line→H3 covering (leaf-feasible
    without geopandas). The future producer replaces this with a true
    polyline→H3 covering via ``h3.polyfill`` and length-weighting.
    """
    cells: dict[str, dict[str, float | int]] = {}
    for seg in segments:
        try:
            lat = float(seg[lat_key])  # type: ignore[arg-type]
            lng = float(seg[lng_key])  # type: ignore[arg-type]
        except (KeyError, TypeError, ValueError):
            continue
        cell = segment_midpoint_to_h3(lat, lng, resolution=resolution)
        bucket = cells.setdefault(
            cell,
            {
                "segment_count": 0,
                "aadt_sum": 0.0,
                "aadt_count": 0,
                "aadt_mean": None,
                "lanes_sum": 0.0,
                "lanes_count": 0,
            },
        )
        bucket["segment_count"] = int(bucket["segment_count"]) + 1
        aadt = seg.get("AADT")
        if aadt is not None and aadt != "" and float(aadt) != 0.0:  # type: ignore[arg-type]
            try:
                v = float(aadt)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                v = None
            if v is not None:
                bucket["aadt_sum"] = float(bucket["aadt_sum"]) + v  # type: ignore[operator]
                bucket["aadt_count"] = int(bucket["aadt_count"]) + 1
        lanes = seg.get("THROUGH_LANES")
        if lanes is not None and lanes != "" and float(lanes) != 0.0:  # type: ignore[arg-type]
            try:
                lv = float(lanes)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                lv = None
            if lv is not None:
                bucket["lanes_sum"] = float(bucket["lanes_sum"]) + lv  # type: ignore[operator]
                bucket["lanes_count"] = int(bucket["lanes_count"]) + 1

    for cell, bucket in cells.items():
        aadt_count = int(bucket["aadt_count"])
        bucket["aadt_mean"] = (float(bucket["aadt_sum"]) / aadt_count) if aadt_count else None  # type: ignore[operator]
    return cells
