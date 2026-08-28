"""Scottsdale, AZ spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Scottsdale
(northeast Maricopa County, AZ — its own CityId, distinct from the
registered Phoenix / Maricopa County neighbor).

Scottsdale is a TWO-FEED PARTIAL metro: PERMITS and SLA on the city ArcGIS
Server 10.6 (``maps.scottsdaleaz.gov``). ``data.scottsdaleaz.gov`` — the
portal the US-227 ticket names as Socrata — is actually an ArcGIS Hub
Open Data site (``/api/catalog/v1`` 404s; the homepage serves
hubcdn.arcgis.com assets); the queryable data host is the REST server.

Live-probe evidence that defines this leaf (probed 2026-08-28, US-227):

* **PERMITS** — ``OpenData_Tabular/MapServer/12`` "Building Permits"
  (standalone table): 288,121 rows; watermark ``IssueDate``
  (esriFieldTypeDate, epoch-ms → ISO in ArcGISClient); newest
  **2026-08-21T00:00:00+00:00** (permit_id 324348, SFR-CUSTOM IN
  SUBDIVISION). 151,704 rows (52.6%) carry native WGS84
  ``Latitude``/``Longitude`` attributes (newest geocoded row 33.6564984 /
  -111.90865983, "18700 N HAYDEN RD UNIT 250", subdivision LOT 1A OF
  CAVASSON); null-coordinate rows fall to the ADR-0004 geocode supplement
  on ``Address``. The mapped twin ``OpenData_Events/MapServer/3`` (store SR
  WKID 2868, Arizona Central intl feet) returns ``{'x':'NaN','y':'NaN'}`
  geometry for null-shape features — ArcGISClient would lift those strings
  as coordinates — so the TABLE endpoint is registered and the NaN trap is
  structurally unreachable. Cadence is bursty but steady (56 rows in the
  last 30d, 124 in 60d; a 7-day dry spell ended 2026-08-21 at probe time),
  hence expected_cadence_days=14 rather than the daily default.
* **SLA** — ``OpenData_Tabular/MapServer/6`` "Business Licenses"
  (standalone table): 19,944 rows (19,922 guarded); watermark
  ``BusinessStartDate``; newest guarded value **2026-08-21T00:00:00+00:00**
  (AcctNum 2045469, APEX APPLIANCES). LicType is only BRM/BRS (merchant /
  retail city business licenses). Address-only (``ServAddrComp`` +
  ``ServCityStateZipComp``) → needs_geocode. **Future-dated sentinels**
  (Albuquerque/Tucson discipline): the newest unguarded row is forward-
  dated to year **5202-09-12** (epoch-ms 102014035200000, 'BOOTS AND
  BEER', AcctStatus Inactive) and Active applications are dated
  2027-01-01 / 2026-11-19 / 2026-11-01 — excluded at the source by the
  where guard ``BusinessStartDate <= CURRENT_TIMESTAMP`` (verified live);
  ``outStatistics`` max on the column server-400s (epoch overflow), so the
  newest value is read via ``orderByFields=BusinessStartDate DESC``.
  Reported OID field ``ESRI_OID`` is per-query unstable (OBJECTID 19901
  returned ESRI_OID 27 and 1 across two probes) — the attribute
  ``OBJECTID`` column is the stable row key and pagination default.
* **311-family REJECTED** per repo discipline: the only complaint feeds are
  code-enforcement layers (``OpenData_Events/MapServer/1`` Code Violations,
  18,470 rows, fresh 2026-08-21; layer 2 Graffiti, 907 rows) — code
  enforcement is NOT COMPLAINTS_311 (Lynchburg TRAKiT / Wichita MABCD
  precedent), and the city publishes no true 311 service-request dataset
  (``My_Services`` is trash/recycling schedule geography).
* **DEEDS REJECTED**: recorder.maricopa.gov (and /recdocdata) return 403 to
  anonymous probes — no bulk API; the registration ships without deeds.
* **ANSI-date host NOT required**: maps.scottsdaleaz.gov accepts ISO
  string date literals with real date math (``IssueDate > '2026-08-01'``
  → 51 rows live, time-of-day respected) — the host is deliberately NOT
  added to ``ANSI_DATE_LITERAL_HOSTS``.
* Divisions are hand-authored from live-row geography plus named
  districts; two submarket anchors are directly evidenced by probe rows
  (Cavasson corridor permit; Desert Highlands / Happy Valley permits).
"""

