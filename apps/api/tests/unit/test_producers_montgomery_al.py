"""Unit tests for the Montgomery, AL leaf (US-424): geometry and permits.

Montgomery registers Construction Permits from the City's own server
(HostedDatasets/Construction_Permits, gis.montgomeryal.gov, 47.5k rows
loaded weekly, IssuedDate date watermark), which on 2026-10-03 replaced the
ArcGIS Online All_Permit_viewlayer that stopped in 2024, and the 311 Service
Requests layer (Received_311_Service_Request, gis.montgomeryal.gov, 228.6k
rows, Create_Date date watermark). The spatial tests cover metro bbox
sanity, division containment, and submarket placement inside their declared
division bbox.
"""

from src.spatial.cities.montgomery_al import (
    MONTGOMERY_AL_CITY_ID,
    MONTGOMERY_AL_DIVISION_BBOXES,
    MONTGOMERY_AL_DIVISIONS,
    MONTGOMERY_AL_METRO_BBOX,
    MONTGOMERY_AL_SUBMARKETS,
    REGISTRATION,
    is_in_montgomery_al_metro,
)
from src.spatial.city_registry import CityId, FeedType, get_dataset


class TestMontgomeryALSpatial:
    def test_metro_bbox_sanity(self):
        assert MONTGOMERY_AL_METRO_BBOX["min_lat"] < MONTGOMERY_AL_METRO_BBOX["max_lat"]
        assert MONTGOMERY_AL_METRO_BBOX["min_lng"] < MONTGOMERY_AL_METRO_BBOX["max_lng"]

    def test_is_in_montgomery_al_metro_rejects_missing_coordinates(self):
        assert is_in_montgomery_al_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in MONTGOMERY_AL_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= MONTGOMERY_AL_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= MONTGOMERY_AL_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= MONTGOMERY_AL_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= MONTGOMERY_AL_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in MONTGOMERY_AL_SUBMARKETS.items():
            bbox = MONTGOMERY_AL_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in MONTGOMERY_AL_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(MONTGOMERY_AL_SUBMARKETS)

    def test_city_id_and_registration_shape(self):
        assert MONTGOMERY_AL_CITY_ID == "montgomery_al"
        assert REGISTRATION.metro_bbox is MONTGOMERY_AL_METRO_BBOX
        assert REGISTRATION.submarkets is MONTGOMERY_AL_SUBMARKETS
        assert 4 <= len(MONTGOMERY_AL_DIVISIONS) <= 8
        assert 6 <= len(MONTGOMERY_AL_SUBMARKETS) <= 10


class TestMontgomeryALPermitsSpec:
    def test_permits_read_the_city_server_layer_newest_first(self):
        spec = get_dataset(CityId.MONTGOMERY_AL, FeedType.PERMITS)
        assert spec.endpoint == (
            "https://gis.montgomeryal.gov/server/rest/services/HostedDatasets/Construction_Permits/FeatureServer/0"
        )
        assert spec.watermark_col == "IssuedDate"
        assert spec.order_by == "IssuedDate DESC, OBJECTID DESC"
        # Two rows carry no PermitNo; they key on their OBJECTID.
        assert spec.id_keys == ["PermitNo", "OBJECTID"]
        assert spec.field_map["job_id"] == ["PermitNo", "OBJECTID"]
        # About one row in six sits at 0,0, outside the box.
        assert spec.metro_clip is True

    def test_permits_never_read_owner_contractor_or_mailing_columns(self):
        spec = get_dataset(CityId.MONTGOMERY_AL, FeedType.PERMITS)
        selected = set(spec.select.split(","))
        mapped = {column for columns in spec.field_map.values() for column in columns}
        assert mapped <= selected
        # ``Address`` is an applicant-style mailing address, not the site.
        assert not selected & {"OwnerName", "OwnerAddress", "ContractorName", "Address"}
        assert spec.field_map["address_street"] == ["PhysicalAddress"]
