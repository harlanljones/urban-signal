"""Anchorage, AK spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the Municipality of
Anchorage, Alaska — the Anchorage Bowl plus Eagle River/Chugiak in the
north and Girdwood at the head of Turnagain Arm in the south (deliberately
not overlapping any sibling leaf box; the nearest census-neighbor, Pierce
County WA, sits a sea lane away).

Feed scope (probed 2026-08-27, docs/research/probe-anchorage.md; re-probed
live 2026-08-28 at implementation). Anchorage is a DEEDS-only Tier-1 metro:
the assessor's property file is the one live, deed-bearing, natively
geospatial feed on the city's real open-data surface (AGOL orgs
``MOA_HostedServices``/``MOAGIS`` hosting on ``services2.arcgis.com``;
``opendata.muni.org`` is an Apache directory listing and ``gis.muni.org``
has no REST directory). Served by the existing ``ArcGISClient``:

* DEEDS — ``PropertyInformation_Hosted/FeatureServer/0`` (assessor property
  file, 84 attribute fields). ``Deed_Date`` is an ``esriFieldTypeDate``
  column: epoch-ms on the wire, flattened to an ISO 8601 UTC string by
  ``ArcGISClient`` before parsing (``_parse_datetime`` then reads it via
  ``fromisoformat``). Date-only values are stamped noon UTC
  (``1787659200000`` → ``2026-08-25T12:00:00+00:00``), not local-midnight
  Anchorage time (AKST/AKDT, UTC-9/UTC-8) — parse against the UTC string
  and never against a local-midnight assumption. ``PUBDATE`` is the other
  and only date column.
* PERMITS — absent at tier: only ``MJ_Permits_Hosted`` exists (marijuana
  local permits, frozen at ``Approved_to_Operate`` 2023-04-24). Tier 3.
* COMPLAINTS_311 — absent (Anchorage 311 is an app with no public bulk
  endpoint). Tier 3.
* SLA — absent (no business-license feed; the frozen MJ permits are the
  only license-adjacent surface). Tier 3.

Implementation re-probe (2026-08-28, live, watermark confirmed): the five
future ``Deed_Date`` sentinels from the probe still pin the lexical top of
the layer (max 2035-03-03), and the newest NON-future row is still
2026-08-25 (three parcels: OBJECTIDs 211515894 / 211522925 / 211547020,
re-captured byte-verbatim as the fixtures) — ``PUBDATE`` max
2026-08-26T23:23:21Z confirms the daily republish continues. ``Deed_Date``
is a snapshot watermark, not a transaction log: the file is the assessor's
last-deed-per-parcel parcel roll, republished as a batch, so freshness is
gated on the publisher's daily job. ``GIS_Site_City`` counts verified live:
Anchorage 74,625 / Eagle River 9,653 / Chugiak 3,274 / Girdwood 1,613
parcels — Eagle River/Chugiak is strongly evidenced as a submarket;
Girdwood rides inside the metro box but is too thin to register.

Native parcel polygons (``outSR=4326`` rings reduced to a centroid) supply
every row's coordinates, so ``needs_geocode`` stays False — no ADR-0004
hook. The host accepts ISO-string date comparisons (``Deed_Date >
'2026-08-25T12:00:00+00:00'`` verified live), so it must NOT be added to
``ANSI_DATE_LITERAL_HOSTS``.
"""

from typing import Dict

from src.producers.field_maps_anchorage import (
    DEEDS_FIELD_MAP,
    FIELD_MAP,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

ANCHORAGE_CITY_ID: str = "anchorage"

# Municipality of Anchorage bbox. Permissive: it only has to keep every live
# parcel inside (the Bowl ~61.15-61.25 / -150.05 to -149.72; Eagle River
# ~61.32, -149.55; Chugiak ~61.39, -149.47; Girdwood ~60.94, -149.15) and
# stay out of the Mat-Su Borough (Wasilla 61.58, Palmer 61.60) and the
# Kenai Peninsula (Soldotna 60.49). South edge at Portage (60.80), north at
# Eklutna (61.50).
ANCHORAGE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 60.80,
    "max_lat": 61.50,
    "min_lng": -150.25,
    "max_lng": -148.95,
}

# Registration-contract center: downtown Anchorage (Town Square / 4th Ave).
ANCHORAGE_CENTER: Dict[str, float] = {"lat": 61.2176, "lng": -149.8997}