from src.producers.field_maps_scottsdale import (
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

SCOTTSDALE_CITY_ID: str = "scottsdale"
SCOTTSDALE_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Scottsdale. Bounds span the live permit-row lat/lng aggregate
# (lat 33.4493-33.8849, lng -111.9759 to -111.7568, probed 2026-08-28) with
# margin, while excluding the Phoenix downtown core (-112.074), Tempe
# (33.4255), Mesa (33.4152), and Fountain Hills (-111.7258).
SCOTTSDALE_METRO_BBOX: dict[str, float] = {
    "min_lat": 33.44,
    "max_lat": 33.91,
    "min_lng": -112.00,
    "max_lng": -111.73,
}

# 6 Scottsdale divisions. Hand-authored; borough resolution at ingest
# comes from coordinates via get_division_for_coordinate, so bboxes need only
# be sane, disjoint, and contain their own submarket centers.
SCOTTSDALE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "OLD_TOWN": {
        "min_lat": 33.490,
        "max_lat": 33.512,
        "min_lng": -111.945,
        "max_lng": -111.912,
    },
    "SOUTH_SCOTTSDALE": {
        "min_lat": 33.440,
        "max_lat": 33.490,
        "min_lng": -111.965,
        "max_lng": -111.880,
    },
    "GAINEY_RANCH": {
        "min_lat": 33.568,
        "max_lat": 33.604,
        "min_lng": -111.930,
        "max_lng": -111.880,
    },
    "AIRPARK": {
        "min_lat": 33.604,
        "max_lat": 33.638,
        "min_lng": -111.960,
        "max_lng": -111.890,
    },
    "DC_RANCH": {
        "min_lat": 33.638,
        "max_lat": 33.678,
        "min_lng": -111.950,
        "max_lng": -111.885,
    },
    "NORTH_SCOTTSDALE": {
        "min_lat": 33.678,
        "max_lat": 33.905,
        "min_lng": -111.980,
        "max_lng": -111.755,
    },
}


def is_in_scottsdale_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Scottsdale metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        SCOTTSDALE_METRO_BBOX["min_lat"] <= lat <= SCOTTSDALE_METRO_BBOX["max_lat"]
        and SCOTTSDALE_METRO_BBOX["min_lng"] <= lng <= SCOTTSDALE_METRO_BBOX["max_lng"]
    )


is_in_greater_scottsdale_metro = is_in_scottsdale_metro


