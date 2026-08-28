"""Per-city field-mapping support for Anchorage, AK (US-330).

The Municipality of Anchorage publishes its assessor's property file — the
``PropertyInformation_Hosted`` FeatureServer layer 0 on
``services2.arcgis.com/Ce3DhLRthdwbHlfF`` — as a **last-deed-per-parcel
snapshot**: one row per parcel carrying ``Deed_Date``/``Deed_Book``/
``Deed_Page`` for the most recent recording, polygon geometry, and no
sale-price/consideration column.

DEEDS mappings (the metro's only feed; permits/311/SLA are Tier 3 and stay
unregistered per ``docs/research/probe-anchorage.md``):

* ``doc_id`` — ``Parcel_ID`` is the assessor's stable key (+ ``GIS_ParcelNum11``
  and the ArcGIS OID as fallbacks). One doc_id per parcel, matching the
  snapshot grain.
* ``recorded_date`` — ``Deed_Date`` is the watermark; the ArcGIS client
  converts the epoch-ms value to an ISO 8601 UTC string before parsing.
* ``borough`` — ``GIS_Site_City`` is the site city on the wire ("Anchorage",
  "Eagle River", "Chugiak", "Girdwood"), a meaningful source-neighborhood
  passthrough; ``Tax_District`` sits behind it.
* ``party2_grantee`` — ``Owner_Name`` is the CURRENT owner, i.e. the GRANTEE
  of the last recorded deed (snapshot grain). Deliberately mapped to the
  grantee, not the grantor — differs from Durham's owner→grantor precedent
  because a last-deed-per-parcel owner is by definition the buyer side.
  ``party1_grantor`` (the seller) does not exist on this feed and stays
  unmapped.
* ``bbl`` — ``Parcel_ID`` (+ ``GIS_ParcelNum11``) for parcel-style joins.

Deliberately unmapped: ``document_amount`` (no sale-price/consideration
column exists; assessed values must not masquerade as deed amounts — parses
to 0.0 by design, NOLA sold-properties precedent) and ``doc_type`` (no
deed-type column; the producer's generic chain picks up ``Property_Type``,
e.g. "RESIDENTIAL").

Schemas verified live 2026-08-28 against the layer's ``?f=pjson`` metadata
(78 attribute fields; ``Deed_Date`` and ``PUBDATE`` are the only
``esriFieldTypeDate`` columns).
"""

from typing import Dict, List

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "deeds": {
        "doc_id": ["Parcel_ID", "GIS_ParcelNum11", "OBJECTID", "id"],
        "recorded_date": ["Deed_Date"],
        "borough": ["GIS_Site_City", "Tax_District"],
        "party2_grantee": ["Owner_Name"],
        "bbl": ["Parcel_ID", "GIS_ParcelNum11"],
    },
}
