'''FMCSA national dataset specs (US-373) — plain data, deliberately unregistered.

Three data.transportation.gov Socrata resources form one national
carrier-license flow riding the existing SLALicenseEvent classify→geocode→H3
path. Each dict is DatasetSpec-shaped (same keys, same semantics as
``src.spatial.city_registry.DatasetSpec``) so spine can adopt them verbatim,
but nothing here touches the city REGISTRY: these are **national** feeds.

Why they cannot attach as city datasets:

* a city holds at most one DatasetSpec per FeedType and these have no
  per-city endpoint — registering one 62 times would create 62 jobs polling
  the same URL;
* the interlock gate\'s city invariants (endpoint-per-city, per-city producer
  keys, dashboard wiring) are meaningless for a national file.

How they attach instead (spine): as a national family alongside
``NATIONAL_FEEDS`` (src/spatial/national_feeds.py), keeping this DatasetSpec
shape because the SLA paginate/parse machinery consumes DatasetSpec fields
(``where``, ``needs_geocode``, ``watermark_*``, ``field_map``) that
``NationalFeedSpec`` does not carry. ``city_id`` resolves per row after
geocoding via ``GeographyCrosswalk.city_for_point`` — rows outside registered
metros keep streaming (they are the national stock the metro slices come
from) and simply land in no metro hex. Scheduler cadences: daily census
poll, daily AuthHist, daily OOS; census additionally needs a monthly
full-snapshot pass because A→I flips happen in-place without moving
``add_date``.

Legacy FMCSA datasets ``6eyk-hxee`` and ``9mw4-x3tu`` are FROZEN ("no longer
updated" per their descriptions, last refreshed 2026-05-14) — never build on
them; they appear nowhere here by design.
'''
from src.config import settings
from src.producers.field_maps_fmcsa import FMCSA_AUTHHIST_FIELD_MAP, FMCSA_CENSUS_FIELD_MAP, FMCSA_OOS_FIELD_MAP
BASE = 'https://data.transportation.gov/resource'
FMCSA_CENSUS_SPEC: dict = {
    'endpoint': f"{BASE}/az4n-8mr2.json",
    'platform': 'socrata',
    'watermark_col': 'add_date',
    'watermark_type': 'text',
    'watermark_format': '%Y%m%d',
    'id_keys': [
        'dot_number'],
    'topic': settings.topic_sla,
    'producer_key': 'carrier',
    'interval_seconds': 86400,
    'expected_cadence_days': 1,
    'ingestion_mode': 'incremental',
    'rollover': 'monthly',
    'needs_geocode': True,
    'field_map': FMCSA_CENSUS_FIELD_MAP }
FMCSA_AUTHHIST_SPEC: dict = {
    'endpoint': f"{BASE}/yu5v-wbh6.json",
    'platform': 'socrata',
    'watermark_col': 'status_change_date',
    'watermark_type': 'text',
    'watermark_format': '%Y%m%d',
    'id_keys': [
        'usdot_number'],
    'topic': settings.topic_sla,
    'producer_key': 'carrier',
    'interval_seconds': 86400,
    'expected_cadence_days': 1,
    'ingestion_mode': 'incremental',
    'needs_geocode': True,
    'field_map': FMCSA_AUTHHIST_FIELD_MAP }
FMCSA_OOS_SPEC: dict = {
    'endpoint': f"{BASE}/p2mt-9ige.json",
    'platform': 'socrata',
    'watermark_col': 'oos_date',
    'watermark_type': 'text',
    'watermark_format': '%Y-%m-%d',
    'id_keys': [
        'dot_number'],
    'topic': settings.topic_sla,
    'producer_key': 'carrier',
    'interval_seconds': 86400,
    'expected_cadence_days': 1,
    'ingestion_mode': 'incremental',
    'needs_geocode': True,
    'field_map': FMCSA_OOS_FIELD_MAP }
FMCSA_CARRIER_JOINBACK_RESOURCE = f"{BASE}/inys-ebih.json"
