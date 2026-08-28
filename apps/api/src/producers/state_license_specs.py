"""DatasetSpec-shaped plain dicts for the US-372 state license registries.

LEAF data — NOT registered anywhere. Field names mirror the ``DatasetSpec``
dataclass in ``src/spatial/city_registry.py`` exactly (``DatasetSpec(**spec)``
constructs from these dicts) so the spine can copy them mechanically during
the interlock hold; the per-city placement is documented in
``.streams/us372-state-licenses.md`` ("Spine delta").

Three of the nine registries are ALREADY registered live: TABC active under
Austin (``settings.socrata_austin_tabc_endpoint``), WA LCB under Seattle
(``settings.socrata_seattle_licenses_endpoint``), OLCC under Portland
(``settings.socrata_portland_olcc_applications_endpoint``). The corresponding
specs here show the namespaced-mapping variant for those feeds — adopting
them changes license_type values and is the spine's call.

license_type NAMESPACING rides the endpoint string: SoQL
``$select=*, '<ns>:' || <type_col> as license_type_ns`` — httpx merges the
client's pagination params with the URL's ``$select`` (verified live through
``SocrataClient.paginate``), so no producer machinery is needed. The
staleness probe and scheduler stay compatible: ``*`` keeps every original
column, including each watermark column.

Snapshot-mode registries (OR CCB, CO liquor, MO new liquor) carry
``watermark_col=""``: their only date columns are MM/DD/YYYY text or
expiry-style values that Socrata cannot server-side order chronologically
(to_fixed_timestamp / substr both 400 on these domains), so a text watermark
would false-alarm the staleness probe with a lexicographic December max.
Snapshot full pulls whose cross-run id-dedup diff is the churn signal follow
the KC SLA precedent (US-134); freshness rides Socrata ``rowsUpdatedAt``,
which the probe reads for every socrata feed.
"""

from src.config import settings

from src.producers.field_maps_state_licenses import (
    CO_APPROVED_FIELD_MAP,
    CO_LIQUOR_FIELD_MAP,
    MO_NEW_FIELD_MAP,
    OR_CCB_FIELD_MAP,
    OR_OLCC_FIELD_MAP,
    TABC_ACTIVE_FIELD_MAP,
    TABC_PENDING_FIELD_MAP,
    WA_LCB_FIELD_MAP,
    WA_LI_FIELD_MAP,
)

TABC_ACTIVE_ENDPOINT = (
    "https://data.texas.gov/resource/7hf9-qc9f.json"
    "?$select=*, 'tabc:' || license_type as license_type_ns"
)
TABC_PENDING_ENDPOINT = (
    "https://data.texas.gov/resource/mxm5-tdpj.json"
    "?$select=*, 'tabc:' || license_type as license_type_ns"
)
WA_LI_ENDPOINT = (
    "https://data.wa.gov/resource/m8qx-ubtq.json"
    "?$select=*, 'wa_li:' || contractorlicensetypecodedesc as license_type_ns"
)
WA_LCB_ENDPOINT = (
    "https://data.wa.gov/resource/vgcw-qfjm.json"
    "?$select=*, 'wa_lcb:' || coalesce(privdesc01, l_a_type) as license_type_ns"
)
OR_CCB_ENDPOINT = (
    "https://data.oregon.gov/resource/g77e-6bhs.json"
    "?$select=*, 'or_ccb:' || license_type as license_type_ns"
)
OR_OLCC_ENDPOINT = (
    "https://data.oregon.gov/resource/qad4-bnxp.json"
    "?$select=*, 'olcc:' || license_type as license_type_ns"
)
CO_LIQUOR_ENDPOINT = (
    "https://data.colorado.gov/resource/ier5-5ms2.json"
    "?$select=*, 'co_liquor:' || license_type as license_type_ns"
)
CO_APPROVED_ENDPOINT = (
    "https://data.colorado.gov/resource/htyp-tqzh.json"
    "?$select=*, 'co_approved:' || license_type as license_type_ns"
)
MO_NEW_ENDPOINT = (
    "https://data.mo.gov/resource/dymb-xy5c.json"
    "?$select=*, 'mo_liquor:' || license_type as license_type_ns, "
    "trim(street_number || ' ' || street) as street_address_ns"
)


def tabc_active_spec(county: str) -> dict:
    """TABC active licenses for one county slice (Travis/Dallas/Tarrant/El Paso)."""
    return {
        "endpoint": TABC_ACTIVE_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "status_change_date",
        "id_keys": ["license_id", "master_file_id"],
        "topic": settings.topic_sla,
        "interval_seconds": 3600.0,
        "producer_key": "sla",
        "expected_cadence_days": 1,
        "ingestion_mode": "incremental",
        "where": f"county = '{county}'",
        "needs_geocode": True,
        "geocode_context": "TX",
        "order_by": "status_change_date DESC",
        "field_map": TABC_ACTIVE_FIELD_MAP,
    }


def tabc_pending_spec(city: str) -> dict:
    """TABC pending original applications for one city slice (leading indicator)."""
    return {
        "endpoint": TABC_PENDING_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "submission_date",
        "id_keys": ["applicationid", "primary_license_id"],
        "topic": settings.topic_sla,
        "interval_seconds": 3600.0,
        "producer_key": "sla",
        "expected_cadence_days": 1,
        "ingestion_mode": "incremental",
        "where": f"city = '{city}'",
        "needs_geocode": True,
        "geocode_context": "TX",
        "order_by": "submission_date DESC",
        "field_map": TABC_PENDING_FIELD_MAP,
    }