# 5 Anchorage Division Bounding Boxes (strictly nested inside the metro bbox)
ANCHORAGE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_CORE":       {"min_lat": 61.197, "max_lat": 61.232, "min_lng": -149.925, "max_lng": -149.862},
    "MIDTOWN_EAST":        {"min_lat": 61.185, "max_lat": 61.200, "min_lng": -149.915, "max_lng": -149.820},
    "EAST_ANCHORAGE":      {"min_lat": 61.188, "max_lat": 61.230, "min_lng": -149.815, "max_lng": -149.735},
    "WEST_ANCH":           {"min_lat": 61.135, "max_lat": 61.200, "min_lng": -150.030, "max_lng": -149.895},
    "EAGLE_RIVER_CHUGIAK": {"min_lat": 61.280, "max_lat": 61.450, "min_lng": -149.660, "max_lng": -149.420},
}


def is_in_anchorage_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Anchorage metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        ANCHORAGE_METRO_BBOX["min_lat"] <= lat <= ANCHORAGE_METRO_BBOX["max_lat"]
        and ANCHORAGE_METRO_BBOX["min_lng"] <= lng <= ANCHORAGE_METRO_BBOX["max_lng"]
    )


def is_in_anchorage(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_anchorage_metro`."""
    return is_in_anchorage_metro(lat, lng)


# ---------------------------------------------------------------------------
# Anchorage Submarket Registry (8 Submarkets Across 5 Divisions)
# Neighborhood anchors use the well-known community/civic coordinates of the
# Anchorage Bowl street grid (Downtown, South Addition, Midtown, Rogers Park,
# Russian Jack, Sand Lake, Turnagain) plus the Eagle River/Chugiak corridor
# evidenced by 12,927 live ``GIS_Site_City`` parcels. Division bboxes are
# hand-authored and nest inside the metro box.
# ---------------------------------------------------------------------------

ANCHORAGE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CORE (2 Submarkets)
    # =======================================================================
    "Downtown Anchorage": SubmarketMeta(
        name="Downtown Anchorage",
        borough="DOWNTOWN_CORE",
        lat=61.2176,
        lng=-149.8997,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.84,
        capex=5100000.0,
        permit_vel=26.0,
        shift_ratio=1.42,
        sla=52.0,
        description="The 4th Avenue/City Hall core on the Knik Arm shoreline with office-to-residential conversions, the waterfront redevelopment arc, and the state government office base.",
        city_id="anchorage",
    ),
    "South Addition": SubmarketMeta(
        name="South Addition",
        borough="DOWNTOWN_CORE",
        lat=61.2030,
        lng=-149.8730,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.82,
        capex=4300000.0,
        permit_vel=22.0,
        shift_ratio=1.36,
        sla=48.0,
        description="The 1910s grid south of downtown around the Delaney Park Strip with craftsman and art-deco stock, small-lot infill, and the West Anchorage restaurant row.",
        city_id="anchorage",
    ),
    # =======================================================================
    # MIDTOWN_EAST (2 Submarkets)
    # =======================================================================
    "Midtown": SubmarketMeta(
        name="Midtown",
        borough="MIDTOWN_EAST",
        lat=61.1955,
        lng=-149.9030,
        zoom=14.5,
        pitch=42.0,
        base_lims=0.81,
        capex=4600000.0,
        permit_vel=25.0,
        shift_ratio=1.40,
        sla=50.0,
        description="The C Street/Northern Lights office-retail node between downtown and the airport with 1980s commercial stock cycling toward multifamily conversion.",
        city_id="anchorage",
    ),
    "Rogers Park": SubmarketMeta(
        name="Rogers Park",
        borough="MIDTOWN_EAST",
        lat=61.1915,
        lng=-149.8420,
        zoom=14.5,
        pitch=38.0,
        base_lims=0.78,
        capex=3700000.0,
        permit_vel=20.0,
        shift_ratio=1.33,
        sla=46.0,
        description="The post-war tract grid east of the Debarr corridor around Rogers Park Elementary with steady renovation trades and duplex conversion pressure.",
        city_id="anchorage",
    ),
    # =======================================================================
    # EAST_ANCHORAGE (1 Submarket)
    # =======================================================================
    "Russian Jack": SubmarketMeta(
        name="Russian Jack",
        borough="EAST_ANCHORAGE",
        lat=61.2100,
        lng=-149.7870,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.72,
        capex=3200000.0,
        permit_vel=17.0,
        shift_ratio=1.27,
        sla=41.0,
        description="The northeast hills around Russian Jack Springs Park with 1960s-70s subdivisions, deep starter-home turnover, and the Muldoon-edge rental register.",
        city_id="anchorage",
    ),
    # =======================================================================
    # WEST_ANCH (2 Submarkets)
    # =======================================================================
    "Sand Lake": SubmarketMeta(
        name="Sand Lake",
        borough="WEST_ANCH",
        lat=61.1500,
        lng=-149.9900,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.75,
        capex=3900000.0,
        permit_vel=19.0,
        shift_ratio=1.30,
        sla=44.0,
        description="The lake-country southwest around the airport was with mid-century ramblers, floatplane-adjacent lots, and steady executive teardown/rebuild.",
        city_id="anchorage",
    ),
    "Turnagain": SubmarketMeta(
        name="Turnagain",
        borough="WEST_ANCH",
        lat=61.1900,
        lng=-149.9670,
        zoom=14.5,
        pitch=38.0,
        base_lims=0.79,
        capex=4100000.0,
        permit_vel=21.0,
        shift_ratio=1.34,
        sla=47.0,
        description="The bluff-top residential arm west of Spenard with Cook Inlet views, chunky 1950s-60s stock, and renovation-led permit flow near Kincaid.",
        city_id="anchorage",
    ),
    # =======================================================================
    # EAGLE_RIVER_CHUGIAK (1 Submarket)
    # =======================================================================
    "Eagle River & Chugiak": SubmarketMeta(
        name="Eagle River & Chugiak",
        borough="EAGLE_RIVER_CHUGIAK",
        lat=61.3220,
        lng=-149.5480,
        zoom=13.0,
        pitch=35.0,
        base_lims=0.73,
        capex=3500000.0,
        permit_vel=18.0,
        shift_ratio=1.29,
        sla=43.0,
        description="The Glenn Highway bedroom corridor from Eagle River through Chugiak to Eklutna with 12,927 live assessor parcels, JBER-driven demand, and large-lot subdivision growth.",
        city_id="anchorage",
    ),
}


# ---------------------------------------------------------------------------
# Anchorage Divisions Catalog
# ---------------------------------------------------------------------------

ANCHORAGE_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=61.2103,
        center_lng=-149.8864,
        zoom=13.5,
        bbox=ANCHORAGE_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in ANCHORAGE_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id="anchorage",
    ),
    "MIDTOWN_EAST": BoroughMeta(
        name="MIDTOWN_EAST",
        center_lat=61.1935,
        center_lng=-149.8725,
        zoom=13.5,
        bbox=ANCHORAGE_DIVISION_BBOXES["MIDTOWN_EAST"],
        submarkets=[k for k, v in ANCHORAGE_SUBMARKETS.items() if v.borough == "MIDTOWN_EAST"],
        city_id="anchorage",
    ),
    "EAST_ANCHORAGE": BoroughMeta(
        name="EAST_ANCHORAGE",
        center_lat=61.2100,
        center_lng=-149.7870,
        zoom=13.0,
        bbox=ANCHORAGE_DIVISION_BBOXES["EAST_ANCHORAGE"],
        submarkets=[k for k, v in ANCHORAGE_SUBMARKETS.items() if v.borough == "EAST_ANCHORAGE"],
        city_id="anchorage",
    ),
    "WEST_ANCH": BoroughMeta(
        name="WEST_ANCH",
        center_lat=61.1700,
        center_lng=-149.9785,
        zoom=13.0,
        bbox=ANCHORAGE_DIVISION_BBOXES["WEST_ANCH"],
        submarkets=[k for k, v in ANCHORAGE_SUBMARKETS.items() if v.borough == "WEST_ANCH"],
        city_id="anchorage",
    ),
    "EAGLE_RIVER_CHUGIAK": BoroughMeta(
        name="EAGLE_RIVER_CHUGIAK",
        center_lat=61.3220,
        center_lng=-149.5480,
        zoom=12.0,
        bbox=ANCHORAGE_DIVISION_BBOXES["EAGLE_RIVER_CHUGIAK"],
        submarkets=[k for k, v in ANCHORAGE_SUBMARKETS.items() if v.borough == "EAGLE_RIVER_CHUGIAK"],
        city_id="anchorage",
    ),
}

ANC_DIVISION_BBOXES = ANCHORAGE_DIVISION_BBOXES
ANC_SUBMARKETS = ANCHORAGE_SUBMARKETS
ANC_DIVISIONS = ANCHORAGE_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-27 and re-probed live 2026-08-28 against the services2
# AGOL org (the city's real open-data surface). Sketch matches
# docs/research/probe-anchorage.md with the live confirmations recorded in
# the module docstring: newest non-future Deed_Date 2026-08-25, five future
# sentinels (max 2035-03-03), PUBDATE daily republish.
# ---------------------------------------------------------------------------
ANCHORAGE_DEEDS_ENDPOINT = (
    "https://services2.arcgis.com/Ce3DhLRthdwbHlfF/arcgis/rest/services/"
    "PropertyInformation_Hosted/FeatureServer/0"
)

# Future-dated Deed_Date rows are sentinels (5 live, max 2035-03-03):
# exclude them at the source so neither the high watermark nor staleness
# math sees them. Verified live on the host; the host also accepts ISO
# string comparisons (NOT an ANSI_DATE_LITERAL_HOSTS member).
ANCHORAGE_DEEDS_WHERE = "Deed_Date <= CURRENT_TIMESTAMP"

ANCHORAGE_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "deeds": {
        "endpoint": ANCHORAGE_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Deed_Date",
        "id_keys": ["Parcel_ID", "GIS_ParcelNum11", "OBJECTID"],
        "topic_key": "topic_deeds",
        "interval_seconds": 600.0,
        "producer_key": "deeds",
        "extra": {
            # Native parcel polygons (outSR=4326 rings -> centroid) supply
            # every row's coordinates; the ADR-0004 geocode hook is NOT
            # declared. ``watermark_exclude`` is deliberately NOT set: the
            # arcgis path ignores it (CSV-client-only) — the where guard
            # above plus the scheduler's US-111 future guard do the work.
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "expected_cadence_days": 3,
            "order_by": "Deed_Date DESC",
            "where": ANCHORAGE_DEEDS_WHERE,
            "non_spatial": False,
            "scope": (
                "Anchorage DEEDS via the assessor PropertyInformation_Hosted "
                "property file (last-deed-per-parcel snapshot, 84 fields; "
                "native parcel polygons, NOT address-only). BATCH "
                "PUBLICATION: the whole file republishes daily (PUBDATE max "
                "2026-08-26T23:23:21Z at re-probe) and Deed_Date advances on "
                "business days, so Fri->Mon is a NORMAL 3-day watermark gap; "
                "expected_cadence_days=3 alarms only when the daily batch "
                "job stalls past a full weekend plus Monday, not on weekend "
                "recording gaps. FUTURE SENTINELS: 5 Deed_Date rows date to "
                "2027-2035 (max 2035-03-03) and are excluded at source by "
                "the Deed_Date<=CURRENT_TIMESTAMP where guard (verified "
                "live); the scheduler US-111 future guard is the second line "
                "of defense. No sale-price/consideration column exists — "
                "document_amount parses 0.0 by design; assessed values must "
                "not masquerade as deed amounts (NOLA precedent). "
                "party2_grantee=Owner_Name (snapshot grain: the current "
                "owner is the last deed's GRANTEE). Date columns are epoch-ms "
                "stamped noon UTC on the wire — compare ISO strings, never "
                "local-midnight AKST/AKDT. GIS_Site_City: Anchorage 74,625 / "
                "Eagle River 9,653 / Chugiak 3,274 / Girdwood 1,613 parcels."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_anchorage_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Anchorage feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent (permits/SLA are absent at tier; 311 has no public bulk
    endpoint).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in ANCHORAGE_FEED_SPECS:
        available = ", ".join(sorted(ANCHORAGE_FEED_SPECS))
        raise KeyError(
            f"'{ANCHORAGE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = ANCHORAGE_FEED_SPECS[feed_name]
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
    metro_bbox=ANCHORAGE_METRO_BBOX,
    division_bboxes=ANCHORAGE_DIVISION_BBOXES,
    submarkets=ANCHORAGE_SUBMARKETS,
    divisions=ANCHORAGE_DIVISIONS,
    contains=is_in_anchorage_metro,
)

__all__ = [
    "ANC_DIVISIONS",
    "ANC_DIVISION_BBOXES",
    "ANC_SUBMARKETS",
    "ANCHORAGE_CENTER",
    "ANCHORAGE_CITY_ID",
    "ANCHORAGE_DEEDS_ENDPOINT",
    "ANCHORAGE_DEEDS_WHERE",
    "ANCHORAGE_DIVISIONS",
    "ANCHORAGE_DIVISION_BBOXES",
    "ANCHORAGE_FEED_SPECS",
    "ANCHORAGE_METRO_BBOX",
    "ANCHORAGE_SUBMARKETS",
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "REGISTRATION",
    "get_anchorage_dataset",
    "is_in_anchorage",
    "is_in_anchorage_metro",
]
