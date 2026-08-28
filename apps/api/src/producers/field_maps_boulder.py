"""Per-city field maps for Boulder, CO (US-245).

Boulder is a TWO-FEED partial metro: PERMITS (``Construction_Permits``
FeatureServer/0 on the city's AGOL org, services.arcgis.com/ePKBjXrBZ2vEEgWd)
and SLA (``RentalHousingLicenses`` MapServer/0 on the city ArcGIS Server at
maps.bouldercolorado.gov). 311 and DEEDS are Tier 3: 311 aggregates (Inquire
Boulder CS Portal Requests by Topic) have no addressable geometry; deeds have
no fresh verifiable bulk feed (the county's Recent Sales AGOL service maxes at
2025-03-28 with null-date rows, and PropSearch_SALES has future-date sentinels
and non-queryable date ranges).

Coordinate contract (pinned by tests):

* PERMITS — the ``Construction_Permits`` layer is a **Table** (non-spatial):
  no geometry is returned. Coordinates are address-only via the ADR-0004
  geocode supplement on ``OriginalAddress`` + ``OriginalCity``/``OriginalState``/
  ``OriginalZip``, with context ``"Boulder, CO"``. All dates are ANSI string
  ``YYYY-MM-DD`` (``IssuedDate``, ``AppliedDate``, ``CompletedDate``) — not
  esriFieldTypeDate, so the client does NOT ISO-normalize them; the producer's
  ``_parse_datetime`` handles the ``%Y-%m-%d`` format.
* SLA — the ``RentalHousingLicenses`` layer is a **MapServer** with polygon
  parcel geometry at native WKID 2876 (NAD83 Colorado North state-plane feet).
  Every query requests ``outSR=4326`` and ``ArcGISClient._flatten_feature``
  reduces the polygon rings to WGS84 (lng, lat) via a shapely centroid.
  ``APPLIEDDATE``/``ISSUEDDATE``/``EXPIRATIONDATE`` are esriFieldTypeDate —
  epoch-ms converted to ISO on flatten. ``ISSUEDDATE`` may carry future-dated
  license-period effective dates (e.g. 2027-04-20 for a 2027-2028 period);
  ``APPLIEDDATE`` is the clean watermark.
"""


# Layer 0 of the Construction_Permits Table (AGOL FeatureServer/0).
# Non-spatial: no geometry, address-only sediments. All dates are ANSI strings.
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["PermitNum", "PermitID", "ObjectId"],
    "issuance_date": ["IssuedDate"],
    "filing_date": ["AppliedDate"],
    "status": ["StatusCurrent"],
    "job_type": ["PermitType", "PermitWorkType"],
    "cost": ["EstProjectCost"],
    "address_street": ["OriginalAddress"],
    "zipcode": ["OriginalZip"],
    "borough": ["OriginalCity"],
}

# MapServer/0 of the RentalHousingLicenses layer (gis.bouldercolorado.gov
# ags_svr1/plan/RentalHousingLicenses/MapServer/0). Polygon parcel geometry;
# coordinates come from the outSR=4326 centroid reduction, never from the
# geocoder. APPLIEDDATE is the effective watermark; ISSUEDDATE may be
# future-dated (license-period effective dates).
SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["LICENSENUMBER"],
    "dba": ["COMPLEXNAME", "PROFESSIONALLICENSEHOLDERNAME"],
    "premises_name": ["COMPLEXNAME"],
    "license_type": ["RENTALTYPE"],
    "status": ["LICENSESTATUS"],
    "effective_date": ["APPLIEDDATE"],
    "expiration_date": ["EXPIRATIONDATE"],
    "address_street": ["MAINADDRESS"],
    "borough": ["SUBCOMMUNITY"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Boulder, CO"

__all__ = [
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]