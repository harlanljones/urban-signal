DEEDS_FIELD_MAP = {
    "doc_id": ["account_id_mdp_field_acctid"],
    "bbl": ["account_id_mdp_field_acctid"],
    "document_amount": ["sales_segment_1_consideration_mdp_field_considr1_sdat_field_90"],
    "recorded_date": ["sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89"],
    "address_street": ["mdp_street_address_mdp_field_address"],
    "incident_address": ["mdp_street_address_mdp_field_address"],
    "borough": ["mdp_street_address_city_mdp_field_city"],
    "zipcode": ["mdp_street_address_zip_code_mdp_field_zipcode"],
    "latitude": ["mdp_latitude_mdp_field_digycord_converted_to_wgs84"],
    "longitude": ["mdp_longitude_mdp_field_digxcord_converted_to_wgs84"],
}

FIELD_MAP = {
    "deeds": DEEDS_FIELD_MAP,
}

"""Frederick Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Frederick,
MD (county seat of Frederick County, at the foot of the Catoctin Mountains
— deliberately not overlapping the sibling Baltimore/Washington leaf boxes).

Feeds (probed 2026-09-30):

* DEEDS — Maryland SDAT real property assessments, Frederick County view
  (``opendata.maryland.gov`` Socrata ``gx8c-a963``, the family the Baltimore,
  Montgomery and Prince George's feeds read), filtered to the FREDERICK postal
  city. One row per account carries its latest sale (the date as text
  ``YYYY.MM.DD``, and the consideration); SDAT refreshes it monthly, about a
  month behind. It is read as a snapshot, newest sale first. Grantor names are
  never mapped. SDAT's own latitude and longitude supply coordinates. The
  ``Frederick_Parcels`` layer registered until 2026-09-30 never existed.
* PERMITS / SLA / 311 — absent from the public Frederick open-data surface;
  Tier 3, not registered.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

FREDERICK_CITY_ID: str = "frederick"

# Frederick metro bbox around the provided center (39.4143 / -77.4105). The
# north edge approaches the Catoctin foothills, the south edge the Monocacy
# River, the west edge the Middletown Valley, the east edge the Liberty
# Reservoir watershed — all kept clear of the Baltimore/Washington boxes.
FREDERICK_METRO_BBOX: dict[str, float] = {
    "min_lat": 39.35,
    "max_lat": 39.48,
    "min_lng": -77.47,
    "max_lng": -77.37,
}

# Registration-contract center: downtown Frederick (Carroll Creek / Market St).
FREDERICK_CENTER: dict[str, float] = {"lat": 39.4143, "lng": -77.4105}

# 5 Frederick Division Bounding Boxes (strictly nested inside the metro bbox)
FREDERICK_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_HISTORIC": {"min_lat": 39.40, "max_lat": 39.425, "min_lng": -77.425, "max_lng": -77.405},
    "NORTH_MARKET":     {"min_lat": 39.425, "max_lat": 39.46, "min_lng": -77.430, "max_lng": -77.400},
    "SOUTH_CREEK":      {"min_lat": 39.36, "max_lat": 39.40, "min_lng": -77.430, "max_lng": -77.400},
    "WEST_RIDGE":       {"min_lat": 39.39, "max_lat": 39.45, "min_lng": -77.470, "max_lng": -77.430},
    "EAST_GATE":        {"min_lat": 39.39, "max_lat": 39.45, "min_lng": -77.400, "max_lng": -77.370},
}


def is_in_frederick_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Frederick metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        FREDERICK_METRO_BBOX["min_lat"] <= lat <= FREDERICK_METRO_BBOX["max_lat"]
        and FREDERICK_METRO_BBOX["min_lng"] <= lng <= FREDERICK_METRO_BBOX["max_lng"]
    )


def is_in_frederick(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_frederick_metro`."""
    return is_in_frederick_metro(lat, lng)


# ---------------------------------------------------------------------------
# Frederick Submarket Registry (7 Submarkets Across 5 Divisions)
# ---------------------------------------------------------------------------

