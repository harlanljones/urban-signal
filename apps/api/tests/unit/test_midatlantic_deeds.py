"""Mid-Atlantic deeds (2026-09-30): five feeds repaired, seven retracted.

None of the fourteen deeds feeds the 2026-09-06 mid-Atlantic wave registered
ever pointed at a live source. Five now read a published last-sale or transfer
layer. Albany, Dover, Harrisburg, Huntington, Manchester, Portland (Maine) and
Wilmington (Delaware) have no public sale source, so their deeds feed is
retracted and their ``sla`` reads the SNAP retailer slice. Roanoke and Richmond
are unchanged (``docs/research/feed-health-2026-09-30.md``). Manchester's deeds
came back on 2026-10-02 from the City's own parcels (``test_manchester_deeds.py``).

Fixture rows keep each source's real column names and value formats; the ids,
addresses and prices in them are made up.
"""

import importlib
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from src.config import settings
from src.producers.arcgis_client import ArcGISClient
from src.spatial.cities.allentown import compose_deed_date
from src.spatial.city_registry import REGISTRY, CityId, FeedType, snap_sla_spec

REPAIRED = {
    "frederick": ("socrata", "opendata.maryland.gov/resource/gx8c-a963.json", "snapshot"),
    "providence": ("arcgis", "/Parcel_Zoning_FL/FeatureServer/0", "snapshot"),
    "burlington": (
        "arcgis",
        "/FS_VCGI_OPENDATA_Cadastral_PTTR_point_WM_v1_view/FeatureServer/0",
        "incremental",
    ),
    "allentown": ("arcgis", "/Tax_Parcels_Assessed_2022/FeatureServer/0", "snapshot"),
    "charleston_wv": (
        "arcgis",
        "kanawhacountyassessorgis.com/server/rest/services/Parcel_Line_Layer/MapServer/1",
        "snapshot",
    ),
}

RETRACTED = {
    "albany": "NY",
    "dover": "DE",
    "harrisburg": "PA",
    "huntington_wv": "WV",
    "portland_maine": "ME",
    "wilmington_de": "DE",
}

# Owner, grantor, buyer and seller columns on each source. They name natural
# persons, so no feed maps them and every ArcGIS feed leaves them out of
# ``select`` (``outFields``), which keeps them on the server.
PARTY_COLUMNS = {
    "frederick": {"sales_segment_1_grantor_name_mdp_field_grntnam1_sdat_field_80"},
    "providence": {"Owner1", "Owner2", "Owner3"},
    "burlington": {
        "sellEntNam", "sellLstNam", "sellFstNam", "buyEntNam", "buyLstNam", "buyFstNam",
    },
    "allentown": {"NAMOWN", "AD1OWN"},
    "charleston_wv": {"Owner_1", "Owner_2", "Street_Address", "City_State_Zip"},
}


def _deeds(city):
    return REGISTRY[CityId(city)].datasets[FeedType.DEEDS]


@pytest.mark.parametrize("city", sorted(REPAIRED))
def test_repaired_feed_reads_its_published_source(city):
    platform, endpoint_tail, mode = REPAIRED[city]
    spec = _deeds(city)
    assert spec.platform == platform
    assert spec.endpoint.endswith(endpoint_tail), spec.endpoint
    assert spec.ingestion_mode == mode


@pytest.mark.parametrize("city", sorted(REPAIRED))
def test_leaf_mirror_matches_the_registry(city):
    leaf = importlib.import_module(f"src.spatial.cities.{city}")
    assert getattr(leaf, f"get_{city}_dataset")(FeedType.DEEDS) == _deeds(city)


@pytest.mark.parametrize("city", sorted(REPAIRED))
def test_no_party_name_column_is_mapped_or_read(city):
    spec = _deeds(city)
    assert not {"party1_grantor", "party2_grantee"} & set(spec.field_map)
    mapped = {col for cols in spec.field_map.values() for col in cols}
    assert not mapped & PARTY_COLUMNS[city]
    if spec.platform == "arcgis":
        assert spec.select, "an ArcGIS parcel layer without select reads its owner columns"
        assert not set(spec.select.split(",")) & PARTY_COLUMNS[city]


