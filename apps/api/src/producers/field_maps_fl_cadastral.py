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
- ``ASMNT_YR`` = assessment year (the layer holds one roll: 2026 on
  2026-10-02). ``CO_NO`` = 2-digit FL DOR county code (11–77).
  ``EFF_YR_BLT`` = effective year built (construction-year proxy).
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
# CO_NO is the 2-digit FDOR county code: the alphabetical index of the 67 FL
# counties plus 10, so Alachua is 11 and Washington 77 (Marion 52 and Orange
# 58 hold 286,275 and 492,806 parcels on the layer, read 2026-10-02). The
# FIPS codes are the standard Census codes and are NOT "12" + the FDOR code —
# Dade (Miami-Dade) carries FIPS 12086 at FDOR 23, so the mapping is spelled
# out in full rather than derived. The table numbered the counties 1–67
# until 2026-10-02, which registered Jackson County's parcels as Ocala's
# (42) and Levy County's as Orlando's (48).
# Use this to resolve county → metro via
# ``geography_crosswalk.city_for_county_fips(fips)``.
FL_COUNTY_CODE_TO_FIPS: dict[int, str] = {
    11: "12001",  # Alachua
    12: "12003",  # Baker
    13: "12005",  # Bay
    14: "12007",  # Bradford
    15: "12009",  # Brevard
    16: "12011",  # Broward
    17: "12013",  # Calhoun
    18: "12015",  # Charlotte
    19: "12017",  # Citrus
    20: "12019",  # Clay
    21: "12021",  # Collier
    22: "12023",  # Columbia
    23: "12086",  # Dade / Miami-Dade
    24: "12027",  # DeSoto
    25: "12029",  # Dixie
    26: "12031",  # Duval
    27: "12033",  # Escambia
    28: "12035",  # Flagler
    29: "12037",  # Franklin
    30: "12039",  # Gadsden
    31: "12041",  # Gilchrist
    32: "12043",  # Glades
    33: "12045",  # Gulf
    34: "12047",  # Hamilton
    35: "12049",  # Hardee
    36: "12051",  # Hendry
    37: "12053",  # Hernando
    38: "12055",  # Highlands
    39: "12057",  # Hillsborough
    40: "12059",  # Holmes
    41: "12061",  # Indian River
    42: "12063",  # Jackson
    43: "12065",  # Jefferson
    44: "12067",  # Lafayette
    45: "12069",  # Lake
    46: "12071",  # Lee
    47: "12073",  # Leon
    48: "12075",  # Levy
    49: "12077",  # Liberty
    50: "12079",  # Madison
    51: "12081",  # Manatee
    52: "12083",  # Marion
    53: "12085",  # Martin
    54: "12087",  # Monroe
    55: "12089",  # Nassau
    56: "12091",  # Okaloosa
    57: "12093",  # Okeechobee
    58: "12095",  # Orange
    59: "12097",  # Osceola
    60: "12099",  # Palm Beach
    61: "12101",  # Pasco
    62: "12103",  # Pinellas
    63: "12105",  # Polk
    64: "12107",  # Putnam
    65: "12109",  # St. Johns
    66: "12111",  # St. Lucie
    67: "12113",  # Santa Rosa
    68: "12115",  # Sarasota
    69: "12117",  # Seminole
    70: "12119",  # Sumter
    71: "12121",  # Suwannee
    72: "12123",  # Taylor
    73: "12125",  # Union
    74: "12127",  # Volusia
    75: "12129",  # Wakulla
    76: "12131",  # Walton
    77: "12133",  # Washington
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