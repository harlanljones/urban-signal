"""Louisville / Kentucky per-city field-map support (US-148).

Louisville's two ArcGIS feeds — Louisville Metro 311 service requests and the
Kentucky Alcoholic Beverage Control liquor-license feed — spell their columns
differently from the shared municipal row parsers.

The shared parsers consult the map before their generic fallback chains.
"""

LOUISVILLE_311_FIELD_MAP = {
    "incident_id": ["service_request_id", "ObjectId"],
    "latitude": ["latitude"],
    "longitude": ["longitude"],
    "complaint_type": ["service_name", "description"],
    "created_date": ["requested_datetime"],
    "closed_date": ["closed_date", "updated_datetime"],
    "incident_address": ["address"],
    "borough": ["council_district"],
    "zipcode": ["zip_code"],
    "status": ["status_description"],
}

LOUISVILLE_SLA_FIELD_MAP = {
    "license_id": ["LicenseNumber", "ObjectId"],
    "latitude": ["Latitude"],
    "longitude": ["Longitude"],
    "effective_date": ["IssueDate", "EffectiveDate"],
    "expiration_date": ["ExpiryDate"],
    "license_type": ["LicenseType"],
    "premises_name": ["Licensee"],
    "dba": ["DBA"],
    "address_street": ["PremisesStreet", "PremisesCityState"],
    "status": ["Status"],
    "borough": ["County", "City"],
}

FIELD_MAP = {
    "COMPLAINTS_311": LOUISVILLE_311_FIELD_MAP,
    "SLA": LOUISVILLE_SLA_FIELD_MAP,
}
