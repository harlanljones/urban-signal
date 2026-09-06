"""Bay Area Census ACS Block-Group Ingest and Dasymetric H3 Join ETL Pipeline (US-438).

End-to-end pipeline that:
1. Ingests ACS 5-year estimates across 9 Bay Area counties via Census API
2. Loads and parses TIGER/Line block-group geometries
3. Performs dasymetric areal interpolation with building footprint weighting
4. Flags high-MOE cells (CV > 0.30)
5. Produces deterministic, vintage-tagged H3 res-9 records
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from shapely.geometry.base import BaseGeometry

from src.spatial.acs_baseline import BGRow
from src.spatial.acs_client import (
    ACSClient,
    rows_to_bgrows,
)
from src.spatial.acs_dasymetric import (
    BuildingIndex,
    DasymetricInterpolator,
    H3DasymetricRecord,
)
from src.spatial.acs_variables import (
    ACS_DASYMETRIC_VARIABLES,
    BAY_AREA_COUNTIES,
    ACSVariableSpec,
    get_required_acs_variable_codes,
)
from src.spatial.tiger_client import load_bay_area_block_groups

logger = logging.getLogger(__name__)


@dataclass
class ACSDasymetricPipelineConfig:
    """Configuration for the Bay Area ACS dasymetric interpolation pipeline."""

    vintage: int = 2023
    h3_resolution: int = 9
    cv_threshold: float = 0.30
    state_fips: str = "06"
    county_fips: Sequence[str] = tuple(sorted(BAY_AREA_COUNTIES.keys()))
    variables: Mapping[str, ACSVariableSpec] = field(
        default_factory=lambda: ACS_DASYMETRIC_VARIABLES
    )


def run_bay_area_acs_dasymetric_pipeline(
    acs_rows: Iterable[Mapping[str, str]] | None = None,
    tiger_geometries: Mapping[str, BaseGeometry] | Path | str | dict | None = None,
    buildings: BuildingIndex | Sequence[BaseGeometry] | Sequence[tuple[float, float]] | None = None,
    config: ACSDasymetricPipelineConfig | None = None,
    api_key: str | None = None,
) -> list[H3DasymetricRecord]:
    """Execute the end-to-end ACS 5-year dasymetric interpolation ETL pipeline.

    Parameters
    ----------
    acs_rows : Iterable[Mapping[str, str]], optional
        Pre-fetched or fixture raw Census API rows. If None, queries live Census API.
    tiger_geometries : Mapping[str, BaseGeometry] or Path or dict, optional
        Pre-loaded block-group geometries or source path/dict. If None, downloads TIGER shapefiles.
    buildings : BuildingIndex or Sequence of geometries/points, optional
        Building footprint layer for dasymetric weighting.
    config : ACSDasymetricPipelineConfig, optional
        Pipeline configuration (vintage, resolution, thresholds, counties).
    api_key : str, optional
        Census API key for live pulls (or CENSUS_API_KEY env var).

    Returns
    -------
    List[H3DasymetricRecord]
        Interpolated H3 res-9 records with vintage tag, extensive sums, intensive medians,
        MOE propagation, and CV flags.
    """
    cfg = config or ACSDasymetricPipelineConfig()
    needed_vars = get_required_acs_variable_codes(cfg.variables)

    # 1. Acquire Census ACS data
    raw_rows: list[Mapping[str, str]]
    if acs_rows is not None:
        raw_rows = list(acs_rows)
    else:
        client = ACSClient(api_key=api_key, vintage=cfg.vintage)
        raw_rows = client.fetch_block_groups(
            state_fips=cfg.state_fips,
            county_fips=cfg.county_fips,
            variable_codes=needed_vars,
        )

    # Convert to BGRow records
    bg_rows: list[BGRow] = rows_to_bgrows(raw_rows, needed_vars)

    # 2. Acquire TIGER/Line block group geometries
    geometries: dict[str, BaseGeometry]
    if tiger_geometries is not None:
        if isinstance(tiger_geometries, dict) and all(isinstance(v, BaseGeometry) for v in tiger_geometries.values()):
            geometries = dict(tiger_geometries)
        else:
            geometries = load_bay_area_block_groups(
                source=tiger_geometries,
                year=cfg.vintage,
                state_fips=cfg.state_fips,
            )
    else:
        geometries = load_bay_area_block_groups(
            year=cfg.vintage,
            state_fips=cfg.state_fips,
        )

    # 3. Perform dasymetric areal interpolation
    interpolator = DasymetricInterpolator(
        h3_resolution=cfg.h3_resolution,
        cv_threshold=cfg.cv_threshold,
        variables=cfg.variables,
    )

    records = interpolator.interpolate(
        bg_rows=bg_rows,
        bg_geometries=geometries,
        buildings=buildings,
        vintage=cfg.vintage,
    )

    logger.info(
        "ACS dasymetric pipeline complete: %d H3 res-%d cells generated for vintage %d",
        len(records),
        cfg.h3_resolution,
        cfg.vintage,
    )

    return records