def wa_li_spec(city: str = "SEATTLE") -> dict:
    """WA L&I contractor licenses for one city slice.

    ``address1`` is the mailing address (no jobsite columns exist on the
    source), so geocoded coordinates carry accepted noise.
    """
    return {
        "endpoint": WA_LI_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "licenseeffectivedate",
        "id_keys": ["contractorlicensenumber", "ubi"],
        "topic": settings.topic_sla,
        "interval_seconds": 3600.0,
        "producer_key": "sla",
        "expected_cadence_days": 1,
        "ingestion_mode": "incremental",
        "where": f"city = '{city}'",
        "needs_geocode": True,
        "geocode_context": "WA",
        "order_by": "licenseeffectivedate DESC",
        "field_map": WA_LI_FIELD_MAP,
    }


def mo_new_spec(
    city: str = "KANSAS CITY", geocode_context: str = "Kansas City, MO"
) -> dict:
    """MO new liquor licenses for one city slice (rolling ~3-week window)."""
    return {
        "endpoint": MO_NEW_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "",
        "id_keys": ["license_number", "licensee"],
        "topic": settings.topic_sla,
        "interval_seconds": 3600.0,
        "producer_key": "sla",
        "expected_cadence_days": 1,
        "ingestion_mode": "snapshot",
        "where": f"city = '{city}'",
        "needs_geocode": True,
        "geocode_context": geocode_context,
        "field_map": MO_NEW_FIELD_MAP,
    }


# WA LCB is already registered live under Seattle, unfiltered, watermarking
# ``applicationdate``. This spec shows the city-sliced variant with the
# fresher ``la_posted_date`` watermark (ISO text, 0 nulls verified) —
# adopting it narrows the live feed's scope, so it is the spine's call.
WA_LCB_SPEC: dict = {
    "endpoint": WA_LCB_ENDPOINT,
    "platform": "socrata",
    "watermark_col": "la_posted_date",
    "id_keys": ["license", "ubi"],
    "topic": settings.topic_sla,
    "interval_seconds": 3600.0,
    "producer_key": "sla",
    "expected_cadence_days": 1,
    "ingestion_mode": "incremental",
    "where": "cityname = 'SEATTLE'",
    "needs_geocode": False,
    "order_by": "la_posted_date DESC",
    "field_map": WA_LCB_FIELD_MAP,
}

# OR CCB dates are MM/DD/YYYY text with no server-side conversion; snapshot
# ingestion per the KC SLA precedent (module docstring).
OR_CCB_SPEC: dict = {
    "endpoint": OR_CCB_ENDPOINT,
    "platform": "socrata",
    "watermark_col": "",
    "id_keys": ["license_number", "related_key"],
    "topic": settings.topic_sla,
    "interval_seconds": 21600.0,
    "producer_key": "sla",
    "expected_cadence_days": 1,
    "ingestion_mode": "snapshot",
    "where": "city = 'PORTLAND' AND state = 'OR'",
    "needs_geocode": True,
    "geocode_context": "Portland, OR",
    "field_map": OR_CCB_FIELD_MAP,
}

# Mirrors the live Portland registration (state-wide application flow,
# address strings embed the city); adds the namespaced license_type.
OR_OLCC_SPEC: dict = {
    "endpoint": OR_OLCC_ENDPOINT,
    "platform": "socrata",
    "watermark_col": "date_received",
    "id_keys": ["trade_name", "address"],
    "topic": settings.topic_sla,
    "interval_seconds": 3600.0,
    "producer_key": "sla",
    "expected_cadence_days": 1,
    "ingestion_mode": "incremental",
    "needs_geocode": True,
    "order_by": "date_received DESC",
    "field_map": OR_OLCC_FIELD_MAP,
}

# Monthly full registry (point geocoded); staleness rides rowsUpdatedAt.
CO_LIQUOR_SPEC: dict = {
    "endpoint": CO_LIQUOR_ENDPOINT,
    "platform": "socrata",
    "watermark_col": "",
    "id_keys": ["license_number", "licensee_name"],
    "topic": settings.topic_sla,
    "interval_seconds": 21600.0,
    "producer_key": "sla",
    "expected_cadence_days": 31,
    "ingestion_mode": "snapshot",
    "where": "city = 'Denver'",
    "needs_geocode": False,
    "field_map": CO_LIQUOR_FIELD_MAP,
}

# ~98 far-future issue_date rows (years 2048-2262) re-pass the incremental
# filter every cycle; the id-dedup cache absorbs them and the watermark
# layer's future guard keeps reported freshness honest (max real 2026-07-31).
CO_APPROVED_SPEC: dict = {
    "endpoint": CO_APPROVED_ENDPOINT,
    "platform": "socrata",
    "watermark_col": "issue_date",
    "id_keys": ["license_number", "licensee_name"],
    "topic": settings.topic_sla,
    "interval_seconds": 21600.0,
    "producer_key": "sla",
    "expected_cadence_days": 7,
    "ingestion_mode": "incremental",
    "where": "city = 'Denver'",
    "needs_geocode": False,
    "order_by": "issue_date DESC",
    "field_map": CO_APPROVED_FIELD_MAP,
}
