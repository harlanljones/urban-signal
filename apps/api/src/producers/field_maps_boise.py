"""Per-city field-mapping support for Boise's municipal row parsers.

Boise publishes through the City of Boise Open Data Hub as an ArcGIS
FeatureServer. Permit rows carry Idaho Transverse Mercator (EPSG:3694)
state-plane geometry in the `SHAPE__X` / `SHAPE__Y` fields — these are NOT
geographic degrees and MUST be dropped (the shared producer's
`abs(lat) > 90 / abs(lng) > 180` guard does this) and resolved by the
ADR-0004 address geocoder from `SITE_ADDRESS` instead.

This module is the per-city analog of :mod:`src.producers.field_maps`; it
exports one `FIELD_MAP` consumed by the shared permits producer via the
registry's `extra["field_map"]` entry. Kept as a dedicated leaf file so the
spine `field_maps.py` dispatch stays untouched.
"""

from typing import Dict, List

# Residential-only, thin PERMITS feed field spellings for Boise. `latitude` /
# `longitude` are intentionally bound to the state-plane geometry columns so the
# producer guard rejects them; real coordinates come from geocoding the address.
FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["PERMITNUMBER", "PERMIT_NUMBER", "PERMITNO"],
    "latitude": ["SHAPE__Y"],
    "longitude": ["SHAPE__X"],
    "cost": ["ESTIMATEDCOST", "ESTIMATED_COST", "PROJECTCOST", "TOTALCOST"],
    "job_type": ["PERMITTYPE", "PERMIT_TYPE", "WORKDESCRIPTION"],
    "issuance_date": ["ISSUEDATE", "ISSUE_DATE", "DATEISSUED"],
    "filing_date": ["APPLICATIONDATE", "APPLICATION_DATE", "DATEFILED"],
    "status": ["STATUS", "PERMITSTATUS"],
    "address_street": ["SITE_ADDRESS", "SITEADDRESS", "PROPERTYADDRESS", "ADDRESS"],
    "zipcode": ["ZIPCODE", "ZIP", "POSTALCODE"],
    "bbl": ["PARCELNUMBER", "PARCEL_NUMBER", "APN"],
}
