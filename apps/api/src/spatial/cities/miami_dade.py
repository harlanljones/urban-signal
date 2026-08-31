GEOCODE_CONTEXT = "Miami-Dade County, FL"

PERMITS_FIELD_MAP = {
    "job_id": ["PermitNumber", "ProcessNumber", "ObjectId"],
    "job_type": ["PermitType", "ApplicationTypeDescription"],
    "cost": ["EstimatedValue"],
    "issuance_date": ["PermitIssuedDate"],
    "issued_date": ["PermitIssuedDate"],
    "filing_date": ["ApplicationDate"],
    "address_street": ["PropertyAddress"],
    "incident_address": ["PropertyAddress"],
    "borough": ["City"],
    "bbl": ["FolioNumber"],
    "proposed_units": ["StructureUnits"],
    "proposed_stories": ["StructureFloors"],
}

SLA_FIELD_MAP = {
    "license_id": ["ACCOUNTNO"],
    "dba": ["BUSNAME"],
    "premises_name": ["OWNERNAME"],
    "license_type": ["CLASSDESC", "CATGRYNAME", "OCCDESC"],
    "effective_date": ["BUSSDATE"],
    "address_street": ["BUSADDR"],
    "latitude": ["LAT"],
    "longitude": ["LON"],
    "status": ["ACCSTATUS", "PAIDSTATUS"],
    "borough": ["BUSCITY"],
    "zipcode": ["ZIPCODE"],
}

