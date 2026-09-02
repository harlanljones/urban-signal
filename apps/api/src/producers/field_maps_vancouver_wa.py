"""Per-city field maps for Vancouver, WA (US-233; SLA super-feed US-426),
imported by the shared parsers.

Vancouver, WA: PERMITS from the ``Permits_and_Code_Enforcement_Data_(public_view)``
FeatureServer/0 ("Permit Data") on the city's AGOL org
(``CityOfVancouverGISAdmin``, ``services.arcgis.com/oNvpY90qsPDizwkN``), plus
(US-426) the WA L&I Construction Contractor registry (``m8qx-ubtq``,
``data.wa.gov``) as the metropolitan SLA super-feed. GIS.cityofvancouver.us
(311) is token-gated and Clark County recorder deeds are a web app — both
stay Tier 3.

Coordinate contract (pinned by tests):

* PERMITS — coordinates come from **native point geometry** requested with
  ``outSR=4326``; ``ArcGISClient._flatten_feature`` lifts them to lowercase
  ``latitude``/``longitude`` keys. The ``Y``/``X`` *attributes* are **WA
  State Plane South feet** (values ≈ 1.1e5 / 1.08e6) and are deliberately
  NOT candidates — mapping them would emit projected feet as degrees.
* SLA — the WA L&I registry is address-only (``address1`` is the mailing
  address; the registry ships no jobsite columns), so rows geocode via the
  ADR-0004 supplement with context "Vancouver, WA" (``needs_geocode=True``).
  ``licenseeffectivedate`` is the watermark.
* ``csm_issued_date`` is esriFieldTypeDate (epoch-ms → ISO) and is
  where-clause queryable with ISO strings. Two future-date sentinel rows
  (2039-05-19, 2049-10-31, both Closed/ELECTRICAL) are excluded by the
  ``where`` guard ``csm_issued_date <= CURRENT_TIMESTAMP`` (Anchorage
  discipline).
* No site-zip column exists on the permits layer (``PRIM_ADDR`` is the
  address without zip) and no parcel/APN column exists, so ``zipcode`` and
  ``bbl`` stay undeclared.
* No neighborhood/district column exists on the permits layer, so no
  ``borough`` field-map candidate is declared (Omaha discipline): division
  resolution comes from coordinates at ingest, and ``source_neighborhood``
  passes through as None.

PII is dropped at the map: no owner/contractor columns exist on the permits
layer.
"""


PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["CSM_CASENO", "sn", "OBJECTID"],
    "issuance_date": ["csm_issued_date"],
    "status": ["CSM_STATUS"],
    "job_type": ["worktype", "cst_description"],
    "address_street": ["PRIM_ADDR"],
    "proposed_units": ["CSM_NO_UNITS"],
}

SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["contractorlicensenumber"],
    "license_type": ["license_type_ns"],
    "effective_date": ["licenseeffectivedate"],
    "expiration_date": ["licenseexpirationdate"],
    "premises_name": ["businessname"],
    "dba": ["businessname"],
    "address_street": ["address1"],
    "status": ["contractorlicensestatus"],
    "borough": ["city"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Vancouver, WA"

__all__ = [
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]