'''Field maps for the US-377 state childcare licensing registries.

LEAF module — NOT imported by the shared producers at runtime. In production
each map is merged into the owning city\'s ``CityRegistration``
``datasets[FeedType.SLA].field_map`` in ``src/spatial/city_registry.py`` (the
spine) when the orchestrator applies the interlock; this file proves the
proposed spellings resolve through the unmodified ``sla_licenses_producer``
and hands the spine a copy-pasteable contract. The status vocabularies and
care filter are small pure helpers the spine wires after the shared parse
(they need the registry key, which only the owning registration knows).

Sources, all live-verified 2026-08-28 from this host (counts, watermarks and
distinct vocabularies in .streams/us377-childcare.md; byte-verbatim fixtures
in tests/fixtures/childcare/):

- TX HHSC Child Care Licensing ``bc5r-88dy`` (data.texas.gov) — daily full
  state registry (14,988 rows) covering Austin/Dallas/Fort Worth/El Paso via
  ``county``. ``issuance_date`` is the permit date but ~64 rows/week re-pass
  any business-date filter on in-place edits, so the owning specs watermark
  Socrata ``:updated_at`` (verified server-side). ``location_address_geo`` is
  a point on most rows but degrades to ``human_address``-only on others
  (e.g. the newest San Antonio row), so latitude/longitude ride the dotted
  candidates and address/ZIP-only rows geocode via ``needs_geocode`` (ADR
  0004). NO expiration column exists on this dataset.
- NY OCFS child care facility listing ``cb42-qumz`` (data.ny.gov) — daily
  state registry (16,722 rows). NYC is excluded server-side with
  ``region_code != \'NYCDOH\'`` (8,576 rows, the state\'s own NYC region —
  redundant with the DOHMH feed below); city slices ride the same region
  code. 732 rows lack coordinates (mostly family-based programs) and geocode
  from the composed ``street_address_ns`` (ADR 0004).
- NYC DOHMH child care inspection-permit programs ``gy3q-4tzp`` — active
  permits only, NO date or status column: churn is the absence diff of the
  daily snapshot (a permit that lapses disappears from the file rather than
  flipping a column). ``facility_type`` GCC/SBCC namespaces the license type.
- DC child development centers, ArcGIS
  ``DCGIS_DATA/Public_Service_WebMercator/MapServer/33`` (maps2.dcgis.dc.gov)
  — 452 point features. PLATFORM DIFFERENCE: ArcGIS, not Socrata — no
  ``:updated_at``, no ``$select`` composition (so no license_type namespace),
  epoch-ms dates ISO-normalized by ``ArcGISClient._flatten_feature``, and a
  ``maxRecordCount`` page cap of 1,000. There is no separate status column;
  ``LICENSE_TYPE`` (Full License / Restricted / Temporary Closure) doubles as
  the status vocabulary. 452 rows make a daily full pull cheaper than any
  watermark scheme.

license_type NAMESPACING (Socrata registries): ``license_type_ns`` does not
exist on the sources — each spec\'s endpoint carries
``?$select=*, \'<ns>:\' || <col> as license_type_ns`` so flow features can
distinguish the childcare registries from liquor feeds sharing the SLA topic
(httpx merges the client\'s pagination params with the URL\'s ``$select``;
verified live through ``SocrataClient.paginate``). ``:updated_at`` rides the
same composition for the TX/NY watermark columns.

Canonical fields mirror the chains in ``sla_licenses_producer`` /
``field_maps.first_mapped``: license_id, license_type, effective_date,
expiration_date, premises_name, dba, address_street, status, latitude,
longitude, borough. Keyed to the FeedType *value* string ("sla") semantics of
``field_maps.resolve_field_map``.
'''
from typing import Any
TX_HHSC_CCL_FIELD_MAP: dict[(str, list[str])] = {
    'license_id': [
        'operation_id'],
    'license_type': [
        'license_type_ns',
        'type_of_issuance'],
    'effective_date': [
        'issuance_date'],
    'premises_name': [
        'administrator_director_name'],
    'dba': [
        'operation_name'],
    'address_street': [
        'address_line',
        'location_address'],
    'status': [
        'operation_status'],
    'latitude': [
        'location_address_geo.latitude'],
    'longitude': [
        'location_address_geo.longitude'],
    'borough': [
        'city'] }
