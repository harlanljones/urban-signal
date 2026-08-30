"""Unit tests for SeriesClient, the geography crosswalk and macro_series (US-363 §1.1).

Fixtures are trimmed from the live files fetched 2026-08-28. Network-free:
the crosswalk is fed a stub payload, and every parser is exercised on text.
"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.features.macro_series_store import MacroSeriesStore
from src.producers.series_client import (
    LONG_ROWS,
    PROFILE_BULK_CSV,
    WIDE_DATES_AS_COLUMNS,
    SeriesClient,
    SeriesFetchError,
    SeriesObservation,
    SeriesSpec,
    build_period,
    parse_period,
    to_float,
)
from src.spatial.geography_crosswalk import (
    CBSA_SUBMARKET_CITIES,
    METRO_NAME_OVERRIDES,
    GeographyCrosswalk,
    metro_primary_key,
    normalize_metro_name,
    normalize_zcta,
)
from src.spatial.series_registry import (
    KEYLESS_SERIES,
    SERIES_REGISTRY,
    ZILLOW_ATTRIBUTION,
    get_series,
)

# Header + two rows, column names verbatim from the live ZORI file.
ZORI_CSV = (
    "RegionID,SizeRank,RegionName,RegionType,StateName,State,City,Metro,CountyName,"
    "2026-05-31,2026-06-30,2026-07-31\n"
    '91982,1,77494,zip,TX,TX,Katy,"Houston-The Woodlands-Sugar Land, TX",Fort Bend County,'
    "2100.5,2110.0,2125.25\n"
    '61639,2,10017,zip,NY,NY,New York,"New York, NY",New York County,'
    "4200,,4250\n"
)

# FHFA hpi_master rows, verbatim shape. Only the purchase-only quarterly MSA
# slice may survive the filter.
FHFA_CSV = (
    "hpi_type,hpi_flavor,frequency,level,place_name,place_id,yr,period,"
    "index_nsa,index_sa,rstderr,note\n"
    "traditional,purchase-only,quarterly,MSA,\"New York, NY\",35620,2026,2,310.55,309.1,,\n"
    "traditional,all-transactions,quarterly,MSA,\"New York, NY\",35620,2026,2,999.99,,,\n"
    "traditional,purchase-only,monthly,USA or Census Division,East North Central Division,"
    "DV_ENC,1991,1,100.00,100.00,,\n"
    "traditional,purchase-only,quarterly,MSA,\"Chicago-Naperville-Elgin, IL-IN\",16980,2026,1,"
    "210.10,,,\n"
)


@pytest.fixture(scope="module")
def crosswalk() -> GeographyCrosswalk:
    return GeographyCrosswalk().load()


@pytest.fixture
def client(crosswalk) -> SeriesClient:
    return SeriesClient(crosswalk=crosswalk)


# --------------------------------------------------------------------------- #
# period + value parsing                                                        #
# --------------------------------------------------------------------------- #


class TestPeriodParsing:
    def test_month_end_headers_normalize_to_month_start(self):
        # Zillow labels columns with the last day of the month. Normalizing to
        # the first keeps the key space from forking if they ever switch.
        assert parse_period("2026-07-31") == date(2026, 7, 1)
        assert parse_period("2026-02-28") == date(2026, 2, 1)

    def test_iso_month_and_bare_year(self):
        assert parse_period("2026-07") == date(2026, 7, 1)
        assert parse_period("2024") == date(2024, 1, 1)

    def test_identity_columns_are_not_periods(self):
        for header in ("RegionID", "SizeRank", "RegionName", "Metro", "CountyName", ""):
            assert parse_period(header) is None

    def test_quarter_composition(self):
        assert build_period([2026, 1], "quarter") == date(2026, 1, 1)
        assert build_period([2026, 2], "quarter") == date(2026, 4, 1)
        assert build_period([2026, 4], "quarter") == date(2026, 10, 1)
        assert build_period([2026, 5], "quarter") is None

    def test_month_composition(self):
        assert build_period([1991, 12], "month") == date(1991, 12, 1)
        assert build_period([1991, 13], "month") is None

    def test_non_numeric_place_ids_never_become_years(self):
        # FHFA's census-division rows carry place_id `DV_ENC`; the filter
        # excludes them, but the period builder must not crash on one either.
        assert build_period(["DV_ENC", "1"], "quarter") is None


class TestValueCoercion:
    @pytest.mark.parametrize("raw", ["", "  ", ".", "-", "NA", "N/A", None, "abc"])
    def test_blanks_are_absent_not_zero(self, raw):
        assert to_float(raw) is None

    def test_numbers_and_formatting(self):
        assert to_float("2125.25") == pytest.approx(2125.25)
        assert to_float("1,234") == pytest.approx(1234.0)
        assert to_float("$980") == pytest.approx(980.0)


# --------------------------------------------------------------------------- #
# geography crosswalk                                                           #
# --------------------------------------------------------------------------- #


class TestGeographyCrosswalk:
    def test_zcta_normalization(self):
        assert normalize_zcta("10017-1234") == "10017"
        assert normalize_zcta(601) == "00601"
        assert normalize_zcta(" 90210 ") == "90210"
        assert normalize_zcta("") == ""
        assert normalize_zcta("abc") == ""

    def test_zip_resolves_to_the_right_metro(self, crosswalk):
        assert crosswalk.city_for_zip("10017") == "nyc"
        assert crosswalk.city_for_zip("60614") == "chicago"
        assert crosswalk.city_for_zip("98101") == "seattle"

    def test_zip_outside_every_metro_resolves_to_nothing(self, crosswalk):
        # A national file covers thousands of ZIPs we do not register. They
        # must resolve to None, never to the nearest city.
        assert crosswalk.city_for_zip("99999") is None
        assert crosswalk.city_for_zip("59001") is None  # rural Montana

    def test_metro_name_normalization_strips_gazetteer_suffixes(self):
        assert normalize_metro_name("Abilene, TX Metro Area") == "abilene, tx"
        assert normalize_metro_name("Adrian, MI Micro Area") == "adrian, mi"

    def test_primary_key_survives_redelineation(self):
        # The 2024 Gazetteer carries 2023 OMB titles while Zillow ships the
        # older ones; only (primary city, first state) is stable across both.
        assert metro_primary_key("Houston-Pasadena-The Woodlands, TX Metro Area") == (
            "houston",
            "tx",
        )
        assert metro_primary_key("Houston-The Woodlands-Sugar Land, TX") == ("houston", "tx")
        assert metro_primary_key("Chicago-Naperville-Elgin, IL-IN-WI") == ("chicago", "il")
        assert metro_primary_key("no comma here") is None

    @pytest.mark.parametrize(
        "label,expected",
        [
            ("Houston-The Woodlands-Sugar Land, TX", "houston"),
            ("New York, NY", "nyc"),
            ("Chicago-Naperville-Elgin, IL-IN-WI", "chicago"),
            ("Seattle-Tacoma-Bellevue, WA", "seattle"),
            ("Denver-Aurora-Lakewood, CO", "denver"),
            ("Washington-Arlington-Alexandria, DC-VA-MD-WV", "washington_dc"),
            ("Miami-Fort Lauderdale-Pompano Beach, FL", "miami_dade"),
            ("Columbus, GA-AL", "columbus_ga"),
            ("Columbus, GA-AL Metro Area", "columbus_ga"),
            ("Columbus, OH Metro Area", "columbus"),
        ],
    )
    def test_publisher_metro_labels_resolve(self, crosswalk, label, expected):
        assert crosswalk.city_for_metro_name(label) == expected

    def test_miami_ok_is_not_miami_fl(self, crosswalk):
        # CBSA 33060 is the Miami, OK micro area. A bare "miami" alias would
        # hand Oklahoma's rents to Miami-Dade; the state half prevents it.
        assert crosswalk.city_for_metro_name("Miami, OK") is None
        assert ("miami", "fl") in METRO_NAME_OVERRIDES

    def test_columbus_ga_is_not_columbus_oh(self, crosswalk):
        # Bare alias "columbus" is Columbus, OH. Columbus, GA-AL (CBSA 17980)
        # landed on main after this PR was cut; without a (city, state)
        # override it would steal Ohio's series or drop GA as unreachable.
        assert ("columbus", "ga") in METRO_NAME_OVERRIDES
        assert crosswalk.city_for_metro_name("Columbus, GA-AL") == "columbus_ga"
        assert crosswalk.city_for_metro_name("Columbus, OH") == "columbus"

    def test_every_registered_city_is_reachable_except_the_submarkets(self, crosswalk):
        from src.spatial.city_registry import REGISTRY

        reached = {
            city
            for city in (crosswalk.city_for_cbsa(code) for code in crosswalk._load_cbsas())
            if city
        }
        unreachable = {cid.value for cid in REGISTRY} - reached
        assert unreachable == set(CBSA_SUBMARKET_CITIES), (
            "a registered market lost its CBSA link — metro-level series will "
            "silently skip it"
        )

    def test_cbsa_centroids_are_not_used_for_containment(self, crosswalk):
        # Seattle-Tacoma-Bellevue's internal point sits east of Seattle's
        # metro_bbox entirely. If CBSA resolution ever regresses to centroid
        # containment this test fails rather than the series silently emptying.
        point = crosswalk._load_cbsas()["42660"]
        assert crosswalk.city_for_point(point.latitude, point.longitude) != "seattle"
        assert crosswalk.city_for_cbsa("42660") == "seattle"

    def test_zip_to_h3_uses_the_centroid(self, crosswalk):
        from src.spatial.h3_indexer import H3SpatialIndexer

        tags = crosswalk.zip_to_h3("10017", H3SpatialIndexer())
        assert tags["h3_res7"] and tags["h3_res8"] and tags["h3_res9"]
        assert crosswalk.zip_to_h3("99999", H3SpatialIndexer())["h3_res9"] is None


# --------------------------------------------------------------------------- #
# parsing                                                                       #
# --------------------------------------------------------------------------- #


class TestWideCsvParsing:
    def spec(self) -> SeriesSpec:
        return SeriesSpec(
            series_id="zori_zip",
            source="zillow",
            dataset_id="https://example.invalid/zori.csv",
            layout=WIDE_DATES_AS_COLUMNS,
            geography_level="zip",
            geography_col="RegionName",
            metro_col="Metro",
            unit="usd_per_month",
        )

    def test_one_observation_per_populated_period(self, client):
        obs = list(client.parse_wide_csv(self.spec(), ZORI_CSV, "2026-08-28"))
        # 3 periods for 77494 + 2 for 10017 (its June cell is blank).
        assert len(obs) == 5
        assert {o.geography_id for o in obs} == {"77494", "10017"}

    def test_blank_cells_are_skipped_not_zeroed(self, client):
        obs = list(client.parse_wide_csv(self.spec(), ZORI_CSV, "2026-08-28"))
        june = [o for o in obs if o.geography_id == "10017" and o.period == date(2026, 6, 1)]
        assert june == [], "a blank rent cell became a rent of 0"

    def test_geography_and_city_resolution(self, client):
        obs = list(client.parse_wide_csv(self.spec(), ZORI_CSV, "2026-08-28"))
        by_zip = {o.geography_id: o.city_id for o in obs}
        assert by_zip["10017"] == "nyc"
        assert by_zip["77494"] == "houston"

    def test_periods_are_month_starts(self, client):
        obs = list(client.parse_wide_csv(self.spec(), ZORI_CSV, "2026-08-28"))
        assert {o.period for o in obs} <= {date(2026, 5, 1), date(2026, 6, 1), date(2026, 7, 1)}

    def test_vintage_and_unit_ride_along(self, client):
        obs = list(client.parse_wide_csv(self.spec(), ZORI_CSV, "2026-08-28"))
        assert all(o.source_vintage == "2026-08-28" for o in obs)
        assert all(o.unit == "usd_per_month" for o in obs)

    def test_a_file_with_no_period_columns_is_an_error_not_an_empty_result(self, client):
        with pytest.raises(SeriesFetchError, match="no period columns"):
            list(client.parse_wide_csv(self.spec(), "RegionID,RegionName\n1,10017\n", "v"))

    def test_unregistered_geographies_are_dropped(self, client):
        csv_text = (
            "RegionID,SizeRank,RegionName,RegionType,StateName,State,City,Metro,CountyName,"
            "2026-07-31\n1,1,59001,zip,MT,MT,Absarokee,\"Billings, MT\",Stillwater,900\n"
        )
        assert list(client.parse_wide_csv(self.spec(), csv_text, "v")) == []


class TestLongCsvParsing:
    def spec(self) -> SeriesSpec:
        return SERIES_REGISTRY["fhfa_hpi_metro"]

    def test_row_filter_selects_exactly_one_series(self, client):
        obs = list(client.parse_long_csv(self.spec(), FHFA_CSV, "2026-08-28"))
        assert len(obs) == 2, "the row filter let another hpi_flavor or level through"
        assert all(o.value != 999.99 for o in obs)

    def test_quarter_periods(self, client):
        obs = {o.geography_id: o for o in client.parse_long_csv(self.spec(), FHFA_CSV, "v")}
        assert obs["35620"].period == date(2026, 4, 1)  # 2026 Q2
        assert obs["16980"].period == date(2026, 1, 1)  # 2026 Q1

    def test_cbsa_place_ids_resolve_to_cities(self, client):
        obs = {o.geography_id: o.city_id for o in client.parse_long_csv(self.spec(), FHFA_CSV, "v")}
        assert obs["35620"] == "nyc"
        assert obs["16980"] == "chicago"

    def test_value_column_is_the_index(self, client):
        obs = {o.geography_id: o.value for o in client.parse_long_csv(self.spec(), FHFA_CSV, "v")}
        assert obs["35620"] == pytest.approx(310.55)


class TestCensusParsing:
    def spec(self) -> SeriesSpec:
        return SERIES_REGISTRY["acs_median_gross_rent_zcta"]

    def test_suppressed_cells_are_dropped(self, client):
        payload = [
            ["NAME", "B25064_001E", "zip code tabulation area"],
            ["ZCTA5 10017", "2450", "10017"],
            ["ZCTA5 60614", "-666666666", "60614"],
        ]
        obs = list(client.parse_census_rows(self.spec(), payload, "v", date(2023, 1, 1)))
        assert [o.geography_id for o in obs] == ["10017"], (
            "Census suppression sentinel -666666666 was read as a rent"
        )

    def test_missing_value_column_is_an_error(self, client):
        with pytest.raises(SeriesFetchError, match="absent"):
            list(
                client.parse_census_rows(
                    self.spec(), [["NAME", "other"], ["x", "1"]], "v", date(2023, 1, 1)
                )
            )


class TestHudParsing:
    def spec(self) -> SeriesSpec:
        return SERIES_REGISTRY["hud_safmr_zip"]

    def test_envelope_is_unwrapped(self, client):
        payload = {
            "data": {
                "year": "2026",
                "basicdata": [
                    {"zip_code": "10017", "Two-Bedroom": 3900},
                    {"zip_code": "99999", "Two-Bedroom": 800},
                ],
            }
        }
        obs = list(client.parse_hud_payload(self.spec(), payload, "v"))
        assert [o.geography_id for o in obs] == ["10017"]
        assert obs[0].period == date(2026, 1, 1)

    def test_missing_token_fails_loudly(self, client, monkeypatch):
        monkeypatch.delenv("HUD_API_TOKEN", raising=False)
        with pytest.raises(SeriesFetchError, match="HUD_API_TOKEN"):
            client.fetch(self.spec())


# --------------------------------------------------------------------------- #
# macro_series store                                                            #
# --------------------------------------------------------------------------- #


def obs(value: float, vintage: str = "v1", period: date = date(2026, 7, 1)) -> SeriesObservation:
    return SeriesObservation(
        series_id="zori_zip",
        geography_level="zip",
        geography_id="10017",
        period=period,
        value=value,
        source_vintage=vintage,
        city_id="nyc",
        unit="usd_per_month",
    )


class TestMacroSeriesStore:
    def test_first_release_inserts(self):
        store = MacroSeriesStore()
        result = store.upsert([obs(4200.0)])
        assert (result.inserted, result.revised, result.unchanged) == (1, 0, 0)
        assert store.count() == 1
        assert store.value("nyc", "zori_zip", "10017", date(2026, 7, 1)) == pytest.approx(4200.0)

    def test_identical_release_changes_nothing(self):
        store = MacroSeriesStore()
        store.upsert([obs(4200.0)])
        result = store.upsert([obs(4200.0, vintage="v2")])
        assert (result.inserted, result.revised, result.unchanged) == (0, 0, 1)

    def test_a_revision_overwrites_and_retains_the_old_value(self):
        store = MacroSeriesStore()
        store.upsert([obs(4200.0, vintage="v1")])
        result = store.upsert([obs(4250.0, vintage="v2")])
        assert (result.inserted, result.revised, result.unchanged) == (0, 1, 0)
        assert store.value("nyc", "zori_zip", "10017", date(2026, 7, 1)) == pytest.approx(4250.0)
        history = store.vintages("nyc", "zori_zip", "10017", date(2026, 7, 1))
        assert len(history) == 1
        assert history[0]["value"] == pytest.approx(4200.0)
        assert history[0]["source_vintage"] == "v1"
        assert history[0]["superseded_by"] == "v2"

    def test_history_accumulates_across_revisions(self):
        store = MacroSeriesStore()
        for i, v in enumerate([4200.0, 4250.0, 4300.0]):
            store.upsert([obs(v, vintage=f"v{i}")])
        assert len(store.vintages("nyc", "zori_zip", "10017", date(2026, 7, 1))) == 2

    def test_repeated_key_within_one_release_collapses(self):
        store = MacroSeriesStore()
        result = store.upsert([obs(4200.0), obs(4250.0)])
        assert result.total == 1
        assert store.count() == 1

    def test_max_period_is_a_freshness_signal(self):
        store = MacroSeriesStore()
        store.upsert([obs(1.0, period=date(2026, 5, 1)), obs(2.0, period=date(2026, 7, 1))])
        assert store.max_period("zori_zip") == date(2026, 7, 1)
        assert store.max_period("zori_zip", "10017") == date(2026, 7, 1)
        assert store.max_period("nope") is None

    def test_latest_by_geography(self):
        store = MacroSeriesStore()
        store.upsert([obs(1.0, period=date(2026, 5, 1)), obs(2.0, period=date(2026, 7, 1))])
        assert store.latest_by_geography("nyc", "zori_zip") == {"10017": pytest.approx(2.0)}

    def test_empty_release_is_a_no_op(self):
        store = MacroSeriesStore()
        assert store.upsert([]).total == 0


# --------------------------------------------------------------------------- #
# registry                                                                      #
# --------------------------------------------------------------------------- #


class TestSeriesRegistry:
    def test_every_zillow_series_carries_the_required_attribution(self):
        for spec in SERIES_REGISTRY.values():
            if spec.source == "zillow":
                assert spec.attribution == ZILLOW_ATTRIBUTION, (
                    f"{spec.series_id}: Zillow ToU §4.C requires attribution on "
                    f"every surface that renders the data"
                )

    def test_credentialed_series_name_their_environment_variable(self):
        for spec in SERIES_REGISTRY.values():
            if spec.auth != "none":
                assert spec.auth_env, f"{spec.series_id} needs auth but names no env var"

    def test_keyless_series_are_the_ones_that_can_run_unattended(self):
        assert set(KEYLESS_SERIES) == {
            "zori_zip",
            "zhvi_zip",
            "zhvf_metro",
            "fhfa_hpi_metro",
            "ntd_upt",
            "ntd_vrm",
            "ntd_vrh",
            "ntd_voms",
        }

    def test_every_series_is_revision_aware(self):
        # These publishers reissue and revise full history; an append-only
        # ingestion mode would freeze the first vintage of every revised month.
        for spec in SERIES_REGISTRY.values():
            assert spec.ingestion_mode == "full", spec.series_id

    def test_unknown_series_error_names_the_known_ones(self):
        with pytest.raises(KeyError, match="zori_zip"):
            get_series("nope")

    def test_bulk_csv_specs_declare_a_layout_the_parser_knows(self):
        for spec in SERIES_REGISTRY.values():
            if spec.profile == PROFILE_BULK_CSV:
                assert spec.layout in (WIDE_DATES_AS_COLUMNS, LONG_ROWS), spec.series_id
                if spec.layout == LONG_ROWS:
                    assert spec.value_col and spec.period_cols, spec.series_id

    def test_cadences_match_publisher_practice(self):
        assert SERIES_REGISTRY["zori_zip"].cadence_days == 31       # monthly, the 16th
        assert SERIES_REGISTRY["fhfa_hpi_metro"].cadence_days == 92  # quarterly
        assert SERIES_REGISTRY["hud_safmr_zip"].cadence_days == 365  # each October
