"""FEMA NFHL flood-hazard → H3 coverage aggregation — leaf module (US-389, NO spine edits).

Pure geometry helpers that convert FEMA NFHL flood-hazard zone polygons
(served by the public NFHL MapServer as ArcGIS polygon ``rings``) into
per-H3-cell flood-zone coverage shares at the repo's res 7/8/9 hierarchy.
This is intentionally a *leaf* file: it imports ONLY from ``h3``, ``shapely``,
and ``h3_indexer`` (itself a leaf file), so it can land without touching any
spine file. Registering NFHL as a live signal would be an interlock/spine
change (new ``FeedType``, a polygon→H3 producer archetype, per-metro registry
entries, versioning by FIRM panel effective date) and is explicitly out of
scope for this stream — see ``docs/research/fema-nfhl-validation.md``
(recommendation: DEFER). The helpers here are the reusable, spine-free building
block a future spine-bound registration would call.

The coverage share is the *areal fraction* of an H3 cell covered by flood
zones (optionally SFHA only) — the "flood-zone share per H3 cell" feature the
ticket asks for, distinct from the repo's existing point-event feeds.
"""

from collections.abc import Sequence

import h3
from shapely.geometry import Polygon
from shapely.ops import unary_union

from src.spatial.h3_indexer import H3SpatialIndexer

# Flood-zone codes (FLD_ZONE) that designate Special Flood Hazard Areas
# (SFHA): the 1%-annual-chance regulatory flood hazard. The MapServer also
# exposes an authoritative boolean ``SFHA_TF`` ('T' = in SFHA); prefer it when
# present, and fall back to this set of zone codes otherwise.
SFHA_ZONE_CODES = frozenset({"A", "AE", "AH", "AO", "A99", "AR", "V", "VE"})

# Zone codes in the 0.2%-annual-chance / minimal-risk tail are treated as
# non-SFHA exposure; anything else (e.g. D, X) is not scored.
NON_SFHA_ZONE_CODES = frozenset({"X", "D"})


def is_sfha_zone(fld_zone: str | None, sfha_tf: str | None = None) -> bool:
    """Return True when a NFHL feature is in a Special Flood Hazard Area.

    Prefers the authoritative ``SFHA_TF`` flag (``'T'``) when the producer
    supplies it; otherwise falls back to the ``FLD_ZONE`` code. This mirrors
    the MapServer's own semantics: ``SFHA_TF='T'`` is the definitive
    in-SFHA marker, and ``FLD_ZONE`` codes like ``AE``/``VE`` are its
    human-readable expression.
    """
    if sfha_tf is not None:
        return str(sfha_tf).strip().upper() == "T"
    if fld_zone is None:
        return False
    return str(fld_zone).strip().upper() in SFHA_ZONE_CODES


def rings_to_shapely(rings: Sequence[Sequence[Sequence[float]]]) -> Polygon:
    """Build a shapely (multi)polygon from one ArcGIS ``rings`` payload.

    ``rings`` is the ArcGIS polygon geometry: a list of rings, each a closed
    list of ``[lng, lat]`` vertices. Interior rings (holes) are not treated
    specially here; each ring is unioned as a solid polygon, which is the
    conservative, boundary-simple approximation the coverage share needs and
    avoids fragile hole-winding logic. Coordinates must already be WGS84.
    """
    parts = []
    for ring in rings:
        coords = [(pt[0], pt[1]) for pt in ring if len(pt) >= 2]
        if len(coords) >= 4:
            parts.append(Polygon(coords))
    if not parts:
        raise ValueError("rings payload contained no usable polygon")
    if len(parts) == 1:
        return parts[0]
    return unary_union(parts)  # type: ignore[return-value]


def _to_h3_shape(geom: Polygon | object) -> object:
    """Convert a shapely (multi)polygon to the H3 LatLngPoly shape object.

    ``h3.h3shape_to_cells`` accepts ``LatLngPoly`` / ``LatLngMultiPoly``
    built from ``(lat, lng)`` tuples (never shapely directly). A shapely
    MultiPolygon maps to a ``LatLngMultiPoly`` of its parts.
    """
    from shapely.geometry import MultiPolygon

    def part_to_poly(p: Polygon) -> h3.LatLngPoly:  # type: ignore[name-defined]
        return h3.LatLngPoly([(lat, lng) for lng, lat in p.exterior.coords])

    if isinstance(geom, MultiPolygon):
        return h3.LatLngMultiPoly(*[part_to_poly(p) for p in geom.geoms])
    return part_to_poly(geom)  # type: ignore[arg-type]


