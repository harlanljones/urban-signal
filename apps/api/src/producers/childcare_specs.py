'''DatasetSpec-shaped plain dicts for the US-377 childcare licensing registries.

LEAF data — NOT registered anywhere. Field names mirror the ``DatasetSpec``
dataclass in ``src/spatial/city_registry.py`` exactly (``DatasetSpec(**spec)``
constructs from these dicts) so the spine can copy them mechanically during
the interlock hold; the per-city placement is documented in
``.streams/us377-childcare.md`` ("Spine delta").

All four registries ride ``FeedType.SLA`` (household-formation proxy) through
the shared ``sla_licenses_producer`` classify->geocode->H3 path:

- TX HHSC CCL ``bc5r-88dy`` is a state-wide registry covering four registered
  metros, so like the US-372 TABC specs it is exposed as a per-city county
  slice (``tx_hhsc_ccl_spec(county)``): Austin/TRAVIS, Dallas/DALLAS,
  Fort Worth/TARRANT, El Paso/EL PASO. Incremental on Socrata ``:updated_at``
  (composed into ``$select`` so the watermark layer reads it from rows;
  server-side ``$where`` verified live) — in-place edits move ``:updated_at``
  without touching ``issuance_date``.
- NY OCFS ``cb42-qumz`` is incremental on ``:updated_at`` with NYC excluded
  server-side (``region_code != \'NYCDOH\'`` — 8,576 rows redundant with the
  DOHMH feed). ``ny_ocfs_spec(region_code)`` cuts optional per-city slices
  (Buffalo/BRO, Rochester/RRO, Syracuse/SRO, Albany/ARO).
- NYC DOHMH ``gy3q-4tzp`` is an active-only registry with no date or status
  column: snapshot full pull, churn via absence diff (KC SLA precedent,
  US-134); freshness rides Socrata ``rowsUpdatedAt``. Daily, 2,750 rows.
- DC child development centers is ARCGIS
  (``DCGIS_DATA/Public_Service_WebMercator/MapServer/33``, 452 point
  features): no ``:updated_at``, no ``$select`` composition, epoch-ms dates
  ISO-normalized by ``ArcGISClient._flatten_feature``. Snapshot full pull at
  the server\'s 1,000-row page cap.

license_type NAMESPACING rides the endpoint string for the three Socrata
registries (``tx_ccl:`` / ``ny_ocfs:`` / ``nyc_cc:`` — all composed selects
verified live 2026-08-28); the DC ArcGIS layer cannot compose ``$select``, so
its license_type stays unnamespaced.
'''
from src.config import settings
from src.producers.field_maps_childcare import DC_CHILD_DEV_FIELD_MAP, NY_OCFS_FIELD_MAP, NYC_DOHMH_FIELD_MAP, TX_HHSC_CCL_FIELD_MAP
TX_HHSC_CCL_ENDPOINT = "https://data.texas.gov/resource/bc5r-88dy.json?$select=*, 'tx_ccl:' || type_of_issuance as license_type_ns, :updated_at"
NY_OCFS_ENDPOINT = "https://data.ny.gov/resource/cb42-qumz.json?$select=*, 'ny_ocfs:' || program_type as license_type_ns, trim(street_number || ' ' || street_name) as street_address_ns, :updated_at"
NYC_DOHMH_ENDPOINT = "https://data.cityofnewyork.us/resource/gy3q-4tzp.json?$select=*, 'nyc_cc:' || facility_type as license_type_ns"
DC_CHILD_DEV_ENDPOINT = 'https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Public_Service_WebMercator/MapServer/33'
TX_CCL_METRO_COUNTIES: dict[(str, str)] = {
    'austin': 'TRAVIS',
    'dallas': 'DALLAS',
    'fort_worth': 'TARRANT',
    'el_paso': 'EL PASO' }
NY_OCFS_METRO_REGIONS: dict[(str, str)] = {
    'buffalo': 'BRO',
    'rochester': 'RRO',
    'syracuse': 'SRO' }

def tx_hhsc_ccl_spec(county = None):
    '''TX HHSC CCL operations for one county slice (Travis/Dallas/Tarrant/El Paso).'''
    return {
        'endpoint': TX_HHSC_CCL_ENDPOINT,
        'platform': 'socrata',
        'watermark_col': ':updated_at',
        'id_keys': [
            'operation_id',
            'operation_number'],
        'topic': settings.topic_sla,
        'interval_seconds': 86400,
        'producer_key': 'sla',
        'expected_cadence_days': 1,
        'ingestion_mode': 'incremental',
        'where': f'''county = \'{county}\'''',
        'needs_geocode': True,
        'geocode_context': 'TX',
        'order_by': ':updated_at DESC',
        'field_map': TX_HHSC_CCL_FIELD_MAP }


def ny_ocfs_spec(region_code = None):
    '''NY OCFS facilities, upstate + state context (NYC excluded server-side).

    Pass an OCFS regional-office code (BRO/RRO/SRO/ARO/LIRO/YRO) for a
    per-city slice; the default keeps every non-NYC region.
    '''
    where = "region_code != 'NYCDOH'"
    if region_code:
        where += f''' AND region_code = \'{region_code}\''''
    return {
        'endpoint': NY_OCFS_ENDPOINT,
        'platform': 'socrata',
        'watermark_col': ':updated_at',
        'id_keys': [
            'facility_id'],
        'topic': settings.topic_sla,
        'interval_seconds': 86400,
        'producer_key': 'sla',
        'expected_cadence_days': 1,
        'ingestion_mode': 'incremental',
        'where': where,
        'needs_geocode': True,
        'geocode_context': 'NY',
        'order_by': ':updated_at DESC',
        'field_map': NY_OCFS_FIELD_MAP }

NYC_DOHMH_SPEC: dict = {
    'endpoint': NYC_DOHMH_ENDPOINT,
    'platform': 'socrata',
    'watermark_col': '',
    'id_keys': [
        'dcid',
        'permit_number'],
    'topic': settings.topic_sla,
    'interval_seconds': 86400,
    'producer_key': 'sla',
    'expected_cadence_days': 1,
    'ingestion_mode': 'snapshot',
    'needs_geocode': True,
    'geocode_context': 'NY',
    'field_map': NYC_DOHMH_FIELD_MAP }
DC_CHILD_DEV_SPEC: dict = {
    'endpoint': DC_CHILD_DEV_ENDPOINT,
    'platform': 'arcgis',
    'watermark_col': '',
    'id_keys': [
        'LICENSE_NUMBER',
        'OBJECTID'],
    'topic': settings.topic_sla,
    'interval_seconds': 86400,
    'producer_key': 'sla',
    'expected_cadence_days': 1,
    'ingestion_mode': 'snapshot',
    'oid_field': 'OBJECTID',
    'max_record_count': 1000,
    'needs_geocode': False,
    'field_map': DC_CHILD_DEV_FIELD_MAP }
CHILD_CARE_SPECS: dict[(str, dict)] = {
    'nyc_dohmh': NYC_DOHMH_SPEC,
    'dc_child_dev': DC_CHILD_DEV_SPEC }