DEEDS_FIELD_MAP = {
    "doc_id": ["OR_BK_1", "OR_PG_1", "FOLIO", "OBJECTID"],
    "bbl": ["FOLIO"],
    "document_amount": ["PRICE_1"],
    "recorded_date": ["DOS_1"],
    "party1_grantor": ["GRANTOR_1"],
    "party2_grantee": ["GRANTEE_1"],
    "address_street": ["TRUE_SITE_ADDR"],
    "incident_address": ["TRUE_SITE_ADDR"],
    "zipcode": ["TRUE_SITE_ZIP_CODE"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
    "deeds": DEEDS_FIELD_MAP,
}

"""Miami-Dade County Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for Miami-Dade County, FL
(county-scale — not City of Miami municipal GIS, not Broward).

Miami-Dade registers as a PARTIAL metro (3 of 4 families) like Austin/LA:

* PERMITS — Hub table ``miamidade_permit_data`` (non-spatial). Address-only
  ``PropertyAddress``; ADR 0004 geocodes at parse time. Rolling ~2-year issued
  window (``rolling_window_days=730``).
* SLA — Local Business Tax Feature Layer View. Current-year occupational
  snapshot (``ingestion_mode=snapshot``), native ``LAT``/``LON``. Certificate
  of Use and the gisweb BusinessTracker twin are companion metadata only;
  the scheduler does not poll them.
* DEEDS — PaGis last-sale points on ``MD_ComparableSales/MapServer/5``.
  Text watermark ``DOS_1`` (``YYYYMMDD``, ADR 0005). Market filter
  ``PRICE_1 >= 10000``. Last-sale-on-parcel, not an ACRIS-style deed stream.

COMPLAINTS_311 is absent: public Hub year-slices stop at 2023; ``data_311_2024``
returns Token Required. Do not fold Broward or City of Miami into this
``city_id`` (ADR 0007 — sibling streams).

Endpoints were live-verified 2026-08-27 (wave-3-probe-miami-dade).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

MIAMI_DADE_CITY_ID: str = "miami_dade"
MIAMI_DADE_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# County-scale bbox: Broward line north, Card Sound south, Everglades west,
# Atlantic / Miami Beach east. City of Miami (~25.76, -80.19) is the center,
# not the extent — Homestead, Aventura, and Doral must sit inside.
MIAMI_DADE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 25.13,
    "max_lat": 25.98,
    "min_lng": -80.88,
    "max_lng": -80.11,
}

# Downtown Miami center from the registration contract.
MIAMI_DADE_CENTER: Dict[str, float] = {"lat": 25.7617, "lng": -80.1918}

MIAMI_DADE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_BRICKELL": {
        "min_lat": 25.740,
        "max_lat": 25.820,
        "min_lng": -80.220,
        "max_lng": -80.160,
    },
    "BEACH_BAY": {
        "min_lat": 25.670,
        "max_lat": 25.880,
        "min_lng": -80.175,
        "max_lng": -80.115,
    },
    "CORAL_GABLES_GROVE": {
        "min_lat": 25.650,
        "max_lat": 25.750,
        "min_lng": -80.330,
        "max_lng": -80.220,
    },
    "NORTH_CORRIDOR": {
        "min_lat": 25.830,
        "max_lat": 25.975,
        "min_lng": -80.320,
        "max_lng": -80.120,
    },
    "WEST_DORAL_AIRPORT": {
        "min_lat": 25.730,
        "max_lat": 25.860,
        "min_lng": -80.420,
        "max_lng": -80.280,
    },
    "SOUTH_KENDALL_HOMESTEAD": {
        "min_lat": 25.140,
        "max_lat": 25.720,
        "min_lng": -80.550,
        "max_lng": -80.250,
    },
}


def is_in_miami_dade_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within Miami-Dade County bounds."""
    if lat is None or lng is None:
        return False
    return (
        MIAMI_DADE_METRO_BBOX["min_lat"] <= lat <= MIAMI_DADE_METRO_BBOX["max_lat"]
        and MIAMI_DADE_METRO_BBOX["min_lng"] <= lng <= MIAMI_DADE_METRO_BBOX["max_lng"]
    )


is_in_greater_miami_dade_metro = is_in_miami_dade_metro


MIAMI_DADE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_BRICKELL (3)
    # =======================================================================
    "Downtown Miami": SubmarketMeta(
        name="Downtown Miami",
        borough="DOWNTOWN_BRICKELL",
        lat=25.7617,
        lng=-80.1918,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.91,
        capex=14500000.0,
        permit_vel=58.0,
        shift_ratio=1.68,
        sla=74.0,
        description="County civic and office core around Government Center with tower conversions and the densest issued-permit pipeline.",
        city_id="miami_dade",
    ),
    "Brickell": SubmarketMeta(
        name="Brickell",
        borough="DOWNTOWN_BRICKELL",
        lat=25.7580,
        lng=-80.1915,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.93,
        capex=16800000.0,
        permit_vel=64.0,
        shift_ratio=1.74,
        sla=78.0,
        description="Financial-district high-rise spine south of the Miami River with luxury condo and office-to-residential conversions.",
        city_id="miami_dade",
    ),
    "Wynwood / Edgewater": SubmarketMeta(
        name="Wynwood / Edgewater",
        borough="DOWNTOWN_BRICKELL",
        lat=25.8010,
        lng=-80.1990,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.88,
        capex=11200000.0,
        permit_vel=52.0,
        shift_ratio=1.62,
        sla=70.0,
        description="Warehouse-district adaptive reuse and bayfront mid-rise infill north of downtown.",
        city_id="miami_dade",
    ),
    # =======================================================================
    # BEACH_BAY (3)
    # =======================================================================
    "South Beach": SubmarketMeta(
        name="South Beach",
        borough="BEACH_BAY",
        lat=25.7826,
        lng=-80.1341,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.90,
        capex=15200000.0,
        permit_vel=48.0,
        shift_ratio=1.60,
        sla=72.0,
        description="Art Deco hotel-renovation corridor on Ocean Drive with the island's highest hospitality-license density.",
        city_id="miami_dade",
    ),
    "Mid-Beach": SubmarketMeta(
        name="Mid-Beach",
        borough="BEACH_BAY",
        lat=25.8130,
        lng=-80.1300,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.86,
        capex=9800000.0,
        permit_vel=36.0,
        shift_ratio=1.48,
        sla=64.0,
        description="Collins Avenue hotel and condo spine north of South Beach with renovation-led permitting.",
        city_id="miami_dade",
    ),
    "Key Biscayne": SubmarketMeta(
        name="Key Biscayne",
        borough="BEACH_BAY",
        lat=25.6936,
        lng=-80.1628,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.84,
        capex=8600000.0,
        permit_vel=24.0,
        shift_ratio=1.36,
        sla=56.0,
        description="Barrier-island village with estate renovations and strict coastal-construction overlays.",
        city_id="miami_dade",
    ),
    # =======================================================================
    # CORAL_GABLES_GROVE (3)
    # =======================================================================
    "Coral Gables": SubmarketMeta(
        name="Coral Gables",
        borough="CORAL_GABLES_GROVE",
        lat=25.7210,
        lng=-80.2680,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.89,
        capex=12400000.0,
        permit_vel=42.0,
        shift_ratio=1.54,
        sla=68.0,
        description="Mediterranean-revival planned city with Miracle Mile retail and high-value residential renovations.",
        city_id="miami_dade",
    ),
    "Coconut Grove": SubmarketMeta(
        name="Coconut Grove",
        borough="CORAL_GABLES_GROVE",
        lat=25.7270,
        lng=-80.2410,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.85,
        capex=9200000.0,
        permit_vel=34.0,
        shift_ratio=1.46,
        sla=62.0,
        description="Bayfront village of cottages and marinas with teardown pressure on large lots.",
        city_id="miami_dade",
    ),
    "South Miami / Pinecrest": SubmarketMeta(
        name="South Miami / Pinecrest",
        borough="CORAL_GABLES_GROVE",
        lat=25.7060,
        lng=-80.2930,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.81,
        capex=7400000.0,
        permit_vel=28.0,
        shift_ratio=1.38,
        sla=54.0,
        description="US-1 corridor suburbs with estate lots, independent retail, and renovation-led licensing.",
        city_id="miami_dade",
    ),
    # =======================================================================
    # NORTH_CORRIDOR (3)
    # =======================================================================
    "Hialeah": SubmarketMeta(
        name="Hialeah",
        borough="NORTH_CORRIDOR",
        lat=25.8576,
        lng=-80.2781,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=38.0,
        shift_ratio=1.44,
        sla=58.0,
        description="Industrial and small-lot residential grid with dense local-business-tax and contractor licensing.",
        city_id="miami_dade",
    ),
    "Miami Gardens": SubmarketMeta(
        name="Miami Gardens",
        borough="NORTH_CORRIDOR",
        lat=25.9420,
        lng=-80.2456,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.72,
        capex=4100000.0,
        permit_vel=26.0,
        shift_ratio=1.30,
        sla=46.0,
        description="North-county suburban grid at the Broward line with single-family infill and neighborhood services.",
        city_id="miami_dade",
    ),
    "Aventura": SubmarketMeta(
        name="Aventura",
        borough="NORTH_CORRIDOR",
        lat=25.9564,
        lng=-80.1390,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.87,
        capex=10800000.0,
        permit_vel=32.0,
        shift_ratio=1.50,
        sla=66.0,
        description="Northeast-county condo and mall node at the Broward line — county identity, not Fort Lauderdale.",
        city_id="miami_dade",
    ),
    # =======================================================================
    # WEST_DORAL_AIRPORT (3)
    # =======================================================================
    "Doral": SubmarketMeta(
        name="Doral",
        borough="WEST_DORAL_AIRPORT",
        lat=25.8195,
        lng=-80.3553,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.86,
        capex=11800000.0,
        permit_vel=46.0,
        shift_ratio=1.56,
        sla=67.0,
        description="West-county office-park and warehouse city with the metro's densest new-construction industrial pipeline.",
        city_id="miami_dade",
    ),
    "Sweetwater": SubmarketMeta(
        name="Sweetwater",
        borough="WEST_DORAL_AIRPORT",
        lat=25.7634,
        lng=-80.3731,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.74,
        capex=4800000.0,
        permit_vel=29.0,
        shift_ratio=1.34,
        sla=50.0,
        description="FIU-adjacent west corridor with small-lot residential and service-license density.",
        city_id="miami_dade",
    ),
    "Westchester": SubmarketMeta(
        name="Westchester",
        borough="WEST_DORAL_AIRPORT",
        lat=25.7543,
        lng=-80.3270,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.76,
        capex=5200000.0,
        permit_vel=27.0,
        shift_ratio=1.36,
        sla=52.0,
        description="Bird Road suburban grid between the airport and Coral Gables with renovation-led permitting.",
        city_id="miami_dade",
    ),
    # =======================================================================
    # SOUTH_KENDALL_HOMESTEAD (3)
    # =======================================================================
    "Kendall": SubmarketMeta(
        name="Kendall",
        borough="SOUTH_KENDALL_HOMESTEAD",
        lat=25.6790,
        lng=-80.3170,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.80,
        capex=6800000.0,
        permit_vel=33.0,
        shift_ratio=1.42,
        sla=57.0,
        description="South-Dade suburban commercial spine along Kendall Drive with medical and retail licensing.",
        city_id="miami_dade",
    ),
    "Cutler Bay": SubmarketMeta(
        name="Cutler Bay",
        borough="SOUTH_KENDALL_HOMESTEAD",
        lat=25.5808,
        lng=-80.3467,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.73,
        capex=4300000.0,
        permit_vel=24.0,
        shift_ratio=1.28,
        sla=48.0,
        description="South-county lakeside suburbs with small-lot infill and neighborhood services.",
        city_id="miami_dade",
    ),
    "Homestead / Florida City": SubmarketMeta(
        name="Homestead / Florida City",
        borough="SOUTH_KENDALL_HOMESTEAD",
        lat=25.4687,
        lng=-80.4776,
        zoom=12.5,
        pitch=38.0,
        base_lims=0.68,
        capex=3600000.0,
        permit_vel=28.0,
        shift_ratio=1.32,
        sla=44.0,
        description="Agricultural south-county edge with new-construction tract housing and the county's southern permit cluster.",
        city_id="miami_dade",
    ),
}