@pytest.mark.parametrize("city,state", sorted(RETRACTED.items()))
def test_retracted_city_polls_only_its_snap_slice(city, state):
    registration = REGISTRY[CityId(city)]
    assert set(registration.datasets) == {FeedType.SLA}
    assert registration.datasets[FeedType.SLA] == snap_sla_spec(state, registration.metro_bbox)
    assert not hasattr(settings, f"arcgis_{city}_deeds_url")


def test_manchesters_deeds_read_the_citys_parcels_beside_its_snap_slice():
    # The wave's Manchester deeds named an ArcGIS Online service that does not
    # exist; the City's own parcel layer, found on 2026-10-02, carries each
    # parcel's latest sale.
    registration = REGISTRY[CityId.MANCHESTER]
    assert set(registration.datasets) == {FeedType.SLA, FeedType.DEEDS}
    assert registration.datasets[FeedType.SLA] == snap_sla_spec("NH", registration.metro_bbox)
    assert _deeds("manchester").endpoint == settings.arcgis_manchester_deeds_url
    assert settings.arcgis_manchester_deeds_url.startswith("https://ags.manchesternh.gov/")


class TestAllentownSaleDate:
    """The parcel layer splits the last sale into SYEAR and SMON, with no day."""

    def test_year_and_month_compose_to_the_first_of_the_month(self):
        assert compose_deed_date({"SYEAR": 2026, "SMON": "08"}) == "2026-08-01"
        assert compose_deed_date({"SYEAR": "1998", "SMON": "12"}) == "1998-12-01"

    @pytest.mark.parametrize(
        "row",
        [
            {"SYEAR": 2026, "SMON": "00"},
            {"SYEAR": 2026, "SMON": ""},
            {"SYEAR": 2026, "SMON": "13"},
            {"SYEAR": None, "SMON": "05"},
            {"SYEAR": 0, "SMON": "05"},
            {},
        ],
    )
    def test_a_missing_part_composes_nothing(self, row):
        assert compose_deed_date(row) is None


def _ms(year, month, day, hour=0):
    return int(datetime(year, month, day, hour, tzinfo=UTC).timestamp() * 1000)


def _square(lng, lat, half=0.0005):
    ring = [
        [lng - half, lat - half],
        [lng - half, lat + half],
        [lng + half, lat + half],
        [lng + half, lat - half],
        [lng - half, lat - half],
    ]
    return {"rings": [ring]}


def _flatten(attributes, geometry, date_fields=()):
    """A row as ``ArcGISClient.paginate`` delivers it (dates ISO, geometry as lat/lng)."""
    return ArcGISClient()._flatten_feature(
        {"attributes": attributes, "geometry": geometry}, date_fields=set(date_fields)
    )


FREDERICK_ROW = {
    "account_id_mdp_field_acctid": "1102999999",
    "county_name_mdp_field_cntyname": "Frederick",
    "sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89": "2026.08.06",
    "sales_segment_1_consideration_mdp_field_considr1_sdat_field_90": "395000",
    "sales_segment_1_grantor_name_mdp_field_grntnam1_sdat_field_80": "REDACTED",
    "mdp_street_address_mdp_field_address": "100 EXAMPLE ST",
    "mdp_street_address_city_mdp_field_city": "FREDERICK",
    "mdp_street_address_zip_code_mdp_field_zipcode": "21701",
    "mdp_latitude_mdp_field_digycord_converted_to_wgs84": "39.4239",
    "mdp_longitude_mdp_field_digxcord_converted_to_wgs84": "-77.4116",
    "mappable_latitude_and_longitude": "POINT (-77.4116 39.4239)",
}

PROVIDENCE_ROW = _flatten(
    {
        "OBJECTID": 101,
        "PROPID": "999-9999-0001",
        "PIN": "999999999",
        "SaleDate": "2026-09-02 00:00:00.000",
        "SalePrice": "650000",
        "ParcAddress": "100 EXAMPLE ST",
        "MuniName": "PROVIDENCE",
        "ZipCode": "02906",
    },
    _square(-71.41, 41.82),
)

