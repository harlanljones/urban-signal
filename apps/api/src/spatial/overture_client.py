"""Overture Maps GeoParquet client for the 9-county Bay Area (US-443).

Queries the Overture Maps Foundation's public S3 GeoParquet release for the
``buildings``/``building`` and ``places``/``place`` themes via DuckDB's remote
Parquet reader, bbox-filtered to the Bay Area envelope so only intersecting
row groups are transferred (the same pruning pattern the prior Overture
research (``docs/research/overture-maps-evaluation.md``) validated live).

Licensing differs by theme and matters for downstream attribution:

* **buildings** conflates OpenStreetMap (primary source, highest priority) with
  other open and ML-derived footprint datasets, and is published under
  **ODbL 1.0** — attribution *and* share-alike on derivative databases.
* **places** is published under a CDLA-Permissive-2.0 / Apache-2.0 / CC0 mix
  across its contributing sources, carries **no OpenStreetMap data**, and has
  no share-alike obligation.

See ``OVERTURE_BUILDINGS_ATTRIBUTION`` / ``OVERTURE_PLACES_ATTRIBUTION`` in
``src.spatial.context_source`` for the exact notices that must travel with any
derived artifact.

This is a context-source client (file/object-store snapshot access), not a
``PaginatingClient``: there is no watermark and no per-row event, only a
release identifier and a full-snapshot GeoParquet partition set — the same
shape ``docs/research/overture-maps-evaluation.md`` found when it deferred
Overture as a producer/``FeedType`` candidate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import duckdb
from shapely import wkt
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

from src.spatial.bay_area_boundary import BAY_AREA_METRO_BBOX

logger = logging.getLogger(__name__)

OVERTURE_S3_BASE = "s3://overturemaps-us-west-2/release"

# The release the ticket's own query pattern was authored against. Overture
# ships a new release roughly monthly; callers computing commercial churn
# should pass two explicit, consecutive release ids rather than relying on
# this default drifting.
DEFAULT_RELEASE = "2026-08-19.0"

_EXTENSIONS_LOADED = False


@dataclass(frozen=True)
class BBox:
    """A WGS84 bounding box in Overture's ``bbox.xmin``/``ymin``/``xmax``/``ymax`` order."""

    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @classmethod
    def from_metro_bbox(cls, metro_bbox: dict[str, float] | None = None) -> BBox:
        """Build a BBox from the repo's canonical ``{min_lat,max_lat,min_lng,max_lng}`` shape."""
        m = metro_bbox or BAY_AREA_METRO_BBOX
        return cls(xmin=m["min_lng"], ymin=m["min_lat"], xmax=m["max_lng"], ymax=m["max_lat"])


BAY_AREA_BBOX = BBox.from_metro_bbox()


@dataclass(frozen=True)
class OvertureBuildingRow:
    """One Overture ``buildings``/``building`` record, parsed to a shapely geometry."""

    id: str
    name: str | None
    subtype: str | None  # BuildingSubtype: residential/commercial/industrial/civic/...
    building_class: str | None  # finer-grained BuildingClass
    height: float | None
    num_floors: int | None
    geometry: BaseGeometry


@dataclass(frozen=True)
class OverturePlaceRow:
    """One Overture ``places``/``place`` record, parsed to a shapely Point geometry."""

    id: str
    name: str | None
    category_primary: str | None
    confidence: float | None
    geometry: BaseGeometry


def _ensure_extensions(con: duckdb.DuckDBPyConnection) -> None:
    """Install/load the DuckDB ``spatial`` and ``httpfs`` extensions, once per connection."""
    global _EXTENSIONS_LOADED
    for ext in ("spatial", "httpfs"):
        try:
            con.execute(f"INSTALL {ext}")
            con.execute(f"LOAD {ext}")
        except (RuntimeError, OSError) as exc:
            logger.warning("DuckDB %s extension load notice: %s", ext, exc)
    _EXTENSIONS_LOADED = True


def buildings_parquet_glob(release: str = DEFAULT_RELEASE, base_url: str = OVERTURE_S3_BASE) -> str:
    """Return the GeoParquet glob for the buildings/building partition of a release."""
    return f"{base_url}/{release}/theme=buildings/type=building/*"


