SLA_FIELD_MAP = {
    "license_id": ["ACC_NUM"],
    "dba": ["ACC_NAME"],
    "premises_name": ["ACC_NAME"],
    "license_type": ["LIC_TYPE", "NAIC_DESC"],
    "status": ["LIC_STATUS"],
    "effective_date": ["DT_START"],
    "address_street": ["FULLADDRESS"],
    "zipcode": ["ZIP_CODE"],
}

FIELD_MAP = {
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT = "Tucson, AZ"

DROPPED_NONADDRESS_COLUMNS = (
    "STREETNUM",
    "STREETDIR",
    "STREETNAM",
    "STREETSUF",
    "APT",
    "ADDRESS",
    "Shape",
    "GlobalID",
)

"""Tucson, AZ spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Tucson
(northeast-to-central Pima County, AZ).

Tucson is a ONE-FEED PARTIAL metro like Albuquerque: SLA only — the BUSLIC
business-license layer (``PublicMaps/OpenData_EconomicDevelopment/
MapServer/3``, Tier 2, ~93k rows, native point geometry + ``FULLADDRESS``).
PERMITS is Tier 3: ``PDSD_PERMITS_ALL`` L0/L2 is a row-frozen archive (max
``DATEISSUED`` 2022-10-20, 0 rows since — the columns are registrable but
the ETL is dead), so a ``where`` guard must prevent accidental registration.
COMPLAINTS_311 and DEEDS are Tier 3 (no Hub dataset; Pima County recording
has no anonymous bulk API) and stay unregistered.

Live-probe caveats that define this leaf (re-probed 2026-08-28, US-328;
original probe 2026-08-27):

* SLA row count is **93,483 live** (probe said 93,483). ``DT_START``
  (license start) is the only ``esriFieldTypeDate`` column and arrives as
  epoch-ms; ``ArcGISClient`` flattens it to ISO 8601 UTC.
* **Future-dated sentinels** (Albuquerque discipline): the newest rows are
  forward-dated license applications — newest ``DT_START`` = **2026-09-12**
  (OBJECTID 16, which also has **null geometry**), then 2026-09-03. Newest
  non-future start: **2026-05-29** (Trader Joe's #288, OBJECTID 6).
  Sentinel handling is the spec ``where`` guard
  ``DT_START <= CURRENT_TIMESTAMP`` (verified live); a static
  ``watermark_exclude`` list cannot pin a rolling set of future-dated
  applications, and on this host the ``NOT IN`` literal form is
  server-broken anyway (see ANSI caveat).
* **ANSI-date host**: ``gis.tucsonaz.gov`` rejects ISO date-string
  comparisons in ``where`` (400 "Unable to complete operation") and only
  accepts ANSI ``date 'YYYY-MM-DD'`` literals — the DC/Milwaukee/Charlotte
  family. The spine must add the host to ``ANSI_DATE_LITERAL_HOSTS``
  (watermarks.py) so incremental watermark comparisons and any exclude
  clause render ANSI; the leaf ``where`` guard uses ``CURRENT_TIMESTAMP``
  and needs no literal form.
* **Slow/annual cadence**: only 2 non-future rows in the 60d window (391
  at Henderson) while the layer is demonstrably maintained (future-dated
  2026-09 applications exist). Declared ``expected_cadence_days=30`` with
  ``alarm_exempt=True`` so staleness alerts do not false-positive.
* Geometry is native point (outSR=4326 lift); some rows are null-geometry
  and fall to the ADR-0004 geocode supplement on ``FULLADDRESS`` (context
  "Tucson, AZ"). Layer store SR is WKID 2868 (Arizona East intl feet) —
  never mapped as coordinates.
* ``CITY`` spans Pima County municipalities (TUCSON 79,012; PIMA COUNTY
  12,424; ORO VALLEY 1,021; MARANA 672; SOUTH TUCSON 249); metro bbox
  containment gates ingestion, and the Oro Valley edge division is
  evidenced by those 1,021 rows.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

TUCSON_CITY_ID: str = "tucson"
TUCSON_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Tucson + the Oro Valley / Catalina Foothills belt it licenses.
# Permissive enough to hold the downtown core (32.2226, -110.9723), the
# University corridor, midtown Broadway, the foothills edge, and the Oro
# Valley town center (32.3907, -110.9757) — while excluding far-county
# Green Valley / Sahuarita rows that ride the county-wide CITY values.
TUCSON_METRO_BBOX: dict[str, float] = {
    "min_lat": 32.15,
    "max_lat": 32.43,
    "min_lng": -111.06,
    "max_lng": -110.78,
}

# 5 Tucson divisions. Hand-authored; borough resolution at ingest
# comes from coordinates via get_division_for_coordinate, so bboxes need only
# be sane and contain their own submarket centers.
TUCSON_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_CORE": {
        "min_lat": 32.208,
        "max_lat": 32.228,
        "min_lng": -110.982,
        "max_lng": -110.964,
    },
    "FOURTH_AVENUE_UNIVERSITY": {
        "min_lat": 32.224,
        "max_lat": 32.238,
        "min_lng": -110.970,
        "max_lng": -110.943,
    },
    "MIDTOWN": {
        "min_lat": 32.215,
        "max_lat": 32.260,
        "min_lng": -110.943,
        "max_lng": -110.890,
    },
    "CATALINA_FOOTHILLS": {
        "min_lat": 32.295,
        "max_lat": 32.345,
        "min_lng": -110.980,
        "max_lng": -110.890,
    },
    "ORO_VALLEY_EDGE": {
        "min_lat": 32.360,
        "max_lat": 32.415,
        "min_lng": -111.010,
        "max_lng": -110.935,
    },
}


def is_in_tucson_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Tucson metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        TUCSON_METRO_BBOX["min_lat"] <= lat <= TUCSON_METRO_BBOX["max_lat"]
        and TUCSON_METRO_BBOX["min_lng"] <= lng <= TUCSON_METRO_BBOX["max_lng"]
    )


is_in_greater_tucson_metro = is_in_tucson_metro


TUCSON_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CORE (3)
    # =======================================================================
    "Downtown Tucson": SubmarketMeta(
        name="Downtown Tucson",
        borough="DOWNTOWN_CORE",
        lat=32.2226,
        lng=-110.9723,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.84,
        capex=8200000.0,
        permit_vel=38.0,
        shift_ratio=1.52,
        sla=62.0,
        description="Congress Street core with the Fox Tucson Theatre, the Rio Nuevo redevelopment blocks, and adaptive-reuse of the warehouse district's commercial stock.",
        city_id="tucson",
    ),
    "Armory Park": SubmarketMeta(
        name="Armory Park",
        borough="DOWNTOWN_CORE",
        lat=32.2159,
        lng=-110.9688,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=7400000.0,
        permit_vel=34.0,
        shift_ratio=1.49,
        sla=59.0,
        description="Historic residential district south of the convention center with Victorian and Sonoran rowhouse restoration and the Tucson Museum of Art edge.",
        city_id="tucson",
    ),
    "Barrio Viejo": SubmarketMeta(
        name="Barrio Viejo",
        borough="DOWNTOWN_CORE",
        lat=32.2145,
        lng=-110.9772,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.82,
        capex=6800000.0,
        permit_vel=31.0,
        shift_ratio=1.46,
        sla=56.0,
        description="Sonoran rowhouse barrio west of I-10 with adobe rehabilitation, courtyarded short-stay conversions, and the Convento cultural frontage.",
        city_id="tucson",
    ),
    # =======================================================================
    # FOURTH_AVENUE_UNIVERSITY (2)
    # =======================================================================
    "Fourth Avenue": SubmarketMeta(
        name="Fourth Avenue",
        borough="FOURTH_AVENUE_UNIVERSITY",
        lat=32.2262,
        lng=-110.9662,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.86,
        capex=7900000.0,
        permit_vel=37.0,
        shift_ratio=1.51,
        sla=60.0,
        description="Historic merchant strip between downtown and campus with storefront retail, patio-dining infill, and the streetcar-linked foot-traffic economy.",
        city_id="tucson",
    ),
    "University of Arizona": SubmarketMeta(
        name="University of Arizona",
        borough="FOURTH_AVENUE_UNIVERSITY",
        lat=32.2312,
        lng=-110.9480,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.87,
        capex=9100000.0,
        permit_vel=41.0,
        shift_ratio=1.55,
        sla=64.0,
        description="Main Gate and campus corridor with student-housing turnover, lab and tech-transfer adjacency, and the university's anchor-institution demand.",
        city_id="tucson",
    ),
    # =======================================================================
    # MIDTOWN (1)
    # =======================================================================
    "Midtown": SubmarketMeta(
        name="Midtown",
        borough="MIDTOWN",
        lat=32.2320,
        lng=-110.9150,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.81,
        capex=7200000.0,
        permit_vel=33.0,
        shift_ratio=1.45,
        sla=57.0,
        description="Broadway and Speedway midtown belt with post-war commercial strip retrofit, medical office demand, and the Grant/Alvernon rental core.",
        city_id="tucson",
    ),
    # =======================================================================
    # CATALINA_FOOTHILLS (1)
    # =======================================================================
    "Catalina Foothills edge": SubmarketMeta(
        name="Catalina Foothills edge",
        borough="CATALINA_FOOTHILLS",
        lat=32.3280,
        lng=-110.9380,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.90,
        capex=10500000.0,
        permit_vel=36.0,
        shift_ratio=1.57,
        sla=66.0,
        description="Skyline and Campbell foothills belt with luxury resort adjacency, view-lot renovation, and the metro's top valuation band at the Santa Catalinas.",
        city_id="tucson",
    ),
    # =======================================================================
    # ORO_VALLEY_EDGE (1)
    # =======================================================================
    "Oro Valley edge": SubmarketMeta(
        name="Oro Valley edge",
        borough="ORO_VALLEY_EDGE",
        lat=32.3907,
        lng=-110.9757,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.88,
        capex=9600000.0,
        permit_vel=32.0,
        shift_ratio=1.53,
        sla=63.0,
        description="Northwest master-planned edge along Oracle Road and La Cañada with golf-community stock, Innovation Park biotech adjacency, and steady license growth.",
        city_id="tucson",
    ),
}


TUCSON_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=32.2200,
        center_lng=-110.9720,
        zoom=13.5,
        bbox=TUCSON_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in TUCSON_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id="tucson",
    ),
    "FOURTH_AVENUE_UNIVERSITY": BoroughMeta(
        name="FOURTH_AVENUE_UNIVERSITY",
        center_lat=32.2287,
        center_lng=-110.9571,
        zoom=13.5,
        bbox=TUCSON_DIVISION_BBOXES["FOURTH_AVENUE_UNIVERSITY"],
        submarkets=[k for k, v in TUCSON_SUBMARKETS.items() if v.borough == "FOURTH_AVENUE_UNIVERSITY"],
        city_id="tucson",
    ),
    "MIDTOWN": BoroughMeta(
        name="MIDTOWN",
        center_lat=32.2320,
        center_lng=-110.9150,
        zoom=13.0,
        bbox=TUCSON_DIVISION_BBOXES["MIDTOWN"],
        submarkets=[k for k, v in TUCSON_SUBMARKETS.items() if v.borough == "MIDTOWN"],
        city_id="tucson",
    ),
    "CATALINA_FOOTHILLS": BoroughMeta(
        name="CATALINA_FOOTHILLS",
        center_lat=32.3280,
        center_lng=-110.9380,
        zoom=12.5,
        bbox=TUCSON_DIVISION_BBOXES["CATALINA_FOOTHILLS"],
        submarkets=[k for k, v in TUCSON_SUBMARKETS.items() if v.borough == "CATALINA_FOOTHILLS"],
        city_id="tucson",
    ),
    "ORO_VALLEY_EDGE": BoroughMeta(
        name="ORO_VALLEY_EDGE",
        center_lat=32.3907,
        center_lng=-110.9757,
        zoom=12.5,
        bbox=TUCSON_DIVISION_BBOXES["ORO_VALLEY_EDGE"],
        submarkets=[k for k, v in TUCSON_SUBMARKETS.items() if v.borough == "ORO_VALLEY_EDGE"],
        city_id="tucson",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-27, re-probed 2026-08-28. Do not register the frozen
# PDSD_PERMITS_ALL archive, 311, deeds, or sibling MapServer layers.
# ---------------------------------------------------------------------------
TUCSON_SLA_ENDPOINT = (
    "https://gis.tucsonaz.gov/arcgis/rest/services/"
    "PublicMaps/OpenData_EconomicDevelopment/MapServer/3"
)

# Future-dated DT_START applications are sentinels (newest live row starts
# 2026-09-12): exclude them at the source so neither the high watermark nor
# staleness math sees them. Verified live; ANSI-date host — never render
# ISO literals for this endpoint (see module docstring).
TUCSON_SLA_WHERE = "DT_START <= CURRENT_TIMESTAMP"

TUCSON_SLA_ALARM_EXEMPT_REASON = (
    "slow/annual effective cadence: newest non-future DT_START rows land "
    "~2 per 60d (layer IS maintained - future-dated 2026-09 applications "
    "present); DT_START<=CURRENT_TIMESTAMP where guard excludes future "
    "sentinels; alarm would false-positive on the slow issuance pace"
)

TUCSON_FEED_SPECS: dict[str, dict[str, object]] = {
    "sla": {
        "endpoint": TUCSON_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "DT_START",
        "id_keys": ["ACC_NUM", "LIC_TYPE", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 30,
            "alarm_exempt": True,
            "alarm_exempt_reason": TUCSON_SLA_ALARM_EXEMPT_REASON,
            "watermark_exclude": [],
            "ingestion_mode": "snapshot",
            "needs_geocode": True,
            "geocode_context": TUCSON_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "DT_START DESC",
            "where": TUCSON_SLA_WHERE,
            "scope": (
                "BUSLIC business licenses (93,483 rows; native outSR=4326 "
                "point geometry primary, FULLADDRESS geocode supplement for "
                "null-geometry rows; future-dated DT_START sentinels "
                "excluded by the where guard; host is ANSI-date - spine "
                "must add gis.tucsonaz.gov to ANSI_DATE_LITERAL_HOSTS; "
                "county-wide CITY values gated by metro bbox containment; "
                "frozen PDSD_PERMITS_ALL permits archive NOT registered)"
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
}


def get_tucson_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Tucson feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in TUCSON_FEED_SPECS:
        available = ", ".join(sorted(TUCSON_FEED_SPECS))
        raise KeyError(
            f"'{TUCSON_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = TUCSON_FEED_SPECS[feed_name]
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
    metro_bbox=TUCSON_METRO_BBOX,
    division_bboxes=TUCSON_DIVISION_BBOXES,
    submarkets=TUCSON_SUBMARKETS,
    divisions=TUCSON_DIVISIONS,
    contains=is_in_tucson_metro,
)

__all__ = [
    "REGISTRATION",
    "TUCSON_CITY_ID",
    "TUCSON_DIVISIONS",
    "TUCSON_DIVISION_BBOXES",
    "TUCSON_FEED_SPECS",
    "TUCSON_GEOCODE_CONTEXT",
    "TUCSON_METRO_BBOX",
    "TUCSON_SLA_ALARM_EXEMPT_REASON",
    "TUCSON_SLA_ENDPOINT",
    "TUCSON_SLA_WHERE",
    "TUCSON_SUBMARKETS",
    "get_tucson_dataset",
    "is_in_greater_tucson_metro",
    "is_in_tucson_metro",
]
