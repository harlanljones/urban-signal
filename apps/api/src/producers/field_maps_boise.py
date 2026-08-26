"""Per-city field-mapping support for Boise's municipal row parsers.

Boise publishes through the City of Boise Open Data Hub as an ArcGIS
FeatureServer. The live layer advertises Idaho state-plane geometry
(WKID 102459), but the shared ArcGIS client requests ``outSR=4326`` and
normalizes the returned point into ``latitude``/``longitude``. The address
fields remain the ADR-0004 fallback when a row has no usable geometry.

This module is the per-city analog of :mod:`src.producers.field_maps`; it
exports one `FIELD_MAP` consumed by the shared permits producer via the
registry's `extra["field_map"]` entry. Kept as a dedicated leaf file so the
spine `field_maps.py` dispatch stays untouched.
"""

from typing import Dict, List

# Residential-only, thin PERMITS feed field spellings for Boise. Geometry is
# supplied by ArcGISClient after its WGS84 request; the aliases below retain
# compatibility with direct rows and state-plane fallbacks.
FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["RecordID", "RECORDID", "OBJECTID", "PERMITNUMBER", "PERMIT_NUMBER", "PERMITNO"],
    "latitude": ["SHAPE__Y", "Y"],
    "longitude": ["SHAPE__X", "X"],
    "cost": ["ESTIMATEDCOST", "ESTIMATED_COST", "PROJECTCOST", "TOTALCOST"],
    "job_type": ["ResidentialType", "ResidentialSubtype", "PERMITTYPE", "PERMIT_TYPE", "WORKDESCRIPTION"],
    "issuance_date": ["IssuedDate", "ISSUEDATE", "ISSUE_DATE", "DATEISSUED"],
    "filing_date": ["ReceiveDate", "APPLICATIONDATE", "APPLICATION_DATE", "DATEFILED"],
    "status": ["PermitStatus", "Status", "STATUS", "PERMITSTATUS"],
    "address_street": ["PropertyAddress", "Match_addr", "SITE_ADDRESS", "SITEADDRESS", "PROPERTYADDRESS", "ADDRESS"],
    "zipcode": ["ZIPCODE", "ZIP", "POSTALCODE"],
    "bbl": ["PARCELNUMBER", "PARCEL_NUMBER", "APN"],
}
