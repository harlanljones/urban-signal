"""Per-city field maps for Anaheim, CA (US-249 leaf), imported by the shared
parsers.

Anaheim is a TWO-FEED metro on the city's official ArcGIS Hub
(``anaheim.opendata.arcgis.com``), whose datasets live on the city AGOL org
``services3.arcgis.com/hPs600I3X0RTaaaq`` (live-probed 2026-08-28):

* PERMITS — ``Accela_Building_Permits/FeatureServer/0`` (191,477 rows).
  Column spellings do not match the shared Socrata chains, so the map lives
  here as a leaf rather than growing ``src/producers/field_maps.py`` (spine).
* SLA — ``ActiveBusinessLicenses/FeatureServer/0`` (15,263 rows, the
  ``casestatus='Active'`` snapshot of the full-history layer).

Coordinate contract (pinned by tests):

* PERMITS — native point geometry requested with ``outSR=4326``; the layer's
  store SR is **WKID 2230 (NAD83 California zone 6, ftUS)** and the host
  honors the outSR request (live fixtures come back as degrees — unlike the
  full-history license layer below). No ``latitude``/``longitude``
  candidates appear in the map; the layer has no projected X/Y *attribute*
  columns to mis-map.
* SLA — the ``ActiveBusinessLicenses`` layer carries WGS84 degree geometry
  (818 degrees / 0 feet / 1,182 null in a 2,000-row live scan). Null-geometry
  rows carry no latitude/longitude keys and fall to the ADR-0004 geocode
  supplement on ``address``. The **full-history** ``Business_Licenses`` layer
  is deliberately unmapped and unregistered: it declares SR 4326 while
  storing WKID 2230 state-plane feet and ignores ``outSR`` (x≈6.1e6 with
  outSR=4326 on the 2026-08-28 probe), and the SLA producer has no
  projected-coordinate guard — feet would ride the geometry lift straight
  onto the wire as latitude/longitude.

Date contract (pinned by tests):

* The SLA layer's dates are ``esriFieldTypeDateOnly`` — plain
  ``"YYYY-MM-DD"`` strings on the wire (an ANSI-date-only host); the client
  discovers only ``esriFieldTypeDate`` as date fields, so they pass through
  ``_flatten_feature`` untouched and parse at the producer.
* ``effective_date`` maps ``applicationdate`` (0 nulls, 0 future sentinels,
  newest 2026-06-02) — NOT ``opendate``, which carries year-3013/2204
  future-date sentinels on live Active rows (BUS2014-01614 "3013-10-31",
  BUS2024-00396 "2204-01-23"). ``expirationdate`` is mapped as-is and
  carries the same sentinel family on a handful of rows.
* PERMITS ``permitissued`` is a true esri Date (epoch-ms → ISO on flatten)
  and carries exactly one future-dated sentinel (BLD2026-01741 @
  2026-09-13); the spec's ``where`` excludes future rows.

PII is dropped at the map: ``ownername`` (person names, "DANIEL MC INTYRE,
PRESIDENT"), ``contractorsname``/``contractorsphone``, and the redundant
``entityname`` legal-entity column are never candidates.
"""


# Canonical permit event field -> Accela_Building_Permits/FeatureServer/0
# column spellings. Live layer (2026-08-28): OBJECTID is the OID, geometry
# is the coordinate source, permitissued is the watermark.
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    # casenumber (BLD2026-…) is the id_keys head; OBJECTID keeps
    # coordinate-less/dedup edge rows addressable if a case number is
    # ever missing client-side (Henderson precedent).
    "job_id": ["casenumber", "OBJECTID"],
    "issuance_date": ["permitissued"],
    "filing_date": ["applicationreceived"],
    "status": ["casestatus"],
    "job_type": ["typeofwork"],
    "cost": ["jobvaluation"],
    "address_street": ["address"],
}


# Canonical SLA event field -> ActiveBusinessLicenses/FeatureServer/0 column
# spellings. ``applicationdate`` doubles as the watermark; ``opendate`` is
# deliberately not a candidate (future-date sentinels, see module docstring).
SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["casenumber", "objectid"],
    "dba": ["businessname"],
    "premises_name": ["businessname"],
    "license_type": ["naicscode"],
    "status": ["casestatus"],
    "effective_date": ["applicationdate"],
    "expiration_date": ["expirationdate"],
    "address_street": ["address"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Anaheim, CA"

# Columns that exist on the live feeds and must never become map candidates.
# ``ownername`` is a person name; the contractor block is permit-party PII;
# ``entityname`` is a legal-entity name redundant with businessname (and
# person-shaped on Sole Proprietor rows). ``opendate`` is excluded as a
# sentinel carrier, not PII.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "ownername",
    "contractorsname",
    "contractorsphone",
    "entityname",
)

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]
