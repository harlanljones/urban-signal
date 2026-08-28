"""Per-city field maps for Spartanburg County, SC (US-301 leaf rebuild).

Spartanburg County publishes its EnerGov permit + license cases through ONE
shared on-prem ArcGIS FeatureServer layer — ``EnerGov/EnerGov_Spatial_Collections/FeatureServer/5``
("History Points") on ``maps.spartanburgcounty.org`` (HTTP site root
``/server/rest/services`` — the naive ``/arcgis/rest/services`` prefix 404s).
The two feeds are separated ONLY by a load-bearing ``where`` module filter:

* PERMITS — ``ModuleName='PermitManagement'``
* SLA — ``ModuleName IN ('BusinessLicenseEntity','BusinessLicenseManagement')``

The layer is a native POINT layer (esriGeometryPoint, outSR=4326 on query), so
the client lifts geometry to ``latitude``/``longitude`` and ``needs_geocode``
stays ``False``. There are NO address columns: every row carries
``SpatialType='Address'`` (a server-side geocode flag) plus a ``SpatialID``
GUID, so the combined street address is deliberately unmapped — coordinates
are the native source and ADR-0004 has nothing to geocode.

Columns the layer actually publishes (all 12, verified live 2026-08-28):
``OBJECTID``, ``ModuleName``, ``CaseID`` (GUID), ``CaseNumber``, ``CaseType``,
``WorkClass``, ``ApplicationDate`` (esriFieldTypeDate, the watermark),
``ProjectID``, ``ProjectName``, ``GISHistoryQueueID``, ``SpatialType``,
``SpatialID``.

Notable shapes that shape the maps:

* ``CaseNumber`` is the human label. For ``PermitManagement`` it is a real
  permit number (``BLDRESDNTL-0826-22014``) and unique. For
  ``BusinessLicenseEntity`` it is the business NAME (``Brat &amp; Curry Co``,
  byte-verbatim HTML-escaped); for ``BusinessLicenseManagement`` a real case
  number (``ZPANNUFOOD-000521-2026``). So the SLA id chain falls back to the
  ``CaseID`` GUID (then ``OBJECTID``) since CaseNumber is not unique across
  the union. The producer does NOT HTML-unescape, so ``license_id``/``dba``
  carry ``&amp;`` verbatim for Entity rows.
* ``WorkClass`` is the most specific sub-type ("New Single Family Residence",
  "Residential Demolition", "Alteration, Remodel, Repair"); ``CaseType`` is the
  permit class ("Building (Residential)", "Demolition (Residential)"). Mapping
  ``job_type`` as ``["WorkClass","CaseType"]`` gives the producer's classifier
  DM/A2 signals; ``New Single Family Residence`` does not match the producer's
  NB keyword set ("NEW CONSTRUCTION"/"NEW BUILDING") — a known classifier gap,
  documented, not worked around here.
* ``ApplicationDate`` is the only date column (both filing and issuance). The
  permits map routes it to ``issuance_date`` so the parsed event carries a real
  date and the scheduler watermark advances.

This is a leaf. The shared ``field_maps.py`` dispatch stays untouched; the
spine pins the per-feed maps onto the matching ``FeedType`` via
``SPARTANBURG_FIELD_MAP``.
"""

from typing import Dict, List

GEOCODE_CONTEXT: str = "Spartanburg, SC"

# PERMITS — EnerGov PermitManagement on /5 (native point).
# CaseNumber is the permit number. WorkClass is the specific sub-type; CaseType
# the class. ApplicationDate is the watermark (same-day live 2026-08-28:
# latest 16:08:53Z). No address / parcel / status / cost column exists, so
# address_street, bbl, cost, filing_date, and status are deliberately unmapped
# (status falls back to the producer's "ISSUED" default).
PERMITS_FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["CaseNumber", "OBJECTID"],
    "job_type": ["WorkClass", "CaseType"],
    "issuance_date": ["ApplicationDate"],
}

# SLA — EnerGov BusinessLicenseEntity + BusinessLicenseManagement on /5
# (native point). license_id prefers CaseNumber (a real case number for
# Management rows, the business name for Entity rows) then the CaseID GUID then
# OBJECTID. ProjectName is empty layer-wide, so dba/premises_name fall through
# to CaseNumber. ApplicationDate is the watermark (union newest
# 2026-07-08T11:55:00Z). license_type is CaseType ("Limited Liability Company",
# "Mobile Food Service Vendor Annual Zoning Permit"). No address / status /
# expiration column exists (status defaults to the producer's ACTIVE).
SLA_FIELD_MAP: Dict[str, List[str]] = {
    "license_id": ["CaseNumber", "CaseID", "OBJECTID"],
    "dba": ["ProjectName", "CaseNumber"],
    "premises_name": ["ProjectName", "CaseNumber"],
    "license_type": ["CaseType"],
    "effective_date": ["ApplicationDate"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

# Spine alias (facts: "field_map SPARTANBURG_FIELD_MAP").
SPARTANBURG_FIELD_MAP = FIELD_MAP

__all__ = [
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
    "SPARTANBURG_FIELD_MAP",
]