FREDERICK_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_HISTORIC (2 Submarkets)
    # =======================================================================
    "Downtown Frederick": SubmarketMeta(
        name="Downtown Frederick",
        borough="DOWNTOWN_HISTORIC",
        lat=39.4130,
        lng=-77.4110,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.86,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=56.0,
        description="The Carroll Creek / Market Street CBD with office-to-residential conversions, the Frederick anchor projects, and the city's densest mixed-use pipeline.",
        city_id="frederick",
    ),
    "Carroll Creek": SubmarketMeta(
        name="Carroll Creek",
        borough="DOWNTOWN_HISTORIC",
        lat=39.4100,
        lng=-77.4070,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.82,
        capex=4100000.0,
        permit_vel=24.0,
        shift_ratio=1.34,
        sla=46.0,
        description="The linear park district southwest of downtown with restored historic rowhouses and steady restoration trades.",
        city_id="frederick",
    ),
    # =======================================================================
    # NORTH_MARKET (2 Submarkets)
    # =======================================================================
    "North Market Street": SubmarketMeta(
        name="North Market Street",
        borough="NORTH_MARKET",
        lat=39.4320,
        lng=-77.4120,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.84,
        capex=4900000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=54.0,
        description="The north-end corridor of boutique retail, mansions cut into apartments, and high-turnover condo stock.",
        city_id="frederick",
    ),
    "Golden Mile": SubmarketMeta(
        name="Golden Mile",
        borough="NORTH_MARKET",
        lat=39.4450,
        lng=-77.4100,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.78,
        capex=3600000.0,
        permit_vel=22.0,
        shift_ratio=1.28,
        sla=42.0,
        description="The U.S. 40 commercial strip with auto-row reinvestment and investor renovation flow.",
        city_id="frederick",
    ),
    # =======================================================================
    # SOUTH_CREEK (1 Submarket)
    # =======================================================================
    "South End": SubmarketMeta(
        name="South End",
        borough="SOUTH_CREEK",
        lat=39.3850,
        lng=-77.4150,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.70,
        capex=3000000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=40.0,
        description="The Monocacy-side wards south of downtown with craftsman-bungalow stock and block-by-block reinvestment.",
        city_id="frederick",
    ),
    # =======================================================================
    # WEST_RIDGE (1 Submarket)
    # =======================================================================
    "West Side": SubmarketMeta(
        name="West Side",
        borough="WEST_RIDGE",
        lat=39.4150,
        lng=-77.4500,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.74,
        capex=3300000.0,
        permit_vel=21.0,
        shift_ratio=1.26,
        sla=42.0,
        description="The west-side grid toward the Middletown Valley with solid pre-war housing stock and steady acquisition flow.",
        city_id="frederick",
    ),
    # =======================================================================
    # EAST_GATE (1 Submarket)
    # =======================================================================
    "East Gate": SubmarketMeta(
        name="East Gate",
        borough="EAST_GATE",
        lat=39.4150,
        lng=-77.3850,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.68,
        capex=2800000.0,
        permit_vel=17.0,
        shift_ratio=1.20,
        sla=36.0,
        description="The east-side gateway toward the Liberty watershed with the city's lowest sale prices and heaviest vacancy-to-acquisition conversion.",
        city_id="frederick",
    ),
}


# ---------------------------------------------------------------------------
# Frederick Divisions Catalog
# ---------------------------------------------------------------------------

