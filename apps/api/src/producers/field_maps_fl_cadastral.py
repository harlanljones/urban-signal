"""Field maps for the FL Statewide Cadastral (US-398).

LEAF module — NOT imported by the shared producers at runtime. In production
each map is merged into the owning city's ``CityRegistration``
``datasets[FeedType.PERMITS].field_map`` in ``src/spatial/city_registry.py``
(the spine) when the orchestrator applies the interlock; this file proves the
proposed spellings resolve through the ``DOBPermitsProducer`` row path and
hands the spine a copy-pasteable contract.

Source: FDOR Statewide Cadastral ArcGIS FeatureServer (live-verified 2026-08-30
from this host):
https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Cadastral/FeatureServer/0

- 2M+ polygon parcels, 121 fields, ``objectIdField: "OBJECTID"``,
  ``maxRecordCount: 2000``, ``geometryType: esriGeometryPolygon``.
- ``ASMNT_YR`` = assessment year (2025). ``CO_NO`` = 2-digit FL DOR county
  code. ``EFF_YR_BLT`` = effective year built (construction-year proxy).
  ``NCONST_VAL`` = new-construction value (cost proxy). ``DEL_VAL`` =
  demolition value. ``JV_CHNG`` = just/market value change.

LABEL: Annual, assessment-derived → a construction-activity context covariate,
never a permit event stream. The ``EFF_YR_BLT`` within 1–3 years of
``ASMNT_YR`` is the defensible building-completion signal.

Canonical fields mirror the chains in ``DOBPermitsProducer`` /
``field_maps.first_mapped``: job_id, issuance_date, cost, bbl, borough,
status, latitude, longitude. Keyed to ``FeedType.PERMITS`` semantics of
``field_maps.resolve_field_map``.
"""

# FL DOR county code → 5-digit Census FIPS code.
# CO_NO is the 2-digit FDOR county code (01–67), alphabetical over the 67 FL
# counties. The FIPS codes are the standard Census codes and are NOT "12" +
# the FDOR code — Dade (Miami-Dade) carries FIPS 12086 at FDOR 13, so the
# mapping is spelled out in full rather than derived. Verified against the
# Census County FIPS codes and the FDOR alphabetical county order.
# Use this to resolve county → metro via
# ``geography_crosswalk.city_for_county_fips(fips)``.
FL_COUNTY_CODE_TO_FIPS: dict[int, str] = {
    1: "12001",  # Alachua
    2: "12003",  # Baker
    3: "12005",  # Bay
    4: "12007",  # Bradford
    5: "12009",  # Brevard
    6: "12011",  # Broward
    7: "12013",  # Calhoun
    8: "12015",  # Charlotte
    9: "12017",  # Citrus
    10: "12019",  # Clay
    11: "12021",  # Collier
    12: "12023",  # Columbia
    13: "12086",  # Dade / Miami-Dade
    14: "12027",  # DeSoto
    15: "12029",  # Dixie
    16: "12031",  # Duval
    17: "12033",  # Escambia
    18: "12035",  # Flagler
    19: "12037",  # Franklin
    20: "12039",  # Gadsden
    21: "12041",  # Gilchrist
    22: "12043",  # Glades
    23: "12045",  # Gulf
    24: "12047",  # Hamilton
    25: "12049",  # Hardee
    26: "12051",  # Hendry
    27: "12053",  # Hernando
    28: "12055",  # Highlands
    29: "12057",  # Hillsborough
    30: "12059",  # Holmes
    31: "12061",  # Indian River
    32: "12063",  # Jackson
    33: "12065",  # Jefferson
    34: "12067",  # Lafayette
    35: "12069",  # Lake
    36: "12071",  # Lee
    37: "12073",  # Leon
    38: "12075",  # Levy
    39: "12077",  # Liberty
    40: "12079",  # Madison
    41: "12081",  # Manatee
    42: "12083",  # Marion
    43: "12085",  # Martin
    44: "12087",  # Monroe
    45: "12089",  # Nassau
    46: "12091",  # Okaloosa
    47: "12093",  # Okeechobee
    48: "12095",  # Orange
    49: "12097",  # Osceola
    50: "12099",  # Palm Beach
    51: "12101",  # Pasco
    52: "12103",  # Pinellas
    53: "12105",  # Polk
    54: "12107",  # Putnam
    55: "12109",  # St. Johns
    56: "12111",  # St. Lucie
    57: "12113",  # Santa Rosa
    58: "12115",  # Sarasota
    59: "12117",  # Seminole
    60: "12119",  # Sumter
    61: "12121",  # Suwannee
    62: "12123",  # Taylor
    63: "12125",  # Union
    64: "12127",  # Volusia
    65: "12129",  # Wakulla
    66: "12131",  # Walton
    67: "12133",  # Washington
}

# Standalone field map — one entry per FL metro that will adopt this spec.
# These are the PERMITS canonical keys the ``DOBPermitsProducer`` parser
# consults via ``field_maps.first_mapped``.
# NOTE: The cadastral is a covariate, not a permit event stream.  ``job_type``
# is intentionally unmapped — the producer's ``NEW CONSTRUCTION`` / ``NB``
# classification is not derivable from this source.  The spine wires the
# construction signal via ``EFF_YR_BLT`` comparison at the feature level.
FL_CADASTRAL_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["OBJECTID", "PARCEL_ID"],
    "issuance_date": ["EFF_YR_BLT"],
    "cost": ["NCONST_VAL"],
    "bbl": ["PARCEL_ID"],
    "borough": ["CO_NO"],
    "status": ["JV_CHNG"],
}

FIELD_MAPS: dict[str, dict[str, list[str]]] = {
    "fl_cadastral": FL_CADASTRAL_FIELD_MAP,
}