def candidate_cells(geom: object, resolution: int) -> list[str]:
    """List H3 cells at ``resolution`` whose centroid falls inside ``geom``.

    Uses ``h3.h3shape_to_cells`` (polyfill), which returns cells whose
    *center points* are contained in the polygon — the standard, cheap way to
    enumerate the cells a polygon touches without rasterizing.
    """
    shape = _to_h3_shape(geom)
    return list(h3.h3shape_to_cells(shape, resolution))


def cell_coverage_share(h3_cell: str, geom: object) -> float:
    """Fraction of one H3 cell's area covered by ``geom``, in [0, 1].

    Computed as the planar intersection of the cell boundary polygon
    (H3 ``cell_to_boundary`` → shapely) with ``geom``, in lng/lat space. This
    is the areal share — meaningful for the same cell and zone because both
    sides of the ratio are in the same projection. Distortion between lng/lat
    area and true surface area cancels to first order for a single cell, which
    is the precision required for a static context feature.
    """
    boundary = h3.cell_to_boundary(h3_cell)  # [(lat, lng), ...]
    cell_poly = Polygon([(lng, lat) for lat, lng in boundary])
    inter = cell_poly.intersection(geom)
    if inter.is_empty:
        return 0.0
    share = inter.area / cell_poly.area
    return min(1.0, max(0.0, share))


def rollup_flood_coverage(
    rings_list: Sequence[Sequence[Sequence[Sequence[float]]]],
    resolution: int = 9,
    sfha_only: bool = True,
    zone_codes: Sequence[str | None] | None = None,
    sfha_flags: Sequence[str | None] | None = None,
) -> dict[str, float]:
    """Accumulate flood-zone coverage shares per H3 cell for a set of zones.

    ``rings_list`` is one ArcGIS ``rings`` payload per flood-zone feature
    (optionally filtered to SFHA first). Optional parallel ``zone_codes`` /
    ``sfha_flags`` let the caller pass ``FLD_ZONE`` / ``SFHA_TF`` per feature
    so a feature can be *skipped* here when ``sfha_only`` rather than relying
    on the caller to filter. Cells are rolled up at ``resolution`` (default
    res 9, the repo's micro/parcel-catalyst tier); pass 7 or 8 for a coarser
    division/macro rollup. Returns ``{h3_cell: coverage_share}``.

    Shares from overlapping zones are unioned per cell by taking the max
    (never summed above 1.0), so a cell that lies in both AE and a floodway
    still reports at most 1.0.
    """
    shares: dict[str, float] = {}
    for i, rings in enumerate(rings_list):
        fld_zone = zone_codes[i] if zone_codes and i < len(zone_codes) else None
        sfha_flag = sfha_flags[i] if sfha_flags and i < len(sfha_flags) else None
        if sfha_only and not is_sfha_zone(fld_zone, sfha_flag):
            continue
        geom = rings_to_shapely(rings)
        for cell in candidate_cells(geom, resolution):
            share = cell_coverage_share(cell, geom)
            if share > 0.0:
                shares[cell] = max(shares.get(cell, 0.0), share)
    return shares


def to_multi_res(
    res9_cells: dict[str, float],
    parent_resolution: int,
) -> dict[str, float]:
    """Aggregate a res-9 coverage rollup up to a coarser resolution.

    Every res-9 cell rolls to exactly one parent at ``parent_resolution``;
    the parent's share is the area-weighted mean of its children's shares
    (children are approximately equal-area at res 9, so a simple mean is used
    — close enough for a static context feature).
    """
    out: dict[str, float] = {}
    for cell, share in res9_cells.items():
        parent = H3SpatialIndexer.get_parent(cell, parent_resolution)
        cur = out.get(parent)
        out[parent] = (cur + share) / 2.0 if cur is not None else share
    return out
