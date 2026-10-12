"""CoveragePlan: the deep module that answers "which cells exist, who owns them, and how honest are they".

ADR-0010 / ``docs/specs/adaptive-hex-coverage.md`` §3. Registry and Urban Anchor geometry
in; per-metro cell sets with ownership and honesty labels out. Transport-free (INV-5): this
module returns plain data and never runs inference or touches HTTP/KV.

Authority. Stage B keeps the bounded k-ring set (US-408) as the authority for LIMS-bearing
cells: measured at HX-B1, clipping those cells to their Census urban areas would drop 5,948
of 54,172 published cells (11 %, up to 71 % in a small metro) that sit within 1.5 km of a
real submarket. Urban Anchors therefore contribute region identity and an ``in_anchor``
flag now, and the LODES-only remainder of each anchor in Stage D.

Ownership (INV-9). Two metros can both claim a cell (373 cells across 8 pairs today). Every
cell has exactly one *owning* region: the metro whose nearest submarket is closest, ties
broken by city id. A non-owning metro still publishes the cell in its own grid so its view
is unchanged; region builds (Stage C) ship only owned cells.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import h3

from src.spatial import coverage
from src.spatial.urban_anchors import ANCHOR_ASSET, _base_cells, anchors_intersecting

Authority = Literal["k_ring"]
Label = Literal["measured", "interpolated"]

DETAIL_RESOLUTION = 9  # Stage B detail cells are res 9; adaptive resolution arrives with Stage D
INTERPOLATION_BOUND_KM = coverage.DEFAULT_MAX_DIST_KM  # 1.5 km, today's dense-grid bound (DG-9)


@dataclass(frozen=True)
class PlannedCell:
    cell: str
    owner: str  # submarket name that supplies the cell's LIMS baseline
    distance_km: float  # to that submarket's center; 0.0 for the center cell itself
    label: Label  # measured = the submarket's own center cell; interpolated otherwise
    in_anchor: bool  # the cell lies inside one of the metro's Urban Anchors
    owned: bool  # this metro is the cell's single owning region (INV-9)
    borough: str


@dataclass(frozen=True)
class CoveragePlan:
    region_id: str  # "metro/{city_id}"
    city_id: str
    authority: Authority
    anchor_ids: tuple[str, ...]
    detail_res: int
    cells: tuple[PlannedCell, ...]  # sorted by cell; every cell this metro publishes
    golden_count: int  # == len(cells)
    owned_count: int
    measured_count: int
    in_anchor_count: int
    plan_hash: str

    def owned_cells(self) -> tuple[PlannedCell, ...]:
        return tuple(c for c in self.cells if c.owned)


@lru_cache(maxsize=1)
def _anchor_asset_sha() -> str:
    return hashlib.sha256(ANCHOR_ASSET.read_bytes()).hexdigest()


@lru_cache(maxsize=64)
def _anchor_region_cells(anchor_ids: tuple[str, ...]) -> frozenset[str]:
    union: set[str] = set()
    for anchor_id in anchor_ids:
        union.update(_base_cells(anchor_id))
    return frozenset(union)


def metro_anchor_ids(city_id: str) -> tuple[str, ...]:
    """Registered anchors, else the geometry-derived candidates (DG-2: derived, not curated)."""
    from src.spatial.city_registry import REGISTRY, normalize_city

    cid = normalize_city(city_id)
    if cid is None or cid not in REGISTRY:
        raise ValueError(f"Unknown city_id '{city_id}' for coverage planning.")
    reg = REGISTRY[cid]
    return tuple(reg.urban_anchors) or anchors_intersecting(reg.metro_bbox)


def _claims(city_id: str, max_ring: int, max_dist_km: float) -> list[coverage.CellAssignment]:
    """Every cell a metro publishes with its nearest-submarket assignment (None cells dropped)."""
    claims = []
    for cell in coverage.metro_cells(city_id, res=DETAIL_RESOLUTION, max_ring=max_ring, max_dist_km=max_dist_km):
        assignment = coverage.assign_cell(cell, city_id, max_dist_km=max_dist_km)
        if assignment is not None:
            claims.append(assignment)
    return claims


def _plan_hash(
    city_id: str,
    anchors: tuple[str, ...],
    max_ring: int,
    max_dist_km: float,
    cells: tuple[PlannedCell, ...],
) -> str:
    from src.spatial.city_registry import REGISTRY, normalize_city

    reg = REGISTRY[normalize_city(city_id)]
    payload = {
        "authority": "k_ring",
        "detail_res": DETAIL_RESOLUTION,
        "max_ring": max_ring,
        "max_dist_km": max_dist_km,
        "anchors": list(anchors),
        "anchor_asset": _anchor_asset_sha(),
        "submarkets": sorted((m.name, m.lat, m.lng) for m in reg.submarkets.values()),
        "cells": [(c.cell, c.owner, c.label, c.in_anchor, c.owned) for c in cells],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@lru_cache(maxsize=4)
def plan_all(
    max_ring: int = coverage.DEFAULT_MAX_RING,
    max_dist_km: float = INTERPOLATION_BOUND_KM,
) -> dict[str, CoveragePlan]:
    """Every registered metro's plan, with cross-metro ownership resolved (INV-9)."""
    from src.spatial.city_registry import REGISTRY

    claims = {cid.value: _claims(cid.value, max_ring, max_dist_km) for cid in REGISTRY}
    # Owner of a contested cell = nearest submarket across claiming metros; city id breaks ties.
    best: dict[str, tuple[float, str]] = {}
    for city, assignments in claims.items():
        for a in assignments:
            candidate = (a.distance_km, city)
            if a.cell not in best or candidate < best[a.cell]:
                best[a.cell] = candidate

    plans: dict[str, CoveragePlan] = {}
    for city in sorted(claims):
        anchors = metro_anchor_ids(city)
        in_anchor_cells = _anchor_region_cells(anchors) if anchors else frozenset()
        cells = tuple(
            PlannedCell(
                cell=a.cell,
                owner=a.submarket,
                distance_km=a.distance_km,
                label="measured" if a.source == "center" else "interpolated",
                in_anchor=h3.cell_to_parent(a.cell, 7) in in_anchor_cells,
                owned=best[a.cell][1] == city,
                borough=a.borough,
            )
            for a in sorted(claims[city], key=lambda x: x.cell)
        )
        plans[city] = CoveragePlan(
            region_id=f"metro/{city}",
            city_id=city,
            authority="k_ring",
            anchor_ids=anchors,
            detail_res=DETAIL_RESOLUTION,
            cells=cells,
            golden_count=len(cells),
            owned_count=sum(c.owned for c in cells),
            measured_count=sum(c.label == "measured" for c in cells),
            in_anchor_count=sum(c.in_anchor for c in cells),
            plan_hash=_plan_hash(city, anchors, max_ring, max_dist_km, cells),
        )
    return plans


def plan_region(region_id: str, **kwargs: float) -> CoveragePlan:
    """The plan for ``metro/{city_id}``."""
    kind, _, city = region_id.partition("/")
    plans = plan_all(**kwargs)
    if kind != "metro" or city not in plans:
        raise KeyError(f"unknown coverage region {region_id!r}")
    return plans[city]


def roll_up(plan: CoveragePlan, to_res: int) -> tuple[str, ...]:
    """Sorted parents of the plan's cells at a coarser resolution."""
    if to_res >= plan.detail_res:
        raise ValueError(f"roll_up goes to a coarser resolution than {plan.detail_res}, got {to_res}")
    return tuple(sorted({h3.cell_to_parent(c.cell, to_res) for c in plan.cells}))
