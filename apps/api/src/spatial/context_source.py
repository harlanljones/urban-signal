"""Geographic context-source registry (US-435).

File-based geographic context (Census LODES, ZBP, ...) is not a municipal event
feed: it has no per-city endpoint, no watermark column, and no paginated
ingestion contract, so forcing it into ``DatasetSpec`` would be a lie the
interlock gate would then have to bless. Each context source registers here
instead, with its own contract:

* a stable source ID, version/vintage, and attribution;
* the geographic assignment method (how source geography becomes H3 cells);
* the supported H3 resolutions;
* per-metric metadata including nullability and suppression handling;
* the builder module + revision that produced a given artifact;
* whether official checksums are required before promotion.

LODES is implemented (``src.export.national_builder``). ZBP is registered with
its assignment method and suppression contract proven by ``zbp_signal`` helpers,
but its builder is not implemented yet — ``implemented`` stays False until a
ZBP build produces a validated artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.export.national_builder import BUILDER_REVISION as LODES_BUILDER_REVISION


class ContextSourceId(str, Enum):
    """Stable IDs for geographic context sources."""

    LODES = "lodes"
    ZBP = "zbp"
    OVERTURE_BUILDINGS = "overture_buildings"
    OVERTURE_PLACES = "overture_places"


@dataclass
class ContextMetricSpec:
    """One published measure of a context source."""

    name: str
    description: str
    nullable: bool = True
    suppression: str = "null_preserved"


@dataclass
class ContextSourceSpec:
    """Publication contract for one geographic context source."""

    source: ContextSourceId
    version: str
    vintage_year: int | None
    attribution: str
    assignment_method: str
    assignment_description: str
    supported_resolutions: tuple[int, ...]
    metrics: list[ContextMetricSpec] = field(default_factory=list)
    suppression_policy: str = ""
    builder_module: str = ""
    builder_revision: str = ""
    requires_checksum: bool = True
    implemented: bool = True
    notes: str = ""


LODES_ATTRIBUTION = (
    "U.S. Census Bureau, Longitudinal Employer-Household Dynamics (LEHD) "
    "Origin-Destination Employment Statistics (LODES), public domain."
)

ZBP_ATTRIBUTION = (
    "U.S. Census Bureau, ZIP Code Business Patterns (ZBP), public domain."
)

# Buildings conflates OpenStreetMap (primary source) with other open/ML-derived
# footprint datasets and is published under ODbL 1.0 — attribution *and*
# share-alike on derivative databases (US-443).
OVERTURE_BUILDINGS_ATTRIBUTION = (
    "Contains information from the Overture Maps Foundation buildings theme, "
    "which is made available under the Open Database License (ODbL) 1.0, "
    "including data \u00a9 OpenStreetMap contributors. Any derived database is "
    "licensed under ODbL 1.0 (share-alike)."
)

# Places carries no OpenStreetMap data and is published under a
# CDLA-Permissive-2.0 / Apache-2.0 / CC0 mix across its contributing sources,
# with no share-alike obligation (US-443).
OVERTURE_PLACES_ATTRIBUTION = (
    "Contains information from the Overture Maps Foundation places theme, "
    "made available under CDLA-Permissive-2.0, Apache-2.0, and CC0-1.0 across "
    "its contributing sources."
)

CONTEXT_SOURCES: dict[ContextSourceId, ContextSourceSpec] = {
    ContextSourceId.LODES: ContextSourceSpec(
        source=ContextSourceId.LODES,
        version="v8",
        vintage_year=2023,
        attribution=LODES_ATTRIBUTION,
        assignment_method="census_block_internal_point",
        assignment_description=(
            "Each LODES block is placed at its crosswalk internal point "
            "(blklatdd/blklondd) and assigned to the containing H3 cell. "
            "This is a representative-point approximation, not polygon "
            "interpolation."
        ),
        supported_resolutions=(4, 5, 6),
        metrics=[
            ContextMetricSpec(
                name="jobs_c000",
                description="Workplace jobs (WAC C000) summed over contributing blocks.",
            ),
            ContextMetricSpec(
                name="workers_c000",
                description="Resident workers (RAC C000) summed over contributing blocks.",
            ),
            ContextMetricSpec(
                name="blocks_wac",
                description="Count of contributing WAC blocks (observed-contributor count).",
                suppression="count",
            ),
            ContextMetricSpec(
                name="blocks_rac",
                description="Count of contributing RAC blocks (observed-contributor count).",
                suppression="count",
            ),
        ],
        suppression_policy=(
            "Hexes with no contributing blocks stay null; WAC and RAC are "
            "independent, so a missing family leaves the other intact. "
            "Nulls are never zero-filled."
        ),
        builder_module="src.export.national_builder",
        builder_revision=LODES_BUILDER_REVISION,
        requires_checksum=True,
        implemented=True,
    ),
    ContextSourceId.ZBP: ContextSourceSpec(
        source=ContextSourceId.ZBP,
        version="zbp",
        vintage_year=None,
        attribution=ZBP_ATTRIBUTION,
        assignment_method="zip_to_dominant_zcta_representative_point",
        assignment_description=(
            "Each ZBP ZIP is resolved to its dominant ZCTA (HUD USPS crosswalk) "
            "and placed at the ZCTA representative point. Representative-point "
            "approximation, not polygon interpolation."
        ),
        supported_resolutions=(7, 8, 9),
        metrics=[
            ContextMetricSpec(
                name="establishments",
                description="Establishment count; suppressed values carried as null.",
                suppression="withheld_as_null",
            ),
            ContextMetricSpec(
                name="employment",
                description="Employment; suppressed values carried as null.",
                suppression="withheld_as_null",
            ),
            ContextMetricSpec(
                name="payroll_annual",
                description="Annual payroll; suppressed values carried as null.",
                suppression="withheld_as_null",
            ),
            ContextMetricSpec(
                name="suppressed_estab",
                description="Count of suppressed establishment contributors.",
                suppression="count",
            ),
            ContextMetricSpec(
                name="suppressed_emp",
                description="Count of suppressed employment contributors.",
                suppression="count",
            ),
            ContextMetricSpec(
                name="suppressed_payroll",
                description="Count of suppressed payroll contributors.",
                suppression="count",
            ),
        ],
        suppression_policy=(
            "Confidentiality flags (D/S/N/X/V/Z) are carried as unknown (null), "
            "never coerced to zero. Metrics with zero observed contributors "
            "stay null even when suppressed contributors exist."
        ),
        builder_module="src.spatial.zbp_signal",
        builder_revision="0",
        requires_checksum=True,
        implemented=False,
        notes="Helpers proven in src.spatial.zbp_signal; no builder yet.",
    ),
    ContextSourceId.OVERTURE_BUILDINGS: ContextSourceSpec(
        source=ContextSourceId.OVERTURE_BUILDINGS,
        version="release-snapshot",
        vintage_year=None,
        attribution=OVERTURE_BUILDINGS_ATTRIBUTION,
        assignment_method="footprint_centroid",
        assignment_description=(
            "Each building footprint's centroid is assigned to the containing "
            "H3 res-9 cell (polygon-intersection assignment was also "
            "considered per the ticket, but centroid is O(1) per building and "
            "never double-counts a footprint split across a hex boundary)."
        ),
        supported_resolutions=(9,),
        metrics=[
            ContextMetricSpec(
                name="building_count",
                description="Total buildings assigned to the hex.",
                suppression="count",
            ),
            ContextMetricSpec(
                name="total_footprint_area_m2",
                description="Sum of geodesic building footprint areas in the hex, in m^2.",
            ),
            ContextMetricSpec(
                name="avg_height_m",
                description="Mean building height where reported; null if no building in the hex reports one.",
            ),
            ContextMetricSpec(
                name="class_mix",
                description="Fraction residential/commercial/industrial/other, sums to 1.0.",
            ),
            ContextMetricSpec(
                name="building_density_weight",
                description=(
                    "Building count normalized so weights across a query batch sum to "
                    "1.0; the dasymetric mask consumed by the US-438 ACS join (Ticket 3)."
                ),
                nullable=False,
            ),
        ],
        suppression_policy=(
            "Hexes with no buildings are simply absent from the result; no "
            "zero-filling across the full metro grid is performed here."
        ),
        builder_module="src.spatial.overture_pipeline",
        builder_revision="1",
        requires_checksum=False,
        implemented=True,
        notes=(
            "ODbL 1.0 share-alike: any derived database built from this source "
            "must itself be released under ODbL 1.0 with attribution."
        ),
    ),
    ContextSourceId.OVERTURE_PLACES: ContextSourceSpec(
        source=ContextSourceId.OVERTURE_PLACES,
        version="release-snapshot",
        vintage_year=None,
        attribution=OVERTURE_PLACES_ATTRIBUTION,
        assignment_method="point_geometry",
        assignment_description=(
            "Each place's point geometry is assigned directly to its "
            "containing H3 res-9 cell."
        ),
        supported_resolutions=(9,),
        metrics=[
            ContextMetricSpec(
                name="poi_density",
                description="Total POI count assigned to the hex.",
                suppression="count",
            ),
            ContextMetricSpec(
                name="poi_category_mix",
                description=(
                    "Fraction restaurants/retail/services/nightlife/healthcare/"
                    "education/other, sums to 1.0."
                ),
            ),
            ContextMetricSpec(
                name="commercial_churn",
                description=(
                    "Net POI id-set change between two consecutive releases "
                    "(appearances minus disappearances) per hex."
                ),
            ),
        ],
        suppression_policy=(
            "Hexes with no places are simply absent from the result; no "
            "zero-filling across the full metro grid is performed here."
        ),
        builder_module="src.spatial.overture_pipeline",
        builder_revision="1",
        requires_checksum=False,
        implemented=True,
        notes="No share-alike obligation; contains no OpenStreetMap data.",
    ),
}


def get_context_source(source: ContextSourceId) -> ContextSourceSpec:
    """Look up a context source spec, with a readable error."""
    try:
        return CONTEXT_SOURCES[source]
    except KeyError as exc:
        raise KeyError(
            f"context source {source!r} is not registered; known sources: "
            f"{sorted(s.value for s in CONTEXT_SOURCES)}"
        ) from exc
