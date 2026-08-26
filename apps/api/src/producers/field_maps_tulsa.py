"""Per-city field-mapping support for Tulsa's 311 row parser.

Tulsa publishes its Verint customer-care cases as an ArcGIS FeatureServer
(`CustomerCare/VerintCasesPublic/FeatureServer/0`) whose open-data view is an
approximately 30-day rolling window with no historical archive (see US-158 and
docs/research/south-central-city-candidates.md). Rows carry native point
geometry, so `latitude`/`longitude` need no override; the overrides below cover
the column spellings the shared 311 parser chain cannot reach on its own.

This module is the per-city analog of :mod:`src.producers.field_maps`; it
exports one ``FIELD_MAP`` consumed by the shared 311 producer via the registry's
``extra["field_map"]`` entry. Kept as a dedicated leaf file so the spine
``field_maps.py`` dispatch stays untouched.
"""

from typing import Dict, List

# Tulsa Verint 311 field spellings. `latitude`/`longitude` are intentionally
# absent — the feed's point geometry already resolves through the shared
# parser's native-coordinate path, so no override is needed there. The
# `incident_id` pair lists `case_id` first with `OBJECTID` as the durable
# fallback (the layer's objectIdField is `OBJECTID`).
FIELD_MAP: Dict[str, List[str]] = {
    "incident_id": ["case_id", "OBJECTID"],
    "created_date": ["case_opened"],
    "closed_date": ["case_closed"],
    "status": ["case_status"],
    "complaint_type": ["case_type", "case_reason", "case_subject"],
    "incident_address": ["case_external_ref"],
}