MIAMI_DADE_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_BRICKELL": BoroughMeta(
        name="DOWNTOWN_BRICKELL",
        center_lat=25.774,
        center_lng=-80.194,
        zoom=13.5,
        bbox=MIAMI_DADE_DIVISION_BBOXES["DOWNTOWN_BRICKELL"],
        submarkets=[k for k, v in MIAMI_DADE_SUBMARKETS.items() if v.borough == "DOWNTOWN_BRICKELL"],
        city_id="miami_dade",
    ),
    "BEACH_BAY": BoroughMeta(
        name="BEACH_BAY",
        center_lat=25.763,
        center_lng=-80.142,
        zoom=12.5,
        bbox=MIAMI_DADE_DIVISION_BBOXES["BEACH_BAY"],
        submarkets=[k for k, v in MIAMI_DADE_SUBMARKETS.items() if v.borough == "BEACH_BAY"],
        city_id="miami_dade",
    ),
    "CORAL_GABLES_GROVE": BoroughMeta(
        name="CORAL_GABLES_GROVE",
        center_lat=25.718,
        center_lng=-80.267,
        zoom=13.0,
        bbox=MIAMI_DADE_DIVISION_BBOXES["CORAL_GABLES_GROVE"],
        submarkets=[k for k, v in MIAMI_DADE_SUBMARKETS.items() if v.borough == "CORAL_GABLES_GROVE"],
        city_id="miami_dade",
    ),
    "NORTH_CORRIDOR": BoroughMeta(
        name="NORTH_CORRIDOR",
        center_lat=25.918,
        center_lng=-80.221,
        zoom=12.5,
        bbox=MIAMI_DADE_DIVISION_BBOXES["NORTH_CORRIDOR"],
        submarkets=[k for k, v in MIAMI_DADE_SUBMARKETS.items() if v.borough == "NORTH_CORRIDOR"],
        city_id="miami_dade",
    ),
    "WEST_DORAL_AIRPORT": BoroughMeta(
        name="WEST_DORAL_AIRPORT",
        center_lat=25.779,
        center_lng=-80.352,
        zoom=12.5,
        bbox=MIAMI_DADE_DIVISION_BBOXES["WEST_DORAL_AIRPORT"],
        submarkets=[k for k, v in MIAMI_DADE_SUBMARKETS.items() if v.borough == "WEST_DORAL_AIRPORT"],
        city_id="miami_dade",
    ),
    "SOUTH_KENDALL_HOMESTEAD": BoroughMeta(
        name="SOUTH_KENDALL_HOMESTEAD",
        center_lat=25.550,
        center_lng=-80.400,
        zoom=11.5,
        bbox=MIAMI_DADE_DIVISION_BBOXES["SOUTH_KENDALL_HOMESTEAD"],
        submarkets=[k for k, v in MIAMI_DADE_SUBMARKETS.items() if v.borough == "SOUTH_KENDALL_HOMESTEAD"],
        city_id="miami_dade",
    ),
}

