"""Bay Area Overture buildings + places density pipeline (US-443).

End-to-end orchestration: fetch (or accept pre-fetched) Overture buildings and
places for the 9-county Bay Area bbox, compute per-H3-res-9 building stock and
POI density metrics, compute commercial churn between two releases, and hand
back building footprints in the exact shape ``run_bay_area_acs_dasymetric_pipeline``
(US-438, Ticket 3) already accepts as its dasymetric weighting mask.

Every result carries ``OVERTURE_BUILDINGS_ATTRIBUTION`` / ``OVERTURE_PLACES_ATTRIBUTION``
(``src.spatial.context_source``) so ODbL notice travels with the pipeline
output rather than being bolted on by a caller that may not know the license
differs from the rest of the ACS/TIGER pipeline.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from shapely.geometry.base import BaseGeometry

from src.spatial.context_source import (
    OVERTURE_BUILDINGS_ATTRIBUTION,
    OVERTURE_PLACES_ATTRIBUTION,
)
from src.spatial.overture_client import (
    BAY_AREA_BBOX,
    DEFAULT_RELEASE,
    BBox,
    OvertureBuildingRow,
    OvertureClient,
    OverturePlaceRow,
)
from src.spatial.overture_density import (
    DEFAULT_H3_RESOLUTION,
    H3BuildingMetrics,
    H3PoiMetrics,
    building_footprint_geometries,
    compute_building_metrics,
    compute_commercial_churn,
    compute_poi_metrics,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OverturePipelineConfig:
    """Configuration for the Bay Area Overture density pipeline."""

    release: str = DEFAULT_RELEASE
    h3_resolution: int = DEFAULT_H3_RESOLUTION
    bbox: BBox = field(default_factory=lambda: BAY_AREA_BBOX)


@dataclass(frozen=True)
class OvertureDensityResult:
    """Bundled pipeline output: per-hex metrics, dasymetric mask, and license notice."""

    release: str
    h3_resolution: int
    building_metrics: list[H3BuildingMetrics]
    poi_metrics: list[H3PoiMetrics]
    building_footprints: list[BaseGeometry]  # ready for BuildingIndex / Ticket-3 dasymetric join
    buildings_attribution: str = OVERTURE_BUILDINGS_ATTRIBUTION
    places_attribution: str = OVERTURE_PLACES_ATTRIBUTION


def run_overture_density_pipeline(
    buildings: Sequence[OvertureBuildingRow] | None = None,
    places: Sequence[OverturePlaceRow] | None = None,
    client: OvertureClient | None = None,
    config: OverturePipelineConfig | None = None,
) -> OvertureDensityResult:
    """Fetch (if needed) and roll up Overture buildings + places into per-hex metrics.

    Parameters
    ----------
    buildings, places : optional
        Pre-fetched rows (e.g. from a cached extraction or a test fixture). If
        either is None, it is fetched live via ``client``.
    client : OvertureClient, optional
        Reused connection for both fetches; a fresh one is opened if omitted
        and a fetch is required.
    config : OverturePipelineConfig, optional
        Release id, H3 resolution, and bbox to query.
    """
    cfg = config or OverturePipelineConfig()

    resolved_buildings = buildings
    resolved_places = places
    if resolved_buildings is None or resolved_places is None:
        active_client = client or OvertureClient()
        try:
            if resolved_buildings is None:
                resolved_buildings = active_client.fetch_buildings(bbox=cfg.bbox, release=cfg.release)
            if resolved_places is None:
                resolved_places = active_client.fetch_places(bbox=cfg.bbox, release=cfg.release)
        finally:
            if client is None:
                active_client.close()

    building_metrics = compute_building_metrics(resolved_buildings, resolution=cfg.h3_resolution)
    poi_metrics = compute_poi_metrics(resolved_places, resolution=cfg.h3_resolution)
    footprints = building_footprint_geometries(resolved_buildings)

    logger.info(
        "Overture density pipeline complete: release=%s buildings=%d places=%d "
        "building_hexes=%d poi_hexes=%d",
        cfg.release,
        len(resolved_buildings),
        len(resolved_places),
        len(building_metrics),
        len(poi_metrics),
    )

    return OvertureDensityResult(
        release=cfg.release,
        h3_resolution=cfg.h3_resolution,
        building_metrics=building_metrics,
        poi_metrics=poi_metrics,
        building_footprints=footprints,
    )


def run_commercial_churn_pipeline(
    places_release_a: Sequence[OverturePlaceRow],
    places_release_b: Sequence[OverturePlaceRow],
    resolution: int = DEFAULT_H3_RESOLUTION,
) -> dict[str, int]:
    """Compute per-hex commercial churn between two already-fetched Overture releases.

    Fetching both releases is left to the caller (two ``OvertureClient.fetch_places``
    calls with different ``release`` ids) since the two calls may need to be
    staged/cached independently ahead of a monthly comparison.
    """
    return compute_commercial_churn(places_release_a, places_release_b, resolution=resolution)
