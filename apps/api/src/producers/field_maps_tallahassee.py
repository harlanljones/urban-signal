"""Per-city field maps for Tallahassee, FL / Leon County (US-303 leaf).

Tallahassee registers three native-point ArcGIS layers on the joint
City/County ArcGIS Server 10.81 at ``intervector.leoncountyfl.gov`` (web-
adaptor base ``/intervector/rest/services/MapServices/``):

* PERMITS — ``TLC_OverlayPermitsActive_D_WM/MapServer/0`` (active building
  permits by type). Watermark ``AppliedDate`` (date-typed). The overlay is
  a live, fresh view of active permits; ``needs_geocode=False``.
* COMPLAINTS_311 — ``LCPW_InforServiceRequest_D_WM/MapServer/1`` (All Service
  Requests, Infor/PublicWorks CRM). Watermark ``CALLDTTM`` (date-typed).
  ``needs_geocode=False``; the spec carries
  ``where="CALLDTTM <= CURRENT_TIMESTAMP"`` to exclude the future-dated
  sentinel + scheduled rows.
* DEEDS — ``LCPA_Last3YearsSales_D_WM/MapServer/0`` (rolling 3-yr sales,
  native parcel-centroid point). Watermark ``SALES_SALEDT`` (date-typed).
  ``needs_geocode=False`` and NO ``parcel_join`` (the layer already serves
  parcel-centroid points). SLA is absent — no BTR dataset in the org.

Coordinate policy (critical): all three layers are native points and publish
NO ``objectIdField``. The ArcGIS client requests ``outSR=4326`` and lifts the
geometry to WGS84 ``latitude``/``longitude``. The attribute coordinate
columns are projected and must NEVER be mapped:
* permits ``Latitude``/``Longitude`` = Web Mercator meters;
* 311 ``GPSX``/``GPSY`` = FL State Plane North feet.
No latitude/longitude candidate is declared on any map here.

This module is a leaf. The shared ``field_maps.py`` dispatch stays untouched;
the spine pins each map onto the matching ``FeedType``.
"""

from typing import Dict, List

GEOCODE_CONTEXT: str = "Tallahassee, FL"

# PERMITS — TLC_OverlayPermitsActive_D_WM /MapServer/0.
# PermitNum is the active-permit id; PermitTypeMapped/WorkClassMapped drive
# the producer's job_type classification ("New" -> NB, "Swimming Pool" -> OT).
# IssuedDate is date-typed; OriginalAddress1 is street-only (no geocode —
# geometry supplies coordinates). PIN is the parcel id (bbl). Jurisdiction
# distinguishes City of Tallahassee vs Leon County. EstProjectCost is the
# declared cost. StatusCurrent is the live status (PENDING/INVOICED/PLANS
# REVIEW/…). Latitude/Longitude attributes are Web Mercator meters — no
# coordinate candidates declared.
PERMITS_FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["PermitNum", "OBJECTID"],
    "job_type": ["PermitTypeMapped", "WorkClassMapped", "WorkClass"],
    "issuance_date": ["IssuedDate"],
    "address_street": ["OriginalAddress1"],
    "bbl": ["PIN"],
    "borough": ["Jurisdiction", "PermitClassMapped"],
    "cost": ["EstProjectCost"],
    "status": ["StatusCurrent", "StatusCurrentMapped"],
}

# COMPLAINTS_311 — LCPW_InforServiceRequest_D_WM /MapServer/1.
# SERVNO is the service-request id (int). PROBDESC is the descriptive problem
# type; CATNAME the coarse bucket. CALLDTTM is the watermark (date-typed);
# RESDTTM the resolve time. ADDRESS (with LOC) is the incident address.
# DISTRICT/COUNTY/CATNAME are the borough-ish labels. RESP/RESCODE carry
# status. GPSX/GPSY are FL State Plane North feet — no coordinate candidates
# declared (geometry supplies WGS84 lat/lng).
COMPLAINTS_311_FIELD_MAP: Dict[str, List[str]] = {
    "incident_id": ["SERVNO"],
    "complaint_type": ["PROBDESC", "CATNAME", "DESCRIPT"],
    "created_date": ["CALLDTTM"],
    "closed_date": ["RESDTTM"],
    "incident_address": ["ADDRESS", "LOC"],
    "borough": ["DISTRICT", "COUNTY", "CATNAME"],
    "status": ["RESP", "RESCODE"],
}

# DEEDS — LCPA_Last3YearsSales_D_WM /MapServer/0.
# SALES_SALEKEY is the per-sale integer id (unique per transfer; the
# SALES_INSTRUNO/SALES_TRANSNO id columns are NULL across the newest batch).
# SALES_PARID is the space-padded fixed-width parcel id (bbl, kept verbatim).
# SALES_PRICE (with SALES_ADJPRICE) is the consideration. SALES_SALEDT is the
# watermark (date-typed) and the recorded date. SALES_OLDOWN/OLDOWN2 =
# grantor; SALES_OWN1/OWN2 = grantee. doc_type is deliberately unmapped so the
# producer defaults to "DEED" rather than emitting a shorthand instrument
# literal (CT/WD). No address column and no coordinate candidates — the layer
# serves parcel-centroid points.
DEEDS_FIELD_MAP: Dict[str, List[str]] = {
    "doc_id": ["SALES_SALEKEY", "OBJECTID"],
    "bbl": ["SALES_PARID"],
    "document_amount": ["SALES_PRICE", "SALES_ADJPRICE"],
    "recorded_date": ["SALES_SALEDT", "SALES_RECORDDT"],
    "party1_grantor": ["SALES_OLDOWN", "SALES_OLDOWN2"],
    "party2_grantee": ["SALES_OWN1", "SALES_OWN2"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "311": COMPLAINTS_311_FIELD_MAP,
    "deeds": DEEDS_FIELD_MAP,
}

__all__ = [
    "COMPLAINTS_311_FIELD_MAP",
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
]
