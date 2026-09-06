"""Census ACS Block-Group to H3 Dasymetric Areal Interpolator (US-438).

Performs dasymetric areal interpolation of Census ACS 5-year estimates across
H3 res-9 hexagonal cells weighted by building footprint density:
1. Intersects source block-group polygon geometries with H3 res-9 cells
2. Counts building footprints (e.g. from Overture buildings) in each intersection piece
3. Proportional allocation for extensive variables (population, housing units, commute breakdown)
4. Building-density-weighted averages for intensive variables (median income, rent, home value)
5. Coefficient of Variation (CV) computation and high-MOE flagging (CV > 0.30)
6. Tagged with ACS vintage year and deterministic/idempotent sorting
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

import h3
from shapely.geometry import Point, Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

from src.spatial.acs_baseline import BGRow
from src.spatial.acs_variables import (
    ACS_DASYMETRIC_VARIABLES,
    ACSVariableSpec,
    VariableType,
)

logger = logging.getLogger(__name__)

# 90% confidence multiplier for ACS margins of error
Z_SCORE_90 = 1.645
DEFAULT_CV_THRESHOLD = 0.30


@dataclass
class H3DasymetricRecord:
    """An H3 cell record produced by dasymetric interpolation."""

    h3_index: str
    vintage: int
    features: dict[str, tuple[float, float]]  # var_name -> (estimate, moe)
    cv_scores: dict[str, float]  # var_name -> CV (se / estimate)
    high_moe_flag: bool  # True if any primary variable exceeds cv_threshold
    high_moe_variables: dict[str, bool]  # per-variable CV > threshold flag
    building_count: float
    intersecting_bg_count: int
    state_fips: str = "06"
    county_fips: list[str] = field(default_factory=list)


class BuildingIndex:
    """Spatial index of building footprint geometries / centroids for rapid querying."""

    def __init__(
        self,
        geometries_or_points: Sequence[BaseGeometry | tuple[float, float] | Sequence[float]] | None = None,
    ):
        self._geoms: list[BaseGeometry] = []
        if geometries_or_points:
            for item in geometries_or_points:
                if isinstance(item, BaseGeometry):
                    self._geoms.append(item)
                elif isinstance(item, (tuple, list)) and len(item) >= 2:
                    # Treat as (lat, lng) or (lng, lat) - convert to Point(lng, lat)
                    # Coordinates in GeoJSON/Shapely are (x=lng, y=lat)
                    first, second = item[0], item[1]
                    if -180.0 <= first <= 180.0 and -90.0 <= second <= 90.0:
                        # Check if (lat, lng) vs (lng, lat)
                        if abs(first) > 90.0 and abs(second) <= 90.0:
                            self._geoms.append(Point(first, second))  # (lng, lat)
                        else:
                            # If first is lat (e.g. 37.77) and second is lng (e.g. -122.42)
                            self._geoms.append(Point(second, first))  # (lng, lat)
                    else:
                        self._geoms.append(Point(first, second))
        self._tree: STRtree | None = STRtree(self._geoms) if self._geoms else None

    @classmethod
    def from_geojson_features(
        cls, features: Iterable[Mapping[str, object]]
    ) -> BuildingIndex:
        """Create BuildingIndex from GeoJSON features."""
        geoms = [shape(f["geometry"]) for f in features if f.get("geometry")]
        return cls(geoms)

    def count_in_geometry(self, geom: BaseGeometry) -> int:
        """Count number of buildings intersecting the target geometry."""
        if self._tree is None or not self._geoms or geom.is_empty:
            return 0
        indices = self._tree.query(geom, predicate="intersects")
        return len(indices)

    def is_empty(self) -> bool:
        return len(self._geoms) == 0


def _get_candidate_h3_cells(geom: BaseGeometry, resolution: int = 9) -> set[str]:
    """Find all H3 cells that could potentially intersect a Shapely geometry."""
    if geom.is_empty:
        return set()

    cells: set[str] = set()
    polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)

    for poly in polys:
        if poly.is_empty or not poly.exterior:
            continue
        # Convert to latlng coordinates (lat, lng) for H3
        outer = tuple((lat, lng) for lng, lat in poly.exterior.coords)
        holes = [
            tuple((lat, lng) for lng, lat in ring.coords)
            for ring in poly.interiors
            if ring
        ]
        try:
            h3_poly = h3.LatLngPoly(outer, *holes)
            base_cells = h3.polygon_to_cells(h3_poly, resolution)
            for c in base_cells:
                cells.update(h3.grid_disk(c, 1))
        except (ValueError, TypeError) as exc:
            logger.debug("H3 polygon_to_cells failed: %s", exc)

        # Also add hexes for all exterior boundary vertices to ensure no edge slices are missed
        for lng, lat in poly.exterior.coords:
            if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
                try:
                    c = h3.latlng_to_cell(lat, lng, resolution)
                    cells.update(h3.grid_disk(c, 1))
                except (ValueError, TypeError) as exc:
                    logger.debug("H3 latlng_to_cell failed: %s", exc)

    return cells


def _h3_cell_to_polygon(cell: str) -> Polygon:
    """Convert an H3 index to a Shapely Polygon in (lng, lat) coordinates."""
    boundary = h3.cell_to_boundary(cell)
    coords = [(lng, lat) for lat, lng in boundary]
    return Polygon(coords)


def compute_cv(estimate: float, moe: float) -> float:
    """Compute Coefficient of Variation: CV = (MOE / 1.645) / |estimate|.

    Returns 0.0 if estimate is 0 and MOE is 0, or 1.0 if estimate is 0 but MOE > 0.
    """
    if estimate is None or moe is None:
        return 0.0
    abs_est = abs(estimate)
    if abs_est <= 0.0:
        return 1.0 if moe > 0.0 else 0.0
    se = (moe or 0.0) / Z_SCORE_90
    return se / abs_est


@dataclass
class IntersectionPiece:
    """Represents the intersection of a block group with an H3 cell."""

    bg_fips12: str
    h3_index: str
    geometry: BaseGeometry
    area: float
    building_count: int


@dataclass
class DasymetricInterpolator:
    """Dasymetric areal interpolation engine with building footprint weighting."""

    h3_resolution: int = 9
    cv_threshold: float = DEFAULT_CV_THRESHOLD
    variables: Mapping[str, ACSVariableSpec] = field(
        default_factory=lambda: ACS_DASYMETRIC_VARIABLES
    )

    def interpolate(
        self,
        bg_rows: Sequence[BGRow] | Mapping[str, BGRow],
        bg_geometries: Mapping[str, BaseGeometry],
        buildings: BuildingIndex | Sequence[BaseGeometry] | Sequence[tuple[float, float]] | None = None,
        vintage: int = 2023,
    ) -> list[H3DasymetricRecord]:
        """Perform dasymetric interpolation from block-group rows and geometries to H3 cells.

        Parameters
        ----------
        bg_rows : Sequence[BGRow] or Mapping[str, BGRow]
            Block-group data rows keyed by 12-digit GEOID.
        bg_geometries : Mapping[str, BaseGeometry]
            Block-group polygon geometries keyed by 12-digit GEOID.
        buildings : BuildingIndex or Sequence of geometries/points, optional
            Building footprints used for dasymetric weighting.
        vintage : int, default 2023
            ACS 5-year estimate vintage year.

        Returns
        -------
        List[H3DasymetricRecord]
            Deterministic, sorted list of interpolated H3 cell records.
        """
        if isinstance(bg_rows, Sequence):
            row_dict: dict[str, BGRow] = {r.bg_fips12: r for r in bg_rows}
        else:
            row_dict = dict(bg_rows)

        # Build building index if needed
        b_index: BuildingIndex
        if isinstance(buildings, BuildingIndex):
            b_index = buildings
        elif buildings is not None:
            b_index = BuildingIndex(buildings)
        else:
            b_index = BuildingIndex([])

        # 1. Compute spatial intersections: BG -> pieces in intersecting H3 cells
        # Group pieces by block group and by H3 cell
        bg_pieces: dict[str, list[IntersectionPiece]] = {}
        cell_pieces: dict[str, list[IntersectionPiece]] = {}

        # Process each block group that has both geometry and data (or geometry alone)
        for bg_fips, geom in bg_geometries.items():
            if geom.is_empty:
                continue

            cand_cells = _get_candidate_h3_cells(geom, resolution=self.h3_resolution)
            for cell in cand_cells:
                hex_poly = _h3_cell_to_polygon(cell)
                try:
                    inter_geom = geom.intersection(hex_poly)
                except (ValueError, TypeError) as exc:
                    logger.debug("Intersection failed for BG %s cell %s: %s", bg_fips, cell, exc)
                    continue

                if inter_geom.is_empty or inter_geom.area <= 0.0:
                    continue

                b_cnt = b_index.count_in_geometry(inter_geom)
                piece = IntersectionPiece(
                    bg_fips12=bg_fips,
                    h3_index=cell,
                    geometry=inter_geom,
                    area=inter_geom.area,
                    building_count=b_cnt,
                )
                bg_pieces.setdefault(bg_fips, []).append(piece)
                cell_pieces.setdefault(cell, []).append(piece)

        # 2. Calculate dasymetric weights per piece within its source block group
        # If total building count in BG > 0: weight_fraction = piece_b_cnt / total_b_cnt
        # Else (0 buildings in entire BG): weight_fraction = piece_area / total_area
        piece_weights: dict[tuple[str, str], float] = {}  # (bg_fips, cell) -> weight_fraction

        for bg_fips, pieces in bg_pieces.items():
            total_buildings = sum(p.building_count for p in pieces)
            total_area = sum(p.area for p in pieces)

            for p in pieces:
                if total_buildings > 0:
                    frac = p.building_count / float(total_buildings)
                elif total_area > 0.0:
                    frac = p.area / float(total_area)
                else:
                    frac = 0.0
                piece_weights[(bg_fips, p.h3_index)] = frac

        # 3. Aggregate each H3 cell's extensive and intensive variables
        output_records: list[H3DasymetricRecord] = []

        for cell in sorted(cell_pieces.keys()):
            pieces = cell_pieces[cell]
            total_cell_buildings = sum(p.building_count for p in pieces)
            intersecting_bgs = sorted({p.bg_fips12 for p in pieces})
            counties = sorted({bg[2:5] for bg in intersecting_bgs if len(bg) >= 5})

            features: dict[str, tuple[float, float]] = {}
            cv_scores: dict[str, float] = {}
            high_moe_vars: dict[str, bool] = {}

            for var_name, spec in self.variables.items():
                if spec.var_type == VariableType.EXTENSIVE:
                    # Extensive variable: proportional allocation + quadrature MOE
                    allocated_estimates: list[float] = []
                    allocated_moes: list[float] = []

                    for p in pieces:
                        bg_fips = p.bg_fips12
                        frac = piece_weights.get((bg_fips, cell), 0.0)
                        if frac <= 0.0:
                            continue

                        row = row_dict.get(bg_fips)
                        if not row:
                            continue

                        val_pair = row.values.get(spec.estimate_var)
                        if val_pair is not None:
                            est, moe = val_pair
                            # Estimate and MOE scale linearly by fraction
                            allocated_estimates.append(est * frac)
                            allocated_moes.append(moe * frac)

                    total_est = sum(allocated_estimates)
                    # Independent BG variances sum in quadrature: sqrt(sum(moe_i^2))
                    total_moe = sum(m ** 2 for m in allocated_moes) ** 0.5
                    features[var_name] = (total_est, total_moe)

                elif spec.var_type == VariableType.INTENSIVE:
                    # Intensive variable: building-density-weighted average (or area-weighted fallback)
                    vals: list[float] = []
                    moes: list[float] = []
                    weights: list[float] = []

                    for p in pieces:
                        bg_fips = p.bg_fips12
                        row = row_dict.get(bg_fips)
                        if not row:
                            continue

                        val_pair = row.values.get(spec.estimate_var)
                        if val_pair is not None:
                            est, moe = val_pair
                            # Ignore special Census suppressed / negative values
                            if est is not None and est > 0.0:
                                vals.append(est)
                                moes.append(moe or 0.0)
                                # Weight by piece building count if available, else piece area
                                weights.append(float(p.building_count))

                    sum_w = sum(weights)
                    if sum_w <= 0.0:
                        # Fallback to area weights for intensive averages
                        area_weights = []
                        valid_vals = []
                        valid_moes = []
                        for p in pieces:
                            bg_fips = p.bg_fips12
                            row = row_dict.get(bg_fips)
                            if not row:
                                continue
                            val_pair = row.values.get(spec.estimate_var)
                            if val_pair is not None:
                                est, moe = val_pair
                                if est is not None and est > 0.0:
                                    valid_vals.append(est)
                                    valid_moes.append(moe or 0.0)
                                    area_weights.append(p.area)
                        vals = valid_vals
                        moes = valid_moes
                        weights = area_weights
                        sum_w = sum(weights)

                    if vals and sum_w > 0.0:
                        weighted_est = sum(v * w for v, w in zip(vals, weights)) / sum_w
                        # Weighted MOE quadrature: sqrt(sum((w_i / sum_w)^2 * moe_i^2))
                        weighted_moe = sum(((w / sum_w) * m) ** 2 for w, m in zip(weights, moes)) ** 0.5
                        features[var_name] = (weighted_est, weighted_moe)
                    else:
                        features[var_name] = (0.0, 0.0)

                # Compute CV and high MOE flag for this variable
                est_val, moe_val = features[var_name]
                cv = compute_cv(est_val, moe_val)
                cv_scores[var_name] = cv
                high_moe_vars[var_name] = cv > self.cv_threshold

            # Cell-level high MOE flag: True if any primary variable exceeds threshold
            primary_vars = ["total_population", "median_household_income", "housing_units_total"]
            cell_high_moe = any(
                high_moe_vars.get(v, False) for v in primary_vars if v in high_moe_vars
            ) or any(high_moe_vars.values())

            record = H3DasymetricRecord(
                h3_index=cell,
                vintage=vintage,
                features=features,
                cv_scores=cv_scores,
                high_moe_flag=cell_high_moe,
                high_moe_variables=high_moe_vars,
                building_count=float(total_cell_buildings),
                intersecting_bg_count=len(intersecting_bgs),
                state_fips="06",
                county_fips=counties,
            )
            output_records.append(record)

        # Deterministic sorting by H3 index for guaranteed idempotency
        output_records.sort(key=lambda r: r.h3_index)
        return output_records
