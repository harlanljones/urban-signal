"""NTD transit / GTFS → H3 projection helpers (US-172, NO spine edits).

Leaf module only — no spine file is imported or edited. This is a building
block for a *future* spine-gated REGISTER of NTD (National Transit Database)
monthly ridership/service and agency GTFS geometry as a transit-demand context
source (see docs/research/ntd-transit-gtfs-validation.md). It is intentionally
self-contained: it depends only on the leaf ``H3SpatialIndexer`` (via h3).

Two primitives:

1. GTFS stop geometry → H3. ``parse_gtfs_stops`` reads ``stops.txt`` from an
   agency GTFS zip and ``rollup_stops_to_h3`` tallies stops per H3 res 7/8/9
   cell — the route/stop spatial-coverage primitive that verifies an agency
   feed actually covers a metro bbox.
2. Monthly ridership delta. ``monthly_series_delta`` turns a list of NTD
   monthly records (agency/mode/date → UPT, VRM, VOMS) into a month-over-month
   / year-over-year *change* feature — the service/ridership-change signal the
   validation proposes, computed without leaking future revision months.

NTD ``UPT``/``VRM``/``VOMS`` values arrive as strings from the Socrata API;
``_to_float`` normalizes them so suppressed/missing values become ``None``
rather than ``0`` (never a false zero).
"""

from collections.abc import Iterable

from src.spatial.h3_indexer import H3SpatialIndexer


def _to_float(value) -> float | None:
    """Normalize an NTD numeric cell (str/int/float) to float or None."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def parse_gtfs_stops(zip_path: str) -> list[tuple[str, float, float, str]]:
    """Extract (stop_id, lat, lng, stop_name) tuples from a GTFS zip's stops.txt.

    Rows without parseable coordinates are skipped so a bad row never poisons
    the spatial rollup. Returns an empty list for feeds with no stops.txt.
    """
    import csv
    import io
    import zipfile

    stops: list[tuple[str, float, float, str]] = []
    try:
        with zipfile.ZipFile(zip_path) as z:
            if "stops.txt" not in z.namelist():
                return stops
            with z.open("stops.txt") as f:
                reader = csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace"))
                for row in reader:
                    try:
                        lat = float(row["stop_lat"])
                        lng = float(row["stop_lon"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    stops.append(
                        (row.get("stop_id", ""), lat, lng, row.get("stop_name", ""))
                    )
    except (zipfile.BadZipFile, OSError):
        return stops
    return stops


def rollup_stops_to_h3(
    stops: Iterable[tuple[str, float, float, str]],
    min_density: int = 5,
) -> list[dict]:
    """Tally GTFS stops per effective H3 res 7/8/9 cell.

    Mirrors the event-feed rollup contract: each stop's coordinates resolve to
    the res 7/8/9 hierarchy, and sparse cells fall back to a coarser parent via
    ``H3SpatialIndexer.dynamic_spatial_fallback`` (keyed on stop count). Returns
    one record per effective cell with the res-7/8/9 lineage and the stop tally.
    """
    tally: dict[str, dict] = {}
    for stop_id, lat, lng, name in stops:
        hierarchy = H3SpatialIndexer.get_multi_res_hierarchy(lat, lng)
        # Running stop count for this res-9 cell drives the sparse fallback, so
        # a lone stop in a cell lands on a coarser parent instead of a res-9 orphan.
        prior = tally.get(hierarchy["h3_res9"], {}).get("stop_count", 0)
        effective, effective_res = H3SpatialIndexer.dynamic_spatial_fallback(
            hierarchy["h3_res9"], prior + 1
        )
        bucket = tally.setdefault(
            effective,
            {
                "h3_res7": hierarchy["h3_res7"],
                "h3_res8": hierarchy["h3_res8"],
                "h3_res9": hierarchy["h3_res9"],
                "effective_h3": effective,
                "effective_resolution": effective_res,
                "stop_count": 0,
            },
        )
        bucket["stop_count"] += 1
    return list(tally.values())


def monthly_series_delta(
    records: list[dict],
    key_cols: tuple[str, str, str] = ("agency", "mode", "date"),
    measure: str = "upt",
    lag_months: int = 12,
) -> list[dict]:
    """Compute month-over-month / year-over-year change for a monthly NTD series.

    ``records`` is a sorted-by-date list of NTD monthly rows (agency/mode/date →
    measure). For each record with a prior record ``lag_months`` earlier in the
    same (agency, mode) series, emits the absolute and relative change plus the
    effective value. Rows whose measure is missing (None) are skipped so a
    suppression never reads as a drop. The last record of the series carries
    ``latest: True`` so a consumer can gate "today's" signal on the newest
    available month without leaking future revision months.
    """
    if lag_months < 1:
        raise ValueError("lag_months must be >= 1")
    valid = [rec for rec in records if _to_float(rec.get(measure)) is not None]
    out: list[dict] = []
    for i, rec in enumerate(valid):
        agency = rec.get(key_cols[0])
        mode = rec.get(key_cols[1])
        date = rec.get(key_cols[2])
        val = _to_float(rec.get(measure))
        delta_abs = None
        delta_rel = None
        if i >= lag_months:
            prev = _to_float(valid[i - lag_months].get(measure))
            if prev is not None:
                delta_abs = val - prev
                delta_rel = (delta_abs / prev) if prev else None
        out.append(
            {
                "agency": agency,
                "mode": mode,
                "date": date,
                "value": val,
                f"{measure}_delta_abs": delta_abs,
                f"{measure}_delta_rel": delta_rel,
                "latest": i == len(valid) - 1,
            }
        )
    return out
