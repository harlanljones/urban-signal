"""Per-city field maps for Oakland, CA (US-223), imported by the shared parsers.

Oakland is a TWO-FEED PARTIAL metro on the official Socrata domain
``data.oaklandca.gov``: OAK 311 Call Center service requests
(``quth-gb8e``, 1,185,559 rows) and OPD CrimeWatch Data (``ppgh-7dqv``,
1,281,231 rows). PERMITS, SLA, and DEEDS are absent — no permits dataset
exists on the domain, the Accela citizen portal is interactive-only
(HTTP 000 to bulk APIs), Oakland publishes no business-license registry,
and Alameda County LANDATA (deeds) is unreachable.

Coordinate contract (pinned by tests):

* COMPLAINTS_311 — the dataset's coordinate columns are named like St.
  Louis's projected ``srx``/``sry``, but on THIS dataset they carry
  **WGS84 degrees** (srx = longitude, sry = latitude; verified live across
  2023-2026 rows from Phone and SeeClickFix sources). The map declares
  ``latitude: ["sry"]`` / ``longitude: ["srx"]`` directly; the producer's
  projected-coordinate guard (|lat| > 90 or |lng| > 180 → null → geocode)
  is the second net if the city ever flips the columns to state-plane feet.
* The ``reqaddress`` Socrata location container is **garbage on SeeClickFix
  rows** (live 2026-08-28: latitude "30.009927…", longitude
  "-141.219150…" — mid-Pacific placeholders for every sampled row) and is
  NEVER a candidate. No candidate reads it; the parser's point-container
  fallback never sees it either (the key is ``reqaddress``, not
  ``location``).
* CRIME — coordinates ride the Socrata point container ``location``
  (GeoJSON ``{"type": "Point", "coordinates": [lng, lat]}``), which the
  crime parser's point-container fallback reads natively. No
  ``latitude``/``longitude`` candidates are declared — a dotted candidate
  would hand the parser the coordinate LIST, not floats. Null-location
  rows (58,587 live, 4.6%) fall to the ADR 0004 geocode supplement on the
  ``address`` text column (present on 95.4% of rows).

Watermark/date contract:

* 311 — ``datetimeinit`` (request creation) is the watermark;
  ``datetimeclosed`` feeds ``closed_date``. No future-dated rows exist
  live (0 rows beyond probe time 2026-08-28T12:00Z).
* CRIME — ``datetime`` is the occurred-date watermark. The archive spans
  1950-01-04 → 2026-08-25 (OPD historical backfill); no future-dated rows.
  ``casenumber`` is NOT unique (multi-offense cases repeat it — case
  26-036393 carries three descriptions live), so the spec's id_keys pair
  it with ``description``; the event-level incident_id is the casenumber.

Descriptor note: the 311 parser reads ``descriptor`` only from its generic
chain (service_details / service_subtype / descriptor / sr_short_code /
sr_type); Oakland's free-text ``description`` column ("Sidewalk -
Damage") is not on that chain, so descriptor passes through as None and
complaint_type comes from ``reqcategory``.
"""


# Canonical 311 event field -> OAK 311 (quth-gb8e) column spellings.
# srx/sry are WGS84 degrees on this dataset (srx = longitude, sry =
# latitude) despite echoing St. Louis's projected x/y names — see module
# docstring for the verification and the second-net guard.
OAKLAND_311_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["requestid"],
    "latitude": ["sry"],
    "longitude": ["srx"],
    "created_date": ["datetimeinit"],
    "closed_date": ["datetimeclosed"],
    "complaint_type": ["reqcategory"],
    "borough": ["councildistrict"],
    "incident_address": ["probaddress"],
    "zipcode": ["zipcode"],
}


# Canonical crime event field -> CrimeWatch Data (ppgh-7dqv) column
# spellings. Coordinates are NOT mapped: the Socrata point container is
# read by the parser's GeoJSON fallback; declaring candidates would feed
# it a list. ``address`` is the ADR 0004 geocode supplement for the 4.6%
# null-location rows (and OPD's public-address granularity).
OAKLAND_CRIME_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["casenumber"],
    "offense_type": ["crimetype"],
    "occurred_date": ["datetime"],
    "borough": ["policebeat"],
    "address": ["address"],
}


FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "311": OAKLAND_311_FIELD_MAP,
    "crime": OAKLAND_CRIME_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Oakland, CA"

# Columns that exist on the live datasets and must never become map
# candidates. ``reqaddress`` is the poisoned location container (see
# docstring); ``beat`` is the police beat superseded by ``councildistrict``
# for source neighborhood; ``status``/``source``/``referredto`` are not
# event fields the parsers consume.
DROPPED_NONADDRESS_COLUMNS: tuple[str, ...] = (
    "reqaddress",
    "beat",
    "status",
    "source",
    "referredto",
    ":@computed_region_w23w_jfhw",
)

__all__ = [
    "DROPPED_NONADDRESS_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "OAKLAND_311_FIELD_MAP",
    "OAKLAND_CRIME_FIELD_MAP",
]
