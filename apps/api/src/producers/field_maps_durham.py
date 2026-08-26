"""Per-city field-mapping support for Durham, NC municipal row parsers.

Durham publishes through the City of Durham Open Data / GIS portal
(``webgis2.durhamnc.gov``) as two ArcGIS layers:

* **PERMITS** — ``PublicServices/Inspections/MapServer/12`` ("All Building
  Permits"), an ``esriGeometryPoint`` layer whose geometry is lifted to
  ``latitude``/``longitude`` by :class:`~src.producers.arcgis_client.ArcGISClient``.
  No latitude/longitude binding is needed in the map; coordinates flow from the
  client. The layer also carries its own date watermark (``ISSUE_DATE`` is the
  layer's ``timeInfo.startTimeField``).
* **DEEDS** — ``PublicServices/Property/MapServer/4`` ("Parcels"), an
  ``esriGeometryPolygon`` assessor-parcel layer. The client reduces the polygon
  to a centroid coordinate, so deeds events still carry H3 cells. The assessor
  table has no grantor/grantee split — ``party1_grantor`` best-effort maps to
  ``PROPERTY_OWNER``; ``party2_grantee`` is intentionally left unmapped (the
  producer tolerates ``None``).

This module is the per-city analog of :mod:`src.producers.field_maps`; it
exports one nested ``FIELD_MAP`` keyed by feed, consumed by the shared permits
and deeds producers via the registry's ``extra["field_map"]`` entry. Kept as a
dedicated leaf file so the spine ``field_maps.py`` dispatch stays untouched.

Schemas verified live 2026-08-26 against the ArcGIS REST ``?f=pjson`` metadata.
"""

from typing import Dict, List

# Canonical event field -> candidate row keys, per feed. Mirrors the spellings
# discovered on the live Durham ArcGIS layers. Values follow the same
# falsy-falls-through semantics as the shared chains.
FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "permits": {
        # Permit number is the human id; OBJECTID is the ArcGIS OID fallback.
        "job_id": ["PermitNum", "OBJECTID", "id"],
        # Total building cost is the closest single permit-value column.
        "cost": ["BLD_Cost", "ESTIMATED_ELEC_COST", "ESTIMATED_MECH_COST", "ESTIMATED_OTH_COST"],
        # Building activity / project type drive job-type classification.
        "job_type": ["BLDB_ACTIVITY", "BLDB_ACTIVITY_1", "PROJECT_TYPE", "TYPE"],
        # Layer time watermark; esriFieldTypeDate (epoch-ms -> ISO by client).
        "issuance_date": ["ISSUE_DATE"],
        "status": ["PmtStatus"],
        # No clean street-address column exists; PROJECT_NAME is the best-effort
        # descriptor. Coordinates come from the Point geometry, so an address is
        # not required to geolocate the event.
        "address_street": ["PROJECT_NAME", "DESCRIPTION"],
        # Parcel identifiers for block/lot-style joins if ever needed.
        "bbl": ["PIN", "PARCEL_ID", "PID"],
    },
    "deeds": {
        # Real-estate id (REID) is the stable assessor key; PIN/PARCEL_PK and the
        # layer OID (OBJECTID_1) are fallbacks.
        "doc_id": ["REID", "PIN", "PARCEL_PK", "OBJECTID_1", "OBJECTID", "id"],
        # Recorded deed date is the watermark; sale dates fall back behind it.
        "recorded_date": ["DEED_DATE", "PKG_SALE_DATE", "LAND_SALE_DATE"],
        # Document amount from the recorded sale prices; total assessed value is
        # a weaker fallback.
        "document_amount": [
            "PKG_SALE_PRICE",
            "LAND_SALE_PRICE",
            "TOTAL_PROP_VALUE",
            "COST_TOTAL_VALUE",
        ],
        # Land class / parcel type describe the property kind.
        "doc_type": ["LAND_CLASS", "PARCEL_TYPE"],
        # Borough resolves from the neighborhood string; township/city behind it.
        "borough": ["NEIGHBORHOOD", "TOWNSHIP", "CITY"],
        # Assessor parcel table has no grantor/grantee split; owner is the
        # best-effort grantor column. Grantee left unmapped.
        "party1_grantor": ["PROPERTY_OWNER"],
        # Parcel identifier.
        "bbl": ["PIN", "REID", "PARCEL_PK"],
    },
}