def places_parquet_glob(release: str = DEFAULT_RELEASE, base_url: str = OVERTURE_S3_BASE) -> str:
    """Return the GeoParquet glob for the places/place partition of a release."""
    return f"{base_url}/{release}/theme=places/type=place/*"


def _bbox_where(bbox: BBox) -> str:
    """The bbox row-group pruning predicate from the ticket's own DuckDB query pattern."""
    return (
        f"bbox.xmin >= {bbox.xmin} AND bbox.xmax <= {bbox.xmax} "
        f"AND bbox.ymin >= {bbox.ymin} AND bbox.ymax <= {bbox.ymax}"
    )


def _parse_geometry(geom_wkt: str | None) -> BaseGeometry | None:
    if not geom_wkt:
        return None
    try:
        geom = wkt.loads(geom_wkt)
        if not geom.is_valid:
            geom = make_valid(geom)
        return geom
    except (ValueError, AttributeError) as exc:
        logger.warning("Failed to parse Overture geometry: %s", exc)
        return None


class OvertureClient:
    """DuckDB-backed reader for Overture buildings/places GeoParquet themes.

    ``source_override`` lets tests (and any offline/cached pipeline) point at a
    local parquet glob instead of the live S3 release, mirroring
    ``tiger_client``'s local-path override for the same reason: network access
    is not assumed available in unit tests or CI.
    """

    def __init__(
        self,
        connection: duckdb.DuckDBPyConnection | None = None,
        base_url: str = OVERTURE_S3_BASE,
    ):
        self._con = connection or duckdb.connect()
        self._base_url = base_url
        _ensure_extensions(self._con)

    def fetch_buildings(
        self,
        bbox: BBox = BAY_AREA_BBOX,
        release: str = DEFAULT_RELEASE,
        source_override: str | None = None,
    ) -> list[OvertureBuildingRow]:
        """Fetch buildings intersecting ``bbox`` for one Overture release."""
        source = source_override or buildings_parquet_glob(release, self._base_url)
        query = f"""
            SELECT
                id,
                names.primary AS name,
                subtype,
                class AS building_class,
                height,
                num_floors,
                ST_AsText(geometry) AS geom_wkt
            FROM read_parquet('{source}')
            WHERE {_bbox_where(bbox)}
        """
        rows = self._con.sql(query).fetchall()
        out: list[OvertureBuildingRow] = []
        for row_id, name, subtype, building_class, height, num_floors, geom_wkt in rows:
            geom = _parse_geometry(geom_wkt)
            if geom is None:
                continue
            out.append(
                OvertureBuildingRow(
                    id=str(row_id),
                    name=name,
                    subtype=subtype,
                    building_class=building_class,
                    height=float(height) if height is not None else None,
                    num_floors=int(num_floors) if num_floors is not None else None,
                    geometry=geom,
                )
            )
        return out

    def fetch_places(
        self,
        bbox: BBox = BAY_AREA_BBOX,
        release: str = DEFAULT_RELEASE,
        source_override: str | None = None,
    ) -> list[OverturePlaceRow]:
        """Fetch places (POI) intersecting ``bbox`` for one Overture release."""
        source = source_override or places_parquet_glob(release, self._base_url)
        query = f"""
            SELECT
                id,
                names.primary AS name,
                categories.primary AS category_primary,
                confidence,
                ST_AsText(geometry) AS geom_wkt
            FROM read_parquet('{source}')
            WHERE {_bbox_where(bbox)}
        """
        rows = self._con.sql(query).fetchall()
        out: list[OverturePlaceRow] = []
        for row_id, name, category_primary, confidence, geom_wkt in rows:
            geom = _parse_geometry(geom_wkt)
            if geom is None:
                continue
            out.append(
                OverturePlaceRow(
                    id=str(row_id),
                    name=name,
                    category_primary=category_primary,
                    confidence=float(confidence) if confidence is not None else None,
                    geometry=geom,
                )
            )
        return out

    def close(self) -> None:
        self._con.close()
