"""Maricopa County Sales Affidavits field map (US-392, Phoenix DEEDS).

Maps canonical ``DeedEvent`` field names to the Maricopa County Assessor sales
affidavits columns. Probe (2026-08-28, full 912,806-row scan) verified the
pipe-delimited schema, clean deed/parcel mapping, and the data-quality caveats
the producer guard relies on.

The feed is a CSV Collection on ArcGIS Online: item `f3484c72a938497286adc4e5de7e9963`
(`https://www.arcgis.com/sharing/rest/content/items/{id}/data` — 61 MB ZIP,
`Data/Sales_Affidavits.txt` member). Delivered snapshot-style: no usable text
watermark (both date columns are lexicographically non-chronological; 134
future-DEEDDATE sentinels exist), so `ingestion_mode="snapshot"` +
cross-run id-dedup diff is the churn signal (KC-SLA/OR-CCB precedent).

Geocoding: the feed carries NO coordinates — location is `SITUSADDRESS` +
`SITUSCITY`/`SITUSZIP` text. The deeds producer resolves coordinates through
the ADR-0004 geocoder when `needs_geocode=True` and a `geocode_context` is
declared.

This module is a leaf: the shared ``field_maps.py`` dispatch is untouched.
Maps are keyed by canonical ``DeedEvent`` field names, which the
``deeds_acris_producer`` walks when parsing rows.
"""


GEOCODE_CONTEXT: str = "Maricopa County, AZ"

# Multi-parcel deeds share one DEEDNUMBER (MULTIPARCELINDICATOR="Y"), so both
# parcel and deed number feed the id — see the DEEDS id_keys in the spine.
MARICOPA_DEEDS_FIELD_MAP: dict[str, list[str]] = {
    "doc_id": ["DEEDNUMBER", "PARCELNUMBER"],
    "bbl": ["PARCELNUMBER"],
    "doc_type": ["DEEDTYPE"],
    "document_amount": ["SALEPRICE"],
    "recorded_date": ["DEEDDATE_MMDDYYYY"],
    "sale_date": ["SALEDATE_MMYYYY"],
    "address_street": ["SITUSADDRESS"],
    "borough": ["SITUSCITY"],
    "zipcode": ["SITUSZIP"],
    "party1_grantor": ["GRANTOROWNERNAME"],
    "party2_grantee": ["GRANTEEOWNERNAME"],
    "status": ["DEEDSTATUS"],
}
