"""FMCSA carrier field maps (US-373).

Three data.transportation.gov Socrata resources ride the SLALicenseEvent
classify→geocode→H3 path as a national carrier-license flow. Keys are the
lowercase names the resource API returns in rows — the ticket's ADD_DATE /
STATUS_CHANGE_DATE / OOS_DATE are the metadata spellings of the same columns.

Only the Company Census carries a physical address. AuthHist and OOS rows
acquire census address fields through the DOT_NUMBER join-back in
carrier_license_producer.py, so their own maps stay honest about what their
resources publish and the census map owns every address key.

Census status_code 'I' includes dormant shells, not only closures — feature
names downstream must not claim otherwise ('carrier_active_count' counts
status_code='A'; exits come from AuthHist/OOS events, never from status I).
"""
FMCSA_CENSUS_FIELD_MAP: dict[(str, list[str])] = {
    'license_id': [
        'dot_number'],
    'premises_name': [
        'legal_name'],
    'dba': [
        'dba_name'],
    'address_street': [
        'phy_street'],
    'effective_date': [
        'add_date'],
    'status': [
        'status_code'],
    'city': [
        'phy_city'],
    'state': [
        'phy_state'],
    'zip': [
        'phy_zip'],
    'county_fips': [
        'phy_cnty'] }
FMCSA_AUTHHIST_FIELD_MAP: dict[(str, list[str])] = {
    'license_id': [
        'usdot_number'],
    'license_type': [
        'op_auth_type'],
    'status': [
        'op_auth_status'],
    'effective_date': [
        'status_change_date'] }
FMCSA_OOS_FIELD_MAP: dict[(str, list[str])] = {
    'license_id': [
        'dot_number'],
    'premises_name': [
        'legal_name'],
    'status': [
        'status'],
    'effective_date': [
        'oos_date'],
    'expiration_date': [
        'rescind_date'] }

# Spec-key -> field map, keyed by the spec keys in fmcsa_specs.py so the
# carrier producer can drive the unmodified SLA parse path per resource.
_SPEC_FIELD_MAPS: dict[str, dict[str, list[str]]] = {
    "fmcsa_census": FMCSA_CENSUS_FIELD_MAP,
    "fmcsa_authhist": FMCSA_AUTHHIST_FIELD_MAP,
    "fmcsa_oos": FMCSA_OOS_FIELD_MAP,
}