BURLINGTON_ROW = _flatten(
    {
        "OBJECTID": 202,
        "returnID": 9999001,
        "span": "11499999999",
        "townCode": "114",
        "postedDate": _ms(2026, 9, 18, 12),
        "closeDate": _ms(2026, 9, 14),
        "ValPdOrTrn": 425000.0,
        "propLocStr": "100 EXAMPLE ST",
        "propLocCty": "BURLINGTON",
        "Latitude": 44.48,
        "Longitude": -73.21,
    },
    {"x": -73.21, "y": 44.48},
    date_fields=("postedDate", "closeDate"),
)

ALLENTOWN_ROW = _flatten(
    {
        "OBJECTID": 303,
        "WARDACCTNO": "99999999",
        "PIN": "549999999999",
        "PARNUM": "0001",
        "XINSTNUM": "2026999999",
        "SYEAR": 2026,
        "SMON": "08",
        "SPRICE": 375000.0,
        "PROPERTYADDR": "100 EXAMPLE ST",
        "ZIP": "18102",
    },
    _square(-75.48, 40.60),
)

CHARLESTON_WV_ROW = _flatten(
    {
        "OBJECTID": 404,
        "PARID": "12   9999999999999",
        "DIST": "12",
        "Last_Sales_Date": _ms(2026, 5, 20),
        "Deed_Book": "9999",
        "Deed_Page": "1",
        "Sales_Price": "125000",
        "Sale_Price": None,
        "Prop_Location": "100 EXAMPLE ST",
    },
    _square(-81.63, 38.35),
    date_fields=("Last_Sales_Date",),
)


class TestRowsParse:
    """Each source's row shape parses through the city's registered field map."""

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @pytest.mark.parametrize(
        "city,row,doc_id,recorded,amount",
        [
            ("frederick", FREDERICK_ROW, "1102999999", (2026, 8, 6), 395000.0),
            ("providence", PROVIDENCE_ROW, "999-9999-0001", (2026, 9, 2), 650000.0),
            ("burlington", BURLINGTON_ROW, "9999001", (2026, 9, 14), 425000.0),
            ("allentown", ALLENTOWN_ROW, "2026999999", (2026, 8, 1), 375000.0),
            ("charleston_wv", CHARLESTON_WV_ROW, "12   9999999999999", (2026, 5, 20), 125000.0),
        ],
    )
    def test_row_parses_to_a_deed(self, deeds, city, row, doc_id, recorded, amount):
        event = deeds.parse_socrata_row(dict(row), city_id=city)
        assert event is not None
        assert event.city_id == city
        assert event.doc_id == doc_id
        assert event.recorded_date.timetuple()[:3] == recorded
        assert event.document_amount == pytest.approx(amount)
        assert event.doc_type == "DEED"
        assert event.party1_grantor is None and event.party2_grantee is None
        assert event.latitude is not None and event.longitude is not None

    def test_frederick_row_autodetects_by_county_name(self, deeds):
        event = deeds.parse_socrata_row(dict(FREDERICK_ROW))
        assert event is not None
        assert event.city_id == "frederick"

    def test_polygon_parcels_take_the_centroid(self, deeds):
        event = deeds.parse_socrata_row(dict(ALLENTOWN_ROW), city_id="allentown")
        assert (event.longitude, event.latitude) == (pytest.approx(-75.48), pytest.approx(40.60))

    def test_allentown_falls_back_to_the_account_without_an_instrument(self, deeds):
        row = {**ALLENTOWN_ROW, "XINSTNUM": ""}
        event = deeds.parse_socrata_row(row, city_id="allentown")
        assert event.doc_id == "99999999"
        assert event.bbl == "549999999999"

    def test_charleston_wv_reads_the_numeric_price_when_the_text_one_is_blank(self, deeds):
        row = {**CHARLESTON_WV_ROW, "Sales_Price": "", "Sale_Price": 90000.0}
        event = deeds.parse_socrata_row(row, city_id="charleston_wv")
        assert event.document_amount == pytest.approx(90000.0)