GREATER_MIAMI_DADE_METRO_BBOX = MIAMI_DADE_METRO_BBOX
MDC_DIVISION_BBOXES = MIAMI_DADE_DIVISION_BBOXES
MDC_SUBMARKETS = MIAMI_DADE_SUBMARKETS
MDC_DIVISIONS = MIAMI_DADE_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-27 against AGOL org 8Pc9XBTAsYuxx9Ny and gisweb.miamidade.gov.
# Sketches match docs/research/wave-3-probe-miami-dade.md Registration contract.
# ---------------------------------------------------------------------------
MIAMI_DADE_PERMITS_ENDPOINT = (
    "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/"
    "miamidade_permit_data/FeatureServer/0"
)
MIAMI_DADE_SLA_ENDPOINT = (
    "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/"
    "Local_Business_Tax_Feature_Layer_View/FeatureServer/0"
)
MIAMI_DADE_DEEDS_ENDPOINT = (
    "https://gisweb.miamidade.gov/ArcGIS/rest/services/MD_ComparableSales/MapServer/5"
)
MIAMI_DADE_SLA_CERTIFICATE_OF_USE = (
    "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/"
    "CertificateOfUse_New_gdb/FeatureServer/0"
)
MIAMI_DADE_SLA_ENTERPRISE_TWIN = (
    "https://gisweb.miamidade.gov/ArcGIS/rest/services/BusinessTracker/MapServer/0"
)

