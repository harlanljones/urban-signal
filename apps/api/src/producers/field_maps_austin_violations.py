"""Austin Code Complaint field map (US-210).

Maps canonical ``ViolationEvent`` field names to the Austin Code Department
code-enforcement columns on ``6wtj-zbtb`` (underlying dataset behind the
``3g2y-5uvh`` story asset). Probed live 2026-08-30 (n=82,854, native
``latitude``/``longitude`` + ``location`` point, stable ``case_id`` PK,
``opened_date`` watermark) — no geocoding required.

This is a distinct signal from the registered Austin 311 feed: code-enforcement
cases carry their own case lifecycle (opened → closed), a parcel id, and a
department/inspector — a VIOLATIONS-family feed subject to the US-72 ablation
rule before any LIMS use.

This module is a leaf: the shared ``field_maps.py`` dispatch is untouched.
Maps are keyed by canonical ``ViolationEvent`` field names, which the
``ViolationsProducer`` walks when parsing Socrata rows.
"""


AUSTIN_VIOLATIONS_FIELD_MAP: dict[str, list[str]] = {
    "violation_id": ["case_id", "violation_id"],
    "code": ["case_type", "code"],
    "status": ["status", "priority"],
    "description": ["description", "case_type", "description"],
    "borough": ["city", "council_district", "borough"],
    "address": ["address", "house_number", "street_name"],
    "zipcode": ["zip_code", "zipcode", "zip"],
    "latitude": ["latitude"],
    "longitude": ["longitude"],
    "status_date": ["opened_date", "status_date"],
}