SCOTTSDALE_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # OLD_TOWN (2)
    # =======================================================================
    "Old Town Scottsdale": SubmarketMeta(
        name="Old Town Scottsdale",
        borough="OLD_TOWN",
        lat=33.4926,
        lng=-111.9253,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.88,
        capex=9800000.0,
        permit_vel=41.0,
        shift_ratio=1.56,
        sla=64.0,
        description="Fifth Avenue and Main Street entertainment core with gallery frontage, hotel conversions, and the entertainment-district patio economy.",
        city_id="scottsdale",
    ),
    "Arts District": SubmarketMeta(
        name="Arts District",
        borough="OLD_TOWN",
        lat=33.4962,
        lng=-111.9341,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.86,
        capex=8600000.0,
        permit_vel=37.0,
        shift_ratio=1.51,
        sla=61.0,
        description="Gallery row west of Scottsdale Road with museum adjacency, art-walk retail, and boutique office conversions.",
        city_id="scottsdale",
    ),
    # =======================================================================
    # SOUTH_SCOTTSDALE (2)
    # =======================================================================
    "Los Arcos Corridor": SubmarketMeta(
        name="Los Arcos Corridor",
        borough="SOUTH_SCOTTSDALE",
        lat=33.4640,
        lng=-111.9255,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.79,
        capex=6400000.0,
        permit_vel=31.0,
        shift_ratio=1.44,
        sla=55.0,
        description="McDowell and Scottsdale Road retail belt with post-war strip retrofit, infill multifamily, and the Los Arcos redevelopment blocks.",
        city_id="scottsdale",
    ),
    "SkySong District": SubmarketMeta(
        name="SkySong District",
        borough="SOUTH_SCOTTSDALE",
        lat=33.4874,
        lng=-111.9211,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=7600000.0,
        permit_vel=35.0,
        shift_ratio=1.49,
        sla=58.0,
        description="ASU SkySong innovation campus corridor with research-office demand, student-adjacent rentals, and steady tenant-improvement permitting.",
        city_id="scottsdale",
    ),
    # =======================================================================
    # GAINEY_RANCH (1)
    # =======================================================================
    "Gainey Village": SubmarketMeta(
        name="Gainey Village",
        borough="GAINEY_RANCH",
        lat=33.5864,
        lng=-111.8959,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.87,
        capex=9200000.0,
        permit_vel=34.0,
        shift_ratio=1.52,
        sla=62.0,
        description="Gainey Ranch corporate and village core with golf-community stock, Class A office along Doubletree, and stable license renewals.",
        city_id="scottsdale",
    ),
    # =======================================================================
    # AIRPARK (1)
    # =======================================================================
    "Scottsdale Airpark": SubmarketMeta(
        name="Scottsdale Airpark",
        borough="AIRPARK",
        lat=33.6229,
        lng=-111.9103,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.89,
        capex=10400000.0,
        permit_vel=39.0,
        shift_ratio=1.55,
        sla=65.0,
        description="Airport and Loop 101 office corridor with aviation-adjacent industrial, WestWorld event demand, and the metro's densest corporate lease belt.",
        city_id="scottsdale",
    ),
    # =======================================================================
    # DC_RANCH (2)
    # =======================================================================
    "DC Ranch / Market Street": SubmarketMeta(
        name="DC Ranch / Market Street",
        borough="DC_RANCH",
        lat=33.6562,
        lng=-111.9168,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.91,
        capex=11200000.0,
        permit_vel=36.0,
        shift_ratio=1.58,
        sla=67.0,
        description="Master-planned DC Ranch village with Market Street retail, custom-lot rebuilds, and the metro's top household-income band.",
        city_id="scottsdale",
    ),
    "Cavasson Corridor": SubmarketMeta(
        name="Cavasson Corridor",
        borough="DC_RANCH",
        lat=33.6565,
        lng=-111.9087,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.90,
        capex=10800000.0,
        permit_vel=38.0,
        shift_ratio=1.57,
        sla=66.0,
        description="Hayden Road corporate corridor anchored by the Cavasson master plan (Scripps/ASU campus) — evidenced by live tenant-improvement permitting at 18700 N Hayden.",
        city_id="scottsdale",
    ),
    # =======================================================================
    # NORTH_SCOTTSDALE (2)
    # =======================================================================
    "Troon": SubmarketMeta(
        name="Troon",
        borough="NORTH_SCOTTSDALE",
        lat=33.7060,
        lng=-111.9090,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.92,
        capex=11800000.0,
        permit_vel=33.0,
        shift_ratio=1.59,
        sla=68.0,
        description="Golf-community custom-home edge at the McDowell Sonoran Preserve with view-lot rebuilds and luxury remodel demand.",
        city_id="scottsdale",
    ),
    "Desert Highlands / Happy Valley": SubmarketMeta(
        name="Desert Highlands / Happy Valley",
        borough="NORTH_SCOTTSDALE",
        lat=33.6803,
        lng=-111.8612,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.90,
        capex=10600000.0,
        permit_vel=32.0,
        shift_ratio=1.56,
        sla=66.0,
        description="Happy Valley Road gate-community belt (Desert Highlands, Troon North edges) — evidenced by live SFR-CUSTOM and NATIVE PLANT permits at 10040 E Happy Valley Rd.",
        city_id="scottsdale",
    ),
}