MIAMI_DADE_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": MIAMI_DADE_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "PermitIssuedDate",
        "id_keys": ["PermitNumber", "ProcessNumber", "ObjectId"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "needs_geocode": True,
            "geocode_context": MIAMI_DADE_GEOCODE_CONTEXT,
            "oid_field": "ObjectId",
            "max_record_count": 1000,
            "expected_cadence_days": 1,
            "non_spatial": True,
            "rolling_window_days": 730,
            "scope": "Miami-Dade building permits issued (rolling 2-year table; ADR-0004)",
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": MIAMI_DADE_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "BUSSDATE",
        "id_keys": ["ACCOUNTNO", "RECEIPTNO", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "ingestion_mode": "snapshot",
            "oid_field": "OBJECTID",
            "max_record_count": 16000,
            "expected_cadence_days": 30,
            "companion_endpoints": {
                "certificate_of_use": MIAMI_DADE_SLA_CERTIFICATE_OF_USE,
                "enterprise_twin": MIAMI_DADE_SLA_ENTERPRISE_TWIN,
            },
            "scope": (
                "Miami-Dade Local Business Tax snapshot (native LAT/LON). "
                "Companions are metadata only; scheduler does not poll them."
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
    "deeds": {
        "endpoint": MIAMI_DADE_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "DOS_1",
        "id_keys": ["FOLIO", "OR_BK_1", "OR_PG_1", "OBJECTID"],
        "topic_key": "topic_deeds",
        "interval_seconds": 600.0,
        "producer_key": "deeds",
        "extra": {
            "watermark_type": "text",
            "watermark_format": "%Y%m%d",
            "where": "PRICE_1 >= 10000",
            "oid_field": "OBJECTID",
            "max_record_count": 20000,
            "expected_cadence_days": 7,
            "scope": (
                "Miami-Dade PaGis last-sale points (DOS_1 YYYYMMDD text; "
                "market filter PRICE_1 >= 10000). Not an ACRIS deed stream."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_miami_dade_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Miami-Dade feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (311).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in MIAMI_DADE_FEED_SPECS:
        available = ", ".join(sorted(MIAMI_DADE_FEED_SPECS))
        raise KeyError(
            f"'{MIAMI_DADE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = MIAMI_DADE_FEED_SPECS[feed_name]
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
    metro_bbox=MIAMI_DADE_METRO_BBOX,
    division_bboxes=MIAMI_DADE_DIVISION_BBOXES,
    submarkets=MIAMI_DADE_SUBMARKETS,
    divisions=MIAMI_DADE_DIVISIONS,
    contains=is_in_miami_dade_metro,
)