NY_OCFS_FIELD_MAP: dict[(str, list[str])] = {
    'license_id': [
        'facility_id'],
    'license_type': [
        'license_type_ns',
        'program_type'],
    'effective_date': [
        'license_issue_date'],
    'expiration_date': [
        'license_expiration_date'],
    'premises_name': [
        'provider_name'],
    'dba': [
        'facility_name'],
    'address_street': [
        'street_address_ns',
        'street_name'],
    'status': [
        'facility_status'],
    'latitude': [
        'latitude'],
    'longitude': [
        'longitude'],
    'borough': [
        'county'] }
NYC_DOHMH_FIELD_MAP: dict[(str, list[str])] = {
    'license_id': [
        'dcid'],
    'license_type': [
        'license_type_ns',
        'facility_type'],
    'dba': [
        'program_name'],
    'address_street': [
        'address'],
    'latitude': [
        'latitude'],
    'longitude': [
        'longitude'],
    'borough': [
        'borough'] }
DC_CHILD_DEV_FIELD_MAP: dict[(str, list[str])] = {
    'license_id': [
        'LICENSE_NUMBER'],
    'license_type': [
        'LICENSE_TYPE'],
    'effective_date': [
        'LICENSE_ISSUE_DATE'],
    'expiration_date': [
        'LICENSE_EXPIRATION_DATE'],
    'dba': [
        'NAME'],
    'address_street': [
        'ADDRESS'],
    'status': [
        'LICENSE_TYPE'],
    'latitude': [
        'LATITUDE'],
    'longitude': [
        'LONGITUDE'] }
FIELD_MAPS: dict[(str, dict[(str, list[str])])] = {
    'tx_hhsc_ccl': TX_HHSC_CCL_FIELD_MAP,
    'ny_ocfs': NY_OCFS_FIELD_MAP,
    'nyc_dohmh': NYC_DOHMH_FIELD_MAP,
    'dc_child_dev': DC_CHILD_DEV_FIELD_MAP }
STATUS_VOCABULARIES: dict[(str, dict[(str, str)])] = {
    'tx_hhsc_ccl': {
        'Y': 'ACTIVE',
        'N': 'INACTIVE' },
    'ny_ocfs': {
        'License': 'ACTIVE',
        'Registration': 'ACTIVE',
        'Suspended': 'INACTIVE',
        'Pending Revocation': 'INACTIVE',
        'Pending Revocation and Denial': 'INACTIVE' },
    'nyc_dohmh': { },
    'dc_child_dev': {
        'Full License': 'ACTIVE',
        'Restricted': 'ACTIVE',
        'Temporary Closure': 'INACTIVE' } }
TX_TEMPORARILY_CLOSED_STATUS: dict[(str, str)] = {
    'YES': 'INACTIVE',
    'NO': '' }

def normalize_status(registry_key = None, raw_status = None, temporarily_closed = None):
    """Map one registry's raw license status onto canonical ACTIVE/INACTIVE.

    NYC's active-only registry normalizes anything (including a missing
    status) to ACTIVE. TX consults ``temporarily_closed`` after the primary
    status so a closed-but-not-revoked operation reads INACTIVE. Unmapped
    raw values pass through stripped, and None passes through as None.
    """
    if registry_key == 'nyc_dohmh':
        return 'ACTIVE'
# WARNING: Decompyle incomplete

EXCLUDED_CARE_TYPES: dict[(str, set[str])] = {
    'tx_hhsc_ccl': {
        'Residential Treatment Center'} }
EXCLUDED_OPERATION_TYPES: dict[(str, set[str])] = {
    'tx_hhsc_ccl': {
        'Child Placing Agency'} }

def passes_care_filter(registry_key = None, row = None):
    '''Keep rows whose care type is a center/home day-care program.

    Only TX declares exclusions today; the other three registries pass every
    row. Missing care_type columns on non-TX registries are not exclusions.
    '''
    excluded_care = EXCLUDED_CARE_TYPES.get(registry_key, set())
    if excluded_care:
        if not row.get('care_type'):
            row.get('care_type')
        if str('').strip() in excluded_care:
            return False
    excluded_operation = EXCLUDED_OPERATION_TYPES.get(registry_key, set())
    if excluded_operation:
        excluded_operation
        if not row.get('operation_type'):
            row.get('operation_type')
    return not (str('').strip() in excluded_operation)

