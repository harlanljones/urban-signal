"""Anchor-institution vocabularies and CCD status mapping (US-375/US-376).

The schema decision for the anchor-institution event family now lives in its
canonical spine home, ``src/schemas/models.py`` (``AnchorInstitutionEvent``,
mirrored on ``schemas/avro/anchor_institution_event.avsc``). This module keeps
the leaf-owned *decision data*: the vocabularies, the CCD
status-to-event-type mapping, and the source/category constants.

US-376 (Head Start) reuses the shape unchanged: ``category="head_start"`` with
``capacity=<funded_slots>`` and ``source="head_start"``.
"""

from __future__ import annotations

from src.schemas.models import AnchorInstitutionEvent

__all__ = ["AnchorInstitutionEvent", "ANCHOR_TOPIC", "ANCHOR_CATEGORIES", "ANCHOR_EVENT_TYPES",
           "CCD_STATUS_EVENT_TYPE", "CCD_STATUS_OPEN", "CCD_STATUS_BOUNDARY",
           "CCD_RECON_YES", "CCD_CHARTER_YES"]

ANCHOR_TOPIC = "raw.anchor.institutions"
ANCHOR_CATEGORIES = ("school", "charter", "head_start")
ANCHOR_EVENT_TYPES = ("opened", "closed", "reopened")

# CCD UPDATED_STATUS_TEXT -> AnchorInstitutionEvent.event_type. 'Open' never
# becomes an event (it is the active inventory); 'Changed Boundary/Agency'
# rows are boundary churn, not real openings, and are dropped entirely.
CCD_STATUS_EVENT_TYPE = {
    "New": "opened",
    "Added": "opened",
    "Future": "opened",
    "Reopened": "reopened",
    "Closed": "closed",
    "Inactive": "closed",
}
CCD_STATUS_OPEN = "Open"
CCD_STATUS_BOUNDARY = "Changed Boundary/Agency"
CCD_RECON_YES = "Yes"
CCD_CHARTER_YES = "Yes"