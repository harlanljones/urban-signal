"""Buffalo, NY spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Buffalo
(Erie County, Western NY).

Buffalo is a ONE-FEED PARTIAL metro: SLA (Restaurant Licenses on the city's
Socrata portal ``data.buffalony.gov``, Tier 1). PERMITS is Tier 3 — every
permit dataset in the 106-item catalog fails with Socrata ``Cannot read rows
for view`` despite fresh catalog ``updatedAt`` stamps (backends gone);
COMPLAINTS_311 is Tier 3 — the CRM extracts are frozen at 2024-05-10; DEEDS
is Tier 3 — no transaction stream in the city portal (Erie County records,
no anonymous bulk API). None are registered.

Live-probe caveats that define this leaf (probed 2026-08-27, re-probed live
2026-08-27 implementation wave, US-349):

* SLA watermark is ``issdttm`` (renewal/issuance datetime; newest row on the
  re-probe = 2026-08-20). Socrata orders NULLs first on
  ``$order=issdttm DESC`` — only 2 of 1,429 rows are null, but the spec
  carries ``where="issdttm IS NOT NULL"`` so the watermark read never lands
  on a null row. ``expdttm`` (max 2027-09-30) is an *expiration* date and
  ``licensedttm`` (original license, some 2001-2007) is NOT the renewal
  stream — neither is a watermark.
* ``licenseno`` repeats across rows (renewals emit one row per issuance;
  e.g. ``RST25-10057856`` twice) — ``uniqkey`` is the row-unique identifier
  and renewal rows are distinct events keyed by ``licenseno`` + ``issdttm``.
* Coordinates: native ``latitude``/``longitude`` are WGS84 degrees and match
  the ``location`` Point on every probed row — but ``gpsx``/``gpsy`` are
  MIXED CRS in one live dataset (WGS84 degrees on some rows, NY State Plane
  feet on others), so they are never map candidates. No ADR 0004 dependency
  (geocode completeness 500/500 on the newest 500 rows).
* The source-maintained ``neighborhood`` column ("Elmwood Bryant",
  "Genesee-Moselle", "North Park", …) passes through as the row's source
  neighborhood.
* Cadence: 23 issuances in the 7 days before probe, 253 in 60 days —
  event-driven, production-grade.
"""

from typing import Any

from src.producers.field_maps_buffalo import SLA_FIELD_MAP
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

BUFFALO_CITY_ID: str = "buffalo"

# City of Buffalo. Permissive enough to hold the Canalside waterfront
# (42.877, -78.881), the Elmwood Village spine, Black Rock on the Niagara
# River edge (-78.91), University Heights at the Amherst line (42.958), the
# Broadway-Fillmore East Side corridor, and the Kaisertown edge (-78.80).
BUFFALO_METRO_BBOX: dict[str, float] = {
    "min_lat": 42.82,
    "max_lat": 42.97,
    "min_lng": -78.93,
    "max_lng": -78.78,
}

# 6 Buffalo divisions. Hand-authored; borough resolution at ingest
# comes from coordinates via get_division_for_coordinate, so bboxes need only
# be sane and contain their own submarket centers.
BUFFALO_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_WATERFRONT": {
        "min_lat": 42.870,
        "max_lat": 42.891,
        "min_lng": -78.890,
        "max_lng": -78.856,
    },
    "WEST_SIDE": {
        "min_lat": 42.892,
        "max_lat": 42.917,
        "min_lng": -78.892,
        "max_lng": -78.866,
    },
    "NORTH_BUFFALO": {
        "min_lat": 42.931,
        "max_lat": 42.950,
        "min_lng": -78.892,
        "max_lng": -78.862,
    },
    "BLACK_ROCK": {
        "min_lat": 42.928,
        "max_lat": 42.947,
        "min_lng": -78.918,
        "max_lng": -78.890,
    },
    "EAST_SIDE": {
        "min_lat": 42.884,
        "max_lat": 42.904,
        "min_lng": -78.852,
        "max_lng": -78.818,
    },
    "UNIVERSITY_HEIGHTS": {
        "min_lat": 42.950,
        "max_lat": 42.967,
        "min_lng": -78.836,
        "max_lng": -78.806,
    },
}


def is_in_buffalo_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Buffalo city bounds."""
    if lat is None or lng is None:
        return False
    return (
        BUFFALO_METRO_BBOX["min_lat"] <= lat <= BUFFALO_METRO_BBOX["max_lat"]
        and BUFFALO_METRO_BBOX["min_lng"] <= lng <= BUFFALO_METRO_BBOX["max_lng"]
    )


is_in_greater_buffalo_metro = is_in_buffalo_metro


BUFFALO_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_WATERFRONT (2)
    # =======================================================================
    "Canalside": SubmarketMeta(
        name="Canalside",
        borough="DOWNTOWN_WATERFRONT",
        lat=42.8772,
        lng=-78.8811,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.82,
        capex=6400000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=55.0,
        description="Erie Canal terminus waterfront with the Cobblestone entertainment district, KeyBank Center adjacency, and heritage-interpreted infill along the recreated canals.",
        city_id="buffalo",
    ),
    "Larkinville": SubmarketMeta(
        name="Larkinville",
        borough="DOWNTOWN_WATERFRONT",
        lat=42.8845,
        lng=-78.8643,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.83,
        capex=6800000.0,
        permit_vel=34.0,
        shift_ratio=1.48,
        sla=56.0,
        description="Larkin Square and the Exchange Street corridor with adaptive reuse of the historic Larkin complex, food-truck programming, and downtown-adjacent office conversion.",
        city_id="buffalo",
    ),
    # =======================================================================
    # WEST_SIDE (2)
    # =======================================================================
    "Allentown": SubmarketMeta(
        name="Allentown",
        borough="WEST_SIDE",
        lat=42.8997,
        lng=-78.8790,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.85,
        capex=6100000.0,
        permit_vel=30.0,
        shift_ratio=1.47,
        sla=55.0,
        description="Historic preservation district along Allen Street with galleries, music venues, Italianate rowhouses, and the Cottage District's Victorian stock renovation.",
        city_id="buffalo",
    ),
    "Elmwood Village": SubmarketMeta(
        name="Elmwood Village",
        borough="WEST_SIDE",
        lat=42.9094,
        lng=-78.8772,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.88,
        capex=7200000.0,
        permit_vel=33.0,
        shift_ratio=1.50,
        sla=58.0,
        description="Elmwood Avenue retail spine between the Olmsted parkways and Delaware Park with the Bidwell farmers market, mixed-use storefronts, and the metro's strongest walk-up rents.",
        city_id="buffalo",
    ),
    # =======================================================================
    # NORTH_BUFFALO (1)
    # =======================================================================
    "Hertel Avenue": SubmarketMeta(
        name="Hertel Avenue",
        borough="NORTH_BUFFALO",
        lat=42.9408,
        lng=-78.8772,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.86,
        capex=6600000.0,
        permit_vel=31.0,
        shift_ratio=1.48,
        sla=56.0,
        description="The Hertel Strip in North Buffalo with its Italian-heritage commercial row, parkside bungalow belts, and restaurant-led storefront revitalization.",
        city_id="buffalo",
    ),
    # =======================================================================
    # BLACK_ROCK (1)
    # =======================================================================
    "Black Rock": SubmarketMeta(
        name="Black Rock",
        borough="BLACK_ROCK",
        lat=42.9374,
        lng=-78.9019,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.79,
        capex=5200000.0,
        permit_vel=26.0,
        shift_ratio=1.40,
        sla=50.0,
        description="Historic 19th-century village on the Niagara River edge (annexed 1854) with the Amherst Street corridor, Scajaquada Creek frontage, and early-stage riverfront reinvestment.",
        city_id="buffalo",
    ),
    # =======================================================================
    # EAST_SIDE (1)
    # =======================================================================
    "Broadway-Fillmore": SubmarketMeta(
        name="Broadway-Fillmore",
        borough="EAST_SIDE",
        lat=42.8940,
        lng=-78.8346,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.78,
        capex=5400000.0,
        permit_vel=28.0,
        shift_ratio=1.42,
        sla=51.0,
        description="Broadway Market and the Fillmore commercial row with Polish-heritage housing stock, stabilization-level values, and corridor redevelopment groundwork on the East Side.",
        city_id="buffalo",
    ),
    # =======================================================================
    # UNIVERSITY_HEIGHTS (1)
    # =======================================================================
    "University Heights": SubmarketMeta(
        name="University Heights",
        borough="UNIVERSITY_HEIGHTS",
        lat=42.9585,
        lng=-78.8218,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.80,
        capex=5600000.0,
        permit_vel=29.0,
        shift_ratio=1.43,
        sla=52.0,
        description="UB South Campus district at the Main Street metro-rail terminus with the student-rental belt, Sugar City creative reuse, and Amherst-line demand spillover.",
        city_id="buffalo",
    ),
}


BUFFALO_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_WATERFRONT": BoroughMeta(
        name="DOWNTOWN_WATERFRONT",
        center_lat=42.8805,
        center_lng=-78.8727,
        zoom=14.0,
        bbox=BUFFALO_DIVISION_BBOXES["DOWNTOWN_WATERFRONT"],
        submarkets=[k for k, v in BUFFALO_SUBMARKETS.items() if v.borough == "DOWNTOWN_WATERFRONT"],
        city_id="buffalo",
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=42.9045,
        center_lng=-78.8781,
        zoom=14.0,
        bbox=BUFFALO_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in BUFFALO_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id="buffalo",
    ),
    "NORTH_BUFFALO": BoroughMeta(
        name="NORTH_BUFFALO",
        center_lat=42.9408,
        center_lng=-78.8772,
        zoom=14.0,
        bbox=BUFFALO_DIVISION_BBOXES["NORTH_BUFFALO"],
        submarkets=[k for k, v in BUFFALO_SUBMARKETS.items() if v.borough == "NORTH_BUFFALO"],
        city_id="buffalo",
    ),
    "BLACK_ROCK": BoroughMeta(
        name="BLACK_ROCK",
        center_lat=42.9374,
        center_lng=-78.9019,
        zoom=14.0,
        bbox=BUFFALO_DIVISION_BBOXES["BLACK_ROCK"],
        submarkets=[k for k, v in BUFFALO_SUBMARKETS.items() if v.borough == "BLACK_ROCK"],
        city_id="buffalo",
    ),
    "EAST_SIDE": BoroughMeta(
        name="EAST_SIDE",
        center_lat=42.8940,
        center_lng=-78.8346,
        zoom=13.5,
        bbox=BUFFALO_DIVISION_BBOXES["EAST_SIDE"],
        submarkets=[k for k, v in BUFFALO_SUBMARKETS.items() if v.borough == "EAST_SIDE"],
        city_id="buffalo",
    ),
    "UNIVERSITY_HEIGHTS": BoroughMeta(
        name="UNIVERSITY_HEIGHTS",
        center_lat=42.9585,
        center_lng=-78.8218,
        zoom=14.0,
        bbox=BUFFALO_DIVISION_BBOXES["UNIVERSITY_HEIGHTS"],
        submarkets=[k for k, v in BUFFALO_SUBMARKETS.items() if v.borough == "UNIVERSITY_HEIGHTS"],
        city_id="buffalo",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed and live re-probed 2026-08-27. Register SLA ONLY — do not register
# the broken permit backends (Cannot read rows for view), the 311 extracts
# frozen at 2024-05-10, the contractor-license dataset (no issuance date),
# or any sibling view.
# ---------------------------------------------------------------------------
BUFFALO_SLA_ENDPOINT = "https://data.buffalony.gov/resource/4pp3-qkuj.json"

BUFFALO_FEED_SPECS: dict[str, dict[str, object]] = {
    "sla": {
        "endpoint": BUFFALO_SLA_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "issdttm",
        "id_keys": ["uniqkey", "licenseno", "aplickey"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 7,
            "needs_geocode": False,
            "where": "issdttm IS NOT NULL",
            "order_by": "issdttm DESC",
            "scope": (
                "Restaurant Licenses (RST/RTO + sibling codes) renewal/issuance "
                "stream (native WGS84 latitude/longitude; gpsx/gpsy mixed CRS "
                "and never candidates; uniqkey row-unique across renewal rows; "
                "Socrata NULLs-first ordering demands the issdttm IS NOT NULL "
                "guard; expdttm/licensedttm/statusdttm never watermarks)"
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
}


def get_buffalo_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Buffalo feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in BUFFALO_FEED_SPECS:
        available = ", ".join(sorted(BUFFALO_FEED_SPECS))
        raise KeyError(
            f"'{BUFFALO_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = BUFFALO_FEED_SPECS[feed_name]
    extra_kwargs = {
        k: v for k, v in payload.get("extra", {}).items() if k != "scope"
    }
    return DatasetSpec(
        endpoint=payload["endpoint"],
        platform=payload["platform"],
        watermark_col=payload["watermark_col"],
        id_keys=payload["id_keys"],
        topic=getattr(settings, payload["topic_key"]),
        interval_seconds=payload["interval_seconds"],
        producer_key=payload["producer_key"],
        **extra_kwargs,
    )


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=BUFFALO_METRO_BBOX,
    division_bboxes=BUFFALO_DIVISION_BBOXES,
    submarkets=BUFFALO_SUBMARKETS,
    divisions=BUFFALO_DIVISIONS,
    contains=is_in_buffalo_metro,
)

__all__ = [
    "BUFFALO_CITY_ID",
    "BUFFALO_DIVISIONS",
    "BUFFALO_DIVISION_BBOXES",
    "BUFFALO_FEED_SPECS",
    "BUFFALO_METRO_BBOX",
    "BUFFALO_SLA_ENDPOINT",
    "BUFFALO_SUBMARKETS",
    "REGISTRATION",
    "get_buffalo_dataset",
    "is_in_buffalo_metro",
    "is_in_greater_buffalo_metro",
]
