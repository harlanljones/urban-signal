"""Per-city field maps for Bridgeport, CT (US-419), imported by the shared parsers.

Bridgeport is a TWO-FEED PARTIAL metro on Connecticut's statewide Socrata portal
(``data.ct.gov``): SLA (State Licenses and Credentials, ``ngch-56tr``) and DEEDS
(Real Estate Sales, ``5mzw-sjtu``). Both are state-level tables filtered to the
city, and both ship address strings rather than a native WGS84 latitude/longitude
column the shared producers actually read, so both feeds declare
``needs_geocode=True`` (ADR-0004) and this map intentionally omits coordinate
slots.

The spellings do not match the shared Socrata chains (``licenseno``/``issdttm``/
``descript``/``businessname``), and the CT columns differ from Hartford's stale
inline map (which references nonexistent ``license_number``/``credential_type``/
``effective_date`` columns), so the map lives here as a leaf rather than growing
``src/producers/field_maps.py`` (spine).

Coordinate contract (pinned by tests):

* SLA — no native latitude/longitude columns (``address``/``city``/``state``/
  ``zip`` only). The map omits latitude/longitude so the producer falls through
  to the address-geocode hook (``geocode_context="Bridgeport, CT"``).
* DEEDS — native ``geo_coordinates`` is a nested Point (WGS84 ``[lng, lat]``,
  present on ~30.6% of ``town='Bridgeport'`` rows) but the shared deeds
  producer's loc fallback reads ``the_geom``/``point``/``location``/
  ``georeference``/``shape``/WKT — never ``geo_coordinates``. The map omits
  latitude/longitude so the feed relies on ``needs_geocode=True`` + ``address``.
  The spine hold SHOULD add ``geo_coordinates`` to the deeds producer's loc
  fallback; this leaf documents that gap rather than papering over it.
"""

SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["credentialid", "fullcredentialcode"],
    "license_type": ["credential", "credentialtype"],
    "effective_date": ["effectivedate", "issuedate"],
    "expiration_date": ["expirationdate"],
    "address_street": ["address"],
    "zipcode": ["zip"],
    "borough": ["city"],
    "premises_name": ["businessname", "name"],
    "dba": ["businessname", "name"],
    "status": ["status"],
}

DEEDS_FIELD_MAP: dict[str, list[str]] = {
    "doc_id": ["serialnumber"],
    "recorded_date": ["daterecorded"],
    "document_amount": ["saleamount"],
    "address_street": ["address"],
    "borough": ["town"],
    "doc_type": ["propertytype"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "sla": SLA_FIELD_MAP,
    "deeds": DEEDS_FIELD_MAP,
}

# ``geo_coordinates`` is deliberately NOT a coordinate candidate: the shared
# deeds producer does not read it (see module docstring). It is documented here
# so a spine hold can wire it into the deeds producer's loc fallback rather than
# leaking a native Point into an address-geocode-only feed.
NATIVE_GEO_COORDINATES: str = "geo_coordinates"

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "NATIVE_GEO_COORDINATES",
    "SLA_FIELD_MAP",
]
