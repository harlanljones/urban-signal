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
* ``address_street`` — ``Parcel_Address`` is the layer's composed site
  address ("2101 W 47TH AVE"). The five ``GIS_Site_Street_*`` parts carry the
  same information split across number/pre/name/suf/type, which
  ``first_mapped`` cannot concatenate — mapping a 5-candidate list there
  would yield a bare street number, so the composed column is the only
  correct candidate.
* ``zipcode`` — ``GIS_Site_Zipcode``. Declarative: the deeds row parser
  reads no zip column today, but the map pins the feed's address surface
  (probe payload contract) and any future address consumer resolves it.

Deliberately unmapped: ``document_amount`` (no sale-price/consideration
column exists; assessed values must not masquerade as deed amounts — parses
to 0.0 by design, NOLA sold-properties precedent) and ``doc_type`` (no
deed-type column; the producer's generic chain picks up ``Property_Type``,
e.g. "RESIDENTIAL").

Schemas verified live 2026-08-28 against the layer's ``?f=pjson`` metadata
(84 attribute fields; ``Deed_Date`` and ``PUBDATE`` are the only
``esriFieldTypeDate`` columns) and against the newest non-future rows
re-captured byte-verbatim.
"""

from typing import Dict, List

DEEDS_FIELD_MAP: Dict[str, List[str]] = {
    "doc_id": ["Parcel_ID", "GIS_ParcelNum11", "OBJECTID", "id"],
    "recorded_date": ["Deed_Date"],
    "borough": ["GIS_Site_City", "Tax_District"],
    "party2_grantee": ["Owner_Name"],
    "bbl": ["Parcel_ID", "GIS_ParcelNum11"],
    "address_street": ["Parcel_Address"],
    "zipcode": ["GIS_Site_Zipcode"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "deeds": DEEDS_FIELD_MAP,
}

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
]