SCOTTSDALE_DIVISIONS: dict[str, BoroughMeta] = {
    "OLD_TOWN": BoroughMeta(
        name="OLD_TOWN",
        center_lat=33.4930,
        center_lng=-111.9258,
        zoom=14.0,
        bbox=SCOTTSDALE_DIVISION_BBOXES["OLD_TOWN"],
        submarkets=[k for k, v in SCOTTSDALE_SUBMARKETS.items() if v.borough == "OLD_TOWN"],
        city_id="scottsdale",
    ),
    "SOUTH_SCOTTSDALE": BoroughMeta(
        name="SOUTH_SCOTTSDALE",
        center_lat=33.4620,
        center_lng=-111.9210,
        zoom=13.5,
        bbox=SCOTTSDALE_DIVISION_BBOXES["SOUTH_SCOTTSDALE"],
        submarkets=[k for k, v in SCOTTSDALE_SUBMARKETS.items() if v.borough == "SOUTH_SCOTTSDALE"],
        city_id="scottsdale",
    ),
    "GAINEY_RANCH": BoroughMeta(
        name="GAINEY_RANCH",
        center_lat=33.5864,
        center_lng=-111.8959,
        zoom=13.5,
        bbox=SCOTTSDALE_DIVISION_BBOXES["GAINEY_RANCH"],
        submarkets=[k for k, v in SCOTTSDALE_SUBMARKETS.items() if v.borough == "GAINEY_RANCH"],
        city_id="scottsdale",
    ),
    "AIRPARK": BoroughMeta(
        name="AIRPARK",
        center_lat=33.6229,
        center_lng=-111.9103,
        zoom=13.5,
        bbox=SCOTTSDALE_DIVISION_BBOXES["AIRPARK"],
        submarkets=[k for k, v in SCOTTSDALE_SUBMARKETS.items() if v.borough == "AIRPARK"],
        city_id="scottsdale",
    ),
    "DC_RANCH": BoroughMeta(
        name="DC_RANCH",
        center_lat=33.6562,
        center_lng=-111.9168,
        zoom=13.5,
        bbox=SCOTTSDALE_DIVISION_BBOXES["DC_RANCH"],
        submarkets=[k for k, v in SCOTTSDALE_SUBMARKETS.items() if v.borough == "DC_RANCH"],
        city_id="scottsdale",
    ),
    "NORTH_SCOTTSDALE": BoroughMeta(
        name="NORTH_SCOTTSDALE",
        center_lat=33.7060,
        center_lng=-111.9090,
        zoom=12.5,
        bbox=SCOTTSDALE_DIVISION_BBOXES["NORTH_SCOTTSDALE"],
        submarkets=[k for k, v in SCOTTSDALE_SUBMARKETS.items() if v.borough == "NORTH_SCOTTSDALE"],
        city_id="scottsdale",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed live 2026-08-28 (US-227). Register the TABLE endpoints — the
# OpenData_Events mapped twins either add nothing (permits) or carry the
# NaN-geometry trap; 311-family and deeds are rejected (see docstring).
# ---------------------------------------------------------------------------
SCOTTSDALE_PERMITS_ENDPOINT = (
    "https://maps.scottsdaleaz.gov/arcgis/rest/services/"
    "OpenData_Tabular/MapServer/12"
)

SCOTTSDALE_SLA_ENDPOINT = (
    "https://maps.scottsdaleaz.gov/arcgis/rest/services/"
    "OpenData_Tabular/MapServer/6"
)

# Future-dated BusinessStartDate applications are sentinels (newest live
# row starts 5202-09-12; Active applications reach 2027-01-01): exclude
# them at the source so neither the high watermark nor staleness math sees
# them. Verified live; the host accepts ISO date literals, so the shared
# incremental watermark comparison needs no ANSI host entry.
SCOTTSDALE_SLA_WHERE = "BusinessStartDate <= CURRENT_TIMESTAMP"

SCOTTSDALE_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": SCOTTSDALE_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "IssueDate",
        "id_keys": ["PermitNumber", "permit_id"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 14,
            "needs_geocode": True,
            "geocode_context": SCOTTSDALE_GEOCODE_CONTEXT,
            "oid_field": "permit_id",
            "max_record_count": 1000,
            "order_by": "IssueDate DESC",
            "scope": (
                "Building Permits table (288,121 rows; native WGS84 "
                "Latitude/Longitude attributes cover 52.6% of rows, "
                "geocode supplement on Address for null rows; registered "
                "as the TABLE endpoint because the OpenData_Events/3 "
                "mapped twin returns {'x':'NaN','y':'NaN'} geometry for "
                "null-shape features which the client would lift as "
                "coordinates; IssueDate bursty-steady at 56/30d-124/60d "
                "hence cadence 14; host accepts ISO date literals - no "
                "ANSI_DATE_LITERAL_HOSTS entry; 311-family and deeds "
                "rejected)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": SCOTTSDALE_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "BusinessStartDate",
        "id_keys": ["AcctNum", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 14,
            "needs_geocode": True,
            "geocode_context": SCOTTSDALE_GEOCODE_CONTEXT,
            "watermark_exclude": [],
            "oid_field": "OBJECTID",
            "max_record_count": 1000,
            "order_by": "BusinessStartDate DESC",
            "where": SCOTTSDALE_SLA_WHERE,
            "scope": (
                "Business Licenses (19,944 rows, 19,922 guarded; "
                "address-only ServAddrComp with geocode supplement "
                "context 'Scottsdale, AZ'; future-dated BusinessStartDate "
                "sentinels excluded by the where guard - newest unguarded "
                "row is year 5202, outStatistics max 400s on the column "
                "so newest is read via orderByFields DESC; reported OID "
                "ESRI_OID is per-query unstable - OBJECTID attribute is "
                "the stable key; LicType only BRM/BRS)"
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
}


def get_scottsdale_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Scottsdale feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in SCOTTSDALE_FEED_SPECS:
        available = ", ".join(sorted(SCOTTSDALE_FEED_SPECS))
        raise KeyError(
            f"'{SCOTTSDALE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = SCOTTSDALE_FEED_SPECS[feed_name]
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
    metro_bbox=SCOTTSDALE_METRO_BBOX,
    division_bboxes=SCOTTSDALE_DIVISION_BBOXES,
    submarkets=SCOTTSDALE_SUBMARKETS,
    divisions=SCOTTSDALE_DIVISIONS,
    contains=is_in_scottsdale_metro,
)

__all__ = [
    "REGISTRATION",
    "SCOTTSDALE_CITY_ID",
    "SCOTTSDALE_DIVISIONS",
    "SCOTTSDALE_DIVISION_BBOXES",
    "SCOTTSDALE_FEED_SPECS",
    "SCOTTSDALE_GEOCODE_CONTEXT",
    "SCOTTSDALE_METRO_BBOX",
    "SCOTTSDALE_PERMITS_ENDPOINT",
    "SCOTTSDALE_SLA_ENDPOINT",
    "SCOTTSDALE_SLA_WHERE",
    "SCOTTSDALE_SUBMARKETS",
    "get_scottsdale_dataset",
    "is_in_greater_scottsdale_metro",
    "is_in_scottsdale_metro",
]