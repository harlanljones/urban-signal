FIELD_MAP = {
    "job_id": ["Permit_Number"],
    "issuance_date": ["issuedate", "applydate", "lastchangedon"],
    "status": ["permit_status"],
    "job_type": ["Permit_Type", "Work_Class", "permit_desc"],
    "cost": ["permitvalue"],
    # ``address_street`` is the composed site address (compose_permit_address);
    # ``Addr1`` alone is only the house number.
    "address_street": ["address_street", "Addr1"],
    "zipcode": ["Zip"],
    "borough": ["City"],
}

CAPE_CORAL_FIELD_MAP = FIELD_MAP

"""Cape Coral–Fort Myers Metro (FL) — spatial registry and feed leaf.

This leaf declares:
- canonical city id (CAPE_CORAL_CITY_ID)
- metro bbox covering Cape Coral and Fort Myers
- a minimal divisions catalog with hand-authored bboxes
- 8 illustrative submarkets (centers, camera presets)
- a leaf-local DatasetSpec accessor for the verified public permits table

311 (2026-10-02): the City's ``311 Issues NonSpatial`` table, table 4 of the
``OpenData/OpenData`` MapServer whose layer 1 holds the permits. It keeps the
City's own requests since 2020-12-17, one row per request with WGS84 ``X``/
``Y`` columns and no geometry: 110,827 rows, 6,953 of them created in the 90
days to 2026-10-02, every one inside the metro box. The table is loaded in
one overnight cut; at 09:05Z on 10-02 its newest request was still the one
created at 02:09 EDT on 10-01, so the cadence is set to two days. 435 of
those 6,953 rows repeat a request exactly, so requests key on ``Issue_id``.
Its dates are Eastern with daylight saving, and the host already takes ANSI
literals for the permits. The poll reads the request's id, type, category,
status, dates and point; the site address and its parts, the title and both
free-text descriptions stay on the server. The ``311Issues`` point layer is
a second copy that also names the requester, and is not read.

DEEDS (2026-10-02): the Lee County Property Appraiser's parcels on the
County's ArcGIS Online org (``Lee_County_Parcels``, 565,114 polygons, edited
nightly), each with its latest sale (``S_1DATE``, ``S_1AMOUNT``, and the
instrument number ``S_1OR_NUM``; the three older sales are never newer). The
poll reads the sales dated in the 90 days before it, county-wide (6,765 on
2026-10-02), at each parcel's own ``LATITUDE``/``LONGITUDE``, and the clip
keeps those in the metro box (4,409). Sales reach the layer two to three
weeks after their date, and the window re-reads them. An instrument can
convey several parcels, so rows key on parcel, date and instrument. The
owner block (``O_*``) and the legal description are never selected.
"""

from typing import Any

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Canonical, stable city id string for Cape Coral–Fort Myers metro.
CAPE_CORAL_CITY_ID: str = "cape_coral"

# Metro bbox — permissive envelope spanning Cape Coral and Fort Myers cores
# and adjacent North Fort Myers. Chosen to comfortably contain all declared
# division bboxes and submarket centers.
CAPE_CORAL_METRO_BBOX: dict[str, float] = {
    "min_lat": 26.40,
    "max_lat": 26.80,
    "min_lng": -82.15,
    "max_lng": -81.70,
}


