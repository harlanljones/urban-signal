"""Per-city field maps for Bowling Green / Warren County, KY (US-300 leaf).

Bowling Green (city of Bowling Green, Warren County seat) registers ONE feed
on the city ArcGIS Server ``webgis.bgky.org`` ``CCPC/CCPC_Building_Permits_2010``
service: PERMITS (``FeatureServer/5`` "Building Permits 2010+", ArcGIS Server
11.5, city-owned). The other three candidate families were probed and are
**deliberately NOT registered**: COMPLAINTS_311 (``Code_Cases/13`` froze
2023-01-31; ``CCPC_Compliance_Inspections/2`` is EPSC/construction
compliance — a different family), SLA (no license register in the
``978-dataset`` org), and DEEDS (``WARCO/Parcel_Reference`` is a parcel
snapshot — no fresh sales).

The permits layer is genuinely **spatial**: a native-point layer in KY-North
State Plane 102680 (WGS84 served via ``outSR=4326``), so the ArcGIS client
lifts ``latitude``/``longitude`` off the feature geometry and ``needs_geocode``
is declared only **defensively** (a has-coordinate feed must never attempt a
geocode fallback that could poison a legit native coordinate; native points
normally ride straight through). ``non_spatial`` is therefore NOT set — unlike
Lynchburg's tabular layers, this layer carries real geometry on every row.

The watermark is the date-typed editor-tracking column ``created_date``
(ArcGIS-11.5 tracked field; flattened to ISO by the client). Host limitation
(verified live): ``webgis.bgky.org`` requires **ANSI date literals** — a bare
ISO comparison (``created_date >= '2026-08-20T00:00:00+00:00'``) returns ArcGIS
error 400, whereas ``created_date >= DATE '2026-08-20 00:00:00'`` verifies.
This is a **host quirk**, not a schema property: the watermark column is a
true date, so no ADR-0005 text-watermark declaration is needed. The spine
delta notes the ANSI-literal ordering requirement; ``watermarks.py`` is not
edited here.

Field shape: the row is split across ``St_Number`` / ``St_Name`` with no
single street line and no neighborhood/parcel key. Because native geometry
carries the coordinate, no address composition hook is registered — the
``address_street`` candidate is deliberately absent so the producer never
emits a number-only half-address from St_Number via ``first_mapped``.

This module is a leaf. The shared ``field_maps.py`` dispatch stays untouched;
the spine pins ``BOWLING_GREEN_PERMITS_FIELD_MAP`` onto the matching FeedType.
"""

from typing import Dict, List

GEOCODE_CONTEXT: str = "Bowling Green, KY"

# PERMITS — Building Permits 2010+ /FeatureServer/5. PermitNum is the
# human-readable id ("2026-1314"); OBJECTID is the OID key. PermitUse is the
# type vocabulary (APARTMENT / FENCE / STORAGE SHED / …) — there is no
# separate application/subtype column, so filing_date and job_type-specific
# subdivision are not declared. created_date is the editor-tracking watermark
# (date-typed, ISO after client flatten) and doubles as the issuance anchor.
# PermitCost is the declared cost. SPID is a site-plan designation, not a
# parcel id; no parcel/bbl key exists, so bbl is left unmapped.
BOWLING_GREEN_PERMITS_FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["PermitNum", "OBJECTID"],
    "job_type": ["PermitUse"],
    "issuance_date": ["created_date"],
    "cost": ["PermitCost"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "permits": BOWLING_GREEN_PERMITS_FIELD_MAP,
}

__all__ = [
    "BOWLING_GREEN_PERMITS_FIELD_MAP",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
]
