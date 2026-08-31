"""NYC DOHMH Restaurant Inspection field map (US-208).

Maps canonical ``InspectionEvent`` field names to the DOHMH Socrata columns on
``43nn-pn8j``. Probed live 2026-08-30 (n≈296K, ``record_date`` fresh
2026-08-27): the feed carries native ``latitude``/``longitude`` numbers plus a
``location`` point container, a stable ``camis`` primary key, and a proper
calendar-date ``inspection_date`` watermark — no geocoding required.

Some rows carry ``0,0`` placeholder coordinates (the Socrata ``location``
column) — the producer drops those (a restaurant at 0,0 is not a restaurant
at the Greenwich meridian).

This module is a leaf: the shared ``field_maps.py`` dispatch is untouched.
Maps are keyed by canonical ``InspectionEvent`` field names, which the
``InspectionsProducer`` walks when parsing Socrata rows.
"""


NYC_INSPECTIONS_FIELD_MAP: dict[str, list[str]] = {
    "inspection_id": ["camis", "inspection_id"],
    "business_name": ["dba", "business_name"],
    "license_category": ["cuisine_description", "inspection_type", "license_category"],
    "license_status": ["action", "license_status"],
    "result": ["action", "grade", "result"],
    "violation_level": ["critical_flag", "violation_level"],
    "violation_desc": ["violation_description", "violation_desc"],
    "borough": ["boro", "borough"],
    # DOHMH stores building/street as separate columns; the producer composes
    # them into "123 BROADWAY", so leave building/street off the address
    # candidate list (a first-match on `building` would emit a bare "123").
    "address": ["address"],
    "zipcode": ["zipcode", "zip"],
    "latitude": ["latitude"],
    "longitude": ["longitude"],
    "issued_date": ["inspection_date", "issued_date"],
    "result_date": ["grade_date", "record_date", "result_date"],
}