FREDERICK_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_HISTORIC": BoroughMeta(
        name="DOWNTOWN_HISTORIC",
        center_lat=39.4100,
        center_lng=-77.4110,
        zoom=13.5,
        bbox=FREDERICK_DIVISION_BBOXES["DOWNTOWN_HISTORIC"],
        submarkets=[k for k, v in FREDERICK_SUBMARKETS.items() if v.borough == "DOWNTOWN_HISTORIC"],
        city_id="frederick",
    ),
    "NORTH_MARKET": BoroughMeta(
        name="NORTH_MARKET",
        center_lat=39.4400,
        center_lng=-77.4120,
        zoom=13.5,
        bbox=FREDERICK_DIVISION_BBOXES["NORTH_MARKET"],
        submarkets=[k for k, v in FREDERICK_SUBMARKETS.items() if v.borough == "NORTH_MARKET"],
        city_id="frederick",
    ),
    "SOUTH_CREEK": BoroughMeta(
        name="SOUTH_CREEK",
        center_lat=39.3850,
        center_lng=-77.4150,
        zoom=13.0,
        bbox=FREDERICK_DIVISION_BBOXES["SOUTH_CREEK"],
        submarkets=[k for k, v in FREDERICK_SUBMARKETS.items() if v.borough == "SOUTH_CREEK"],
        city_id="frederick",
    ),
    "WEST_RIDGE": BoroughMeta(
        name="WEST_RIDGE",
        center_lat=39.4200,
        center_lng=-77.4500,
        zoom=13.0,
        bbox=FREDERICK_DIVISION_BBOXES["WEST_RIDGE"],
        submarkets=[k for k, v in FREDERICK_SUBMARKETS.items() if v.borough == "WEST_RIDGE"],
        city_id="frederick",
    ),
    "EAST_GATE": BoroughMeta(
        name="EAST_GATE",
        center_lat=39.4200,
        center_lng=-77.3850,
        zoom=13.0,
        bbox=FREDERICK_DIVISION_BBOXES["EAST_GATE"],
        submarkets=[k for k, v in FREDERICK_SUBMARKETS.items() if v.borough == "EAST_GATE"],
        city_id="frederick",
    ),
}

FRK_DIVISION_BBOXES = FREDERICK_DIVISION_BBOXES
FRK_SUBMARKETS = FREDERICK_SUBMARKETS
FRK_DIVISIONS = FREDERICK_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Frederick deeds: MD SDAT assessments (Socrata gx8c-a963), FREDERICK postal city.
# ---------------------------------------------------------------------------
FREDERICK_DEEDS_ENDPOINT = "https://opendata.maryland.gov/resource/gx8c-a963.json"

FREDERICK_FEED_SPECS: dict[str, dict[str, object]] = {
    "deeds": {
        "endpoint": FREDERICK_DEEDS_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89",
        "id_keys": [
            "account_id_mdp_field_acctid",
            "sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89",
        ],
        "topic_key": "topic_deeds",
        "interval_seconds": 1800.0,
        "producer_key": "deeds",
        "extra": {
            "order_by": (
                "sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89 DESC, :id"
            ),
            "where": "mdp_street_address_city_mdp_field_city = 'FREDERICK'",
            "ingestion_mode": "snapshot",
            "expected_cadence_days": 30,
            "non_spatial": False,
            "composite_id": True,
            "scope": (
                "Frederick MD deeds from the SDAT real property assessments (Frederick "
                "County view, gx8c-a963), FREDERICK postal city, newest sale first. "
                "Grantor names are never mapped."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_frederick_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Frederick feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (deeds only).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in FREDERICK_FEED_SPECS:
        available = ", ".join(sorted(FREDERICK_FEED_SPECS))
        raise KeyError(
            f"'{FREDERICK_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = FREDERICK_FEED_SPECS[feed_name]
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
    metro_bbox=FREDERICK_METRO_BBOX,
    division_bboxes=FREDERICK_DIVISION_BBOXES,
    submarkets=FREDERICK_SUBMARKETS,
    divisions=FREDERICK_DIVISIONS,
    contains=is_in_frederick_metro,
)

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "FREDERICK_CENTER",
    "FREDERICK_CITY_ID",
    "FREDERICK_DEEDS_ENDPOINT",
    "FREDERICK_DIVISIONS",
    "FREDERICK_DIVISION_BBOXES",
    "FREDERICK_FEED_SPECS",
    "FREDERICK_METRO_BBOX",
    "FREDERICK_SUBMARKETS",
    "FRK_DIVISIONS",
    "FRK_DIVISION_BBOXES",
    "FRK_SUBMARKETS",
    "REGISTRATION",
    "get_frederick_dataset",
    "is_in_frederick",
    "is_in_frederick_metro",
]