def is_in_cape_coral_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Greater Cape Coral–Fort Myers bounds."""
    if lat is None or lng is None:
        return False
    return (
        CAPE_CORAL_METRO_BBOX["min_lat"] <= lat <= CAPE_CORAL_METRO_BBOX["max_lat"]
        and CAPE_CORAL_METRO_BBOX["min_lng"] <= lng <= CAPE_CORAL_METRO_BBOX["max_lng"]
    )


def compose_permit_address(row: dict[str, Any]) -> str | None:
    """Join the permit layer's site-address parts into one geocode query.

    ``Addr1`` holds only the house number; the street is split across
    ``Predir``, ``Addr2`` (the name), ``Street_Type`` and ``Post_Dir``, and
    ``Addr3`` is the literal ``Parcel``. Form: ``{Addr1} {Predir} {Addr2}
    {Street_Type} {Post_Dir}, {City}, {State} {Zip}``; ``City`` is not always
    Cape Coral (North Fort Myers rows carry their own). Returns ``None``
    without a street name, so the geocoder is never asked for a bare number.
    """

    def _part(key: str) -> str:
        val = row.get(key)
        return str(val).strip() if val is not None else ""

    if not _part("Addr2"):
        return None
    street = " ".join(
        part
        for part in (
            _part("Addr1"),
            _part("Predir"),
            _part("Addr2"),
            _part("Street_Type"),
            _part("Post_Dir"),
        )
        if part
    )
    place = f"{_part('City') or 'Cape Coral'}, {_part('State') or 'FL'}"
    zipcode = _part("Zip")
    return f"{street}, {place} {zipcode}" if zipcode else f"{street}, {place}"


# Division bounding boxes — coarse, disjoint-ish envelopes around key areas.
# These are hand-authored for stable resolution, not cadastral boundaries.
CAPE_CORAL_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "CAPE_CORE_WATERFRONT": {"min_lat": 26.55, "max_lat": 26.65, "min_lng": -82.05, "max_lng": -81.92},
    "CAPE_SW_ISLES": {"min_lat": 26.52, "max_lat": 26.60, "min_lng": -82.10, "max_lng": -82.00},
    "CAPE_NW_GATOR": {"min_lat": 26.60, "max_lat": 26.72, "min_lng": -82.10, "max_lng": -81.98},
    "FORT_MYERS_CORE": {"min_lat": 26.60, "max_lat": 26.67, "min_lng": -81.91, "max_lng": -81.83},
    "NORTH_FORT_MYERS": {"min_lat": 26.67, "max_lat": 26.76, "min_lng": -81.95, "max_lng": -81.82},
}


CAPE_CORAL_SUBMARKETS: dict[str, SubmarketMeta] = {
    # -----------------------------------------------------------------------
    # CAPE_CORE_WATERFRONT (3)
    # -----------------------------------------------------------------------
    "Cape Coral Pkwy & Marina": SubmarketMeta(
        name="Cape Coral Pkwy & Marina",
        borough="CAPE_CORE_WATERFRONT",
        lat=26.562,
        lng=-81.948,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.86,
        capex=7200000.0,
        permit_vel=34.0,
        shift_ratio=1.42,
        sla=55.0,
        description="Cape Coral Parkway corridor and yacht club/marina district with steady residential reinvestment.",
        city_id=CAPE_CORAL_CITY_ID,
    ),
    "Bimini Basin & Downtown": SubmarketMeta(
        name="Bimini Basin & Downtown",
        borough="CAPE_CORE_WATERFRONT",
        lat=26.563,
        lng=-81.956,
        zoom=15.0,
        pitch=52.0,
        base_lims=0.88,
        capex=7800000.0,
        permit_vel=36.0,
        shift_ratio=1.48,
        sla=58.0,
        description="Downtown Cape Coral and Bimini Basin waterfront infill with mixed-use and hospitality momentum.",
        city_id=CAPE_CORAL_CITY_ID,
    ),
    "Pelican Blvd & Mohawk": SubmarketMeta(
        name="Pelican Blvd & Mohawk",
        borough="CAPE_CORE_WATERFRONT",
        lat=26.580,
        lng=-81.976,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.80,
        capex=5600000.0,
        permit_vel=28.0,
        shift_ratio=1.35,
        sla=50.0,
        description="Southwest grid of canals with teardowns and substantial single-family rebuild permits.",
        city_id=CAPE_CORAL_CITY_ID,
    ),
    # -----------------------------------------------------------------------
    # CAPE_SW_ISLES (2)
    # -----------------------------------------------------------------------
    "Southwest Isles & Cape Harbour": SubmarketMeta(
        name="Southwest Isles & Cape Harbour",
        borough="CAPE_SW_ISLES",
        lat=26.540,
        lng=-82.026,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.82,
        capex=6200000.0,
        permit_vel=30.0,
        shift_ratio=1.40,
        sla=54.0,
        description="Cape Harbour and deepwater canal neighborhoods with high-value renovation and pool permits.",
        city_id=CAPE_CORAL_CITY_ID,
    ),
    "Surfside & Veterans Pkwy": SubmarketMeta(
        name="Surfside & Veterans Pkwy",
        borough="CAPE_SW_ISLES",
        lat=26.575,
        lng=-82.030,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=4800000.0,
        permit_vel=24.0,
        shift_ratio=1.28,
        sla=46.0,
        description="Retail and residential mix along Veterans Parkway with steady small-scale permits.",
        city_id=CAPE_CORAL_CITY_ID,
    ),
    # -----------------------------------------------------------------------
    # CAPE_NW_GATOR (1)
    # -----------------------------------------------------------------------
    "Northwest Cape & Burnt Store": SubmarketMeta(
        name="Northwest Cape & Burnt Store",
        borough="CAPE_NW_GATOR",
        lat=26.655,
        lng=-82.045,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.70,
        capex=3800000.0,
        permit_vel=18.0,
        shift_ratio=1.18,
        sla=40.0,
        description="Exurban expansion corridor toward Burnt Store Road with new single-family starts.",
        city_id=CAPE_CORAL_CITY_ID,
    ),
    # -----------------------------------------------------------------------
    # FORT_MYERS_CORE (1)
    # -----------------------------------------------------------------------
    "Downtown Fort Myers River District": SubmarketMeta(
        name="Downtown Fort Myers River District",
        borough="FORT_MYERS_CORE",
        lat=26.642,
        lng=-81.871,
        zoom=15.0,
        pitch=52.0,
        base_lims=0.88,
        capex=8000000.0,
        permit_vel=35.0,
        shift_ratio=1.50,
        sla=60.0,
        description="Historic riverfront core with mid-rise infill and hospitality redevelopment.",
        city_id=CAPE_CORAL_CITY_ID,
    ),
    # -----------------------------------------------------------------------
    # NORTH_FORT_MYERS (1)
    # -----------------------------------------------------------------------
    "North Fort Myers & Hancock Bridge": SubmarketMeta(
        name="North Fort Myers & Hancock Bridge",
        borough="NORTH_FORT_MYERS",
        lat=26.685,
        lng=-81.890,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.74,
        capex=4200000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=44.0,
        description="Commercial strips and older subdivisions north of the river with moderate permit activity.",
        city_id=CAPE_CORAL_CITY_ID,
    ),
}


CAPE_CORAL_DIVISIONS: dict[str, BoroughMeta] = {
    "CAPE_CORE_WATERFRONT": BoroughMeta(
        name="CAPE_CORE_WATERFRONT",
        center_lat=26.568,
        center_lng=-81.957,
        zoom=13.5,
        bbox=CAPE_CORAL_DIVISION_BBOXES["CAPE_CORE_WATERFRONT"],
        submarkets=[k for k, v in CAPE_CORAL_SUBMARKETS.items() if v.borough == "CAPE_CORE_WATERFRONT"],
        city_id=CAPE_CORAL_CITY_ID,
    ),
    "CAPE_SW_ISLES": BoroughMeta(
        name="CAPE_SW_ISLES",
        center_lat=26.555,
        center_lng=-82.026,
        zoom=13.0,
        bbox=CAPE_CORAL_DIVISION_BBOXES["CAPE_SW_ISLES"],
        submarkets=[k for k, v in CAPE_CORAL_SUBMARKETS.items() if v.borough == "CAPE_SW_ISLES"],
        city_id=CAPE_CORAL_CITY_ID,
    ),
    "CAPE_NW_GATOR": BoroughMeta(
        name="CAPE_NW_GATOR",
        center_lat=26.665,
        center_lng=-82.030,
        zoom=12.5,
        bbox=CAPE_CORAL_DIVISION_BBOXES["CAPE_NW_GATOR"],
        submarkets=[k for k, v in CAPE_CORAL_SUBMARKETS.items() if v.borough == "CAPE_NW_GATOR"],
        city_id=CAPE_CORAL_CITY_ID,
    ),
    "FORT_MYERS_CORE": BoroughMeta(
        name="FORT_MYERS_CORE",
        center_lat=26.642,
        center_lng=-81.871,
        zoom=13.5,
        bbox=CAPE_CORAL_DIVISION_BBOXES["FORT_MYERS_CORE"],
        submarkets=[k for k, v in CAPE_CORAL_SUBMARKETS.items() if v.borough == "FORT_MYERS_CORE"],
        city_id=CAPE_CORAL_CITY_ID,
    ),
    "NORTH_FORT_MYERS": BoroughMeta(
        name="NORTH_FORT_MYERS",
        center_lat=26.710,
        center_lng=-81.890,
        zoom=12.5,
        bbox=CAPE_CORAL_DIVISION_BBOXES["NORTH_FORT_MYERS"],
        submarkets=[k for k, v in CAPE_CORAL_SUBMARKETS.items() if v.borough == "NORTH_FORT_MYERS"],
        city_id=CAPE_CORAL_CITY_ID,
    ),
}


# Leaf-local feed registration ------------------------------------------------

# Verified public permits table (address-only; ADR-0004 geocoding in registry).
# PERMITS only here: 311 and deeds read the City's 311 issues table and the
# Lee County parcels, which the corpus registers.
CAPE_CORAL_PERMITS_ENDPOINT = "https://capeims.capecoral.gov/arcgis/rest/services/OpenData/OpenData/MapServer/1"

CAPE_CORAL_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": CAPE_CORAL_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "issuedate",
        "id_keys": ["Permit_Number", "objectid"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 7,
            "order_by": "issuedate DESC",
            # 33 of 64,910 rows carry issue dates past 2026-10-01 (as far out
            # as the year 2610); newest-first reads would start with them.
            "where": "issuedate <= CURRENT_TIMESTAMP",
            "needs_geocode": True,
            "geocode_context": "Cape Coral, FL",
            "scope": (
                "Cape Coral–Fort Myers building permits (address-only; the "
                "site address is composed from its parts and geocoded)"
            ),
            "field_map": CAPE_CORAL_FIELD_MAP,
            "non_spatial": True,
        },
    },
}


def get_cape_coral_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset`` for Cape Coral."""
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in CAPE_CORAL_FEED_SPECS:
        available = ", ".join(sorted(CAPE_CORAL_FEED_SPECS))
        raise KeyError(f"'{CAPE_CORAL_CITY_ID}' has no '{feed_name}' feed; available: {available}")
    payload = CAPE_CORAL_FEED_SPECS[feed_name]
    from src.config import settings

    extra_kwargs = {k: v for k, v in payload.get("extra", {}).items() if k != "scope"}

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


# Registration object consumed by the derived registry aggregator.
from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=CAPE_CORAL_METRO_BBOX,
    division_bboxes=CAPE_CORAL_DIVISION_BBOXES,
    submarkets=CAPE_CORAL_SUBMARKETS,
    divisions=CAPE_CORAL_DIVISIONS,
    contains=is_in_cape_coral_metro,
)

