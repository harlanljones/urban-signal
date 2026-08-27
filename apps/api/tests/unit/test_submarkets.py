"""Unit tests for the Multi-City Submarket Registry and Spatial Layer (NYC, Chicago & San Francisco)."""

import h3
import pytest
from src.spatial.cities.chicago import (
    CHICAGO_DIVISION_BBOXES,
    CHICAGO_DIVISIONS,
    CHICAGO_METRO_BBOX,
    CHICAGO_SUBMARKETS,
    is_in_chicago_metro,
)
from src.spatial.cities.san_francisco import (
    SAN_FRANCISCO_DIVISION_BBOXES,
    SAN_FRANCISCO_DIVISIONS,
    SAN_FRANCISCO_METRO_BBOX,
    SAN_FRANCISCO_SUBMARKETS,
    SF_DIVISION_BBOXES,
    SF_DIVISIONS,
    SF_METRO_BBOX,
    SF_SUBMARKETS,
    is_in_san_francisco_metro,
    is_in_sf_metro,
)
from src.spatial.geo_utils import (
    NYC_BOROUGH_BBOXES,
    NYC_METRO_BBOX,
    get_borough_for_coordinate,
    get_borough_for_h3,
    get_city_for_coordinate,
    get_division_for_coordinate,
    get_division_for_h3,
    is_in_nyc_metro,
)
from src.spatial.submarkets import (
    NYC_BOROUGHS,
    NYC_SUBMARKETS,
    BoroughMeta,
    DivisionMeta,
    SubmarketMeta,
    find_nearest_submarket,
    get_all_submarkets,
    get_borough_catalog,
    get_city_catalog,
    get_division_catalog,
    get_submarket_by_name,
    get_submarkets,
)


class TestSubmarketRegistry:
    """Test suite for NYC, Chicago, and San Francisco submarket catalog and filtering."""

    def test_total_and_borough_submarket_counts_nyc(self):
        """Verify 50+ total NYC submarkets and distinct submarkets across all 5 boroughs."""
        all_submarkets = get_all_submarkets("nyc")
        assert len(all_submarkets) >= 50, f"Expected >= 50 submarkets, found {len(all_submarkets)}"

        manhattan = get_submarkets("MANHATTAN")
        brooklyn = get_submarkets("BROOKLYN")
        queens = get_submarkets("QUEENS")
        bronx = get_submarkets("BRONX")
        staten_island = get_submarkets("STATEN_ISLAND")

        assert len(manhattan) >= 15, f"Expected >= 15 Manhattan submarkets, got {len(manhattan)}"
        assert len(brooklyn) >= 15, f"Expected >= 15 Brooklyn submarkets, got {len(brooklyn)}"
        assert len(queens) >= 10, f"Expected >= 10 Queens submarkets, got {len(queens)}"
        assert len(bronx) >= 8, f"Expected >= 8 Bronx submarkets, got {len(bronx)}"
        assert len(staten_island) >= 5, f"Expected >= 5 Staten Island submarkets, got {len(staten_island)}"

        total_borough_count = (
            len(manhattan) + len(brooklyn) + len(queens) + len(bronx) + len(staten_island)
        )
        assert total_borough_count == len(all_submarkets)

    def test_chicago_submarket_counts_and_divisions(self):
        """Verify 30+ total Chicago submarkets across all 6 divisions."""
        chicago_submarkets = get_all_submarkets("chicago")
        assert len(chicago_submarkets) >= 30, f"Expected >= 30 Chicago submarkets, found {len(chicago_submarkets)}"

        central = get_submarkets("chicago", "CENTRAL_DOWNTOWN")
        north = get_submarkets("chicago", "NORTH_SIDE")
        northwest = get_submarkets("chicago", "NORTHWEST_SIDE")
        south = get_submarkets("chicago", "SOUTH_SIDE")
        far_north = get_submarkets("chicago", "FAR_NORTH_SIDE")
        southwest = get_submarkets("chicago", "SOUTHWEST_SIDE")

        assert len(central) >= 5, f"Expected >= 5 Central Downtown submarkets, got {len(central)}"
        assert len(north) >= 5, f"Expected >= 5 North Side submarkets, got {len(north)}"
        assert len(northwest) >= 5, f"Expected >= 5 Northwest Side submarkets, got {len(northwest)}"
        assert len(south) >= 5, f"Expected >= 5 South Side submarkets, got {len(south)}"
        assert len(far_north) >= 4, f"Expected >= 4 Far North Side submarkets, got {len(far_north)}"
        assert len(southwest) >= 4, f"Expected >= 4 Southwest Side submarkets, got {len(southwest)}"

        total_div_count = (
            len(central) + len(north) + len(northwest) + len(south) + len(far_north) + len(southwest)
        )
        assert total_div_count == len(chicago_submarkets)

    def test_sf_submarket_counts_and_divisions(self):
        """Verify 35+ total San Francisco submarkets across all 5 divisions."""
        sf_submarkets = get_all_submarkets("san_francisco")
        assert len(sf_submarkets) >= 35, f"Expected >= 35 SF submarkets, found {len(sf_submarkets)}"

        core = get_submarkets("san_francisco", "SAN_FRANCISCO_CORE")
        east_bay = get_submarkets("san_francisco", "EAST_BAY")
        peninsula = get_submarkets("san_francisco", "PENINSULA")
        silicon_valley = get_submarkets("san_francisco", "SILICON_VALLEY_SOUTH_BAY")
        marin = get_submarkets("san_francisco", "MARIN_NORTH_BAY")

        assert len(core) >= 15, f"Expected >= 15 SF Core submarkets, got {len(core)}"
        assert len(east_bay) >= 8, f"Expected >= 8 East Bay submarkets, got {len(east_bay)}"
        assert len(peninsula) >= 5, f"Expected >= 5 Peninsula submarkets, got {len(peninsula)}"
        assert len(silicon_valley) >= 5, f"Expected >= 5 Silicon Valley submarkets, got {len(silicon_valley)}"
        assert len(marin) >= 4, f"Expected >= 4 Marin submarkets, got {len(marin)}"

        total_div_count = (
            len(core) + len(east_bay) + len(peninsula) + len(silicon_valley) + len(marin)
        )
        assert total_div_count == len(sf_submarkets)

    def test_nyc_submarket_meta_attributes(self):
        """Verify every NYC submarket entry contains complete and valid metadata."""
        for name, meta in get_all_submarkets("nyc").items():
            assert isinstance(meta, SubmarketMeta)
            assert meta.name == name
            assert meta.borough in ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN_ISLAND"]
            assert 40.48 <= meta.lat <= 40.93, f"Lat {meta.lat} out of range for {name}"
            assert -74.28 <= meta.lng <= -73.68, f"Lng {meta.lng} out of range for {name}"
            assert meta.zoom > 0
            assert meta.pitch >= 0
            assert meta.base_lims > 0
            assert meta.capex > 0
            assert meta.permit_vel > 0
            assert meta.shift_ratio > 0
            assert meta.sla > 0
            assert len(meta.description) > 10
            assert meta.city_id == "nyc"

    def test_chicago_submarket_meta_attributes(self):
        """Verify every Chicago submarket entry contains complete and valid metadata."""
        expected_divisions = [
            "CENTRAL_DOWNTOWN",
            "NORTH_SIDE",
            "NORTHWEST_SIDE",
            "SOUTH_SIDE",
            "FAR_NORTH_SIDE",
            "SOUTHWEST_SIDE",
        ]
        for name, meta in get_all_submarkets("chicago").items():
            assert isinstance(meta, SubmarketMeta)
            assert meta.name == name
            assert meta.borough in expected_divisions
            assert meta.division == meta.borough
            assert 41.64 <= meta.lat <= 42.03, f"Lat {meta.lat} out of range for {name}"
            assert -87.94 <= meta.lng <= -87.52, f"Lng {meta.lng} out of range for {name}"
            assert meta.zoom > 0
            assert meta.pitch >= 0
            assert meta.base_lims > 0
            assert meta.capex > 0
            assert meta.permit_vel > 0
            assert meta.shift_ratio > 0
            assert meta.sla > 0
            assert len(meta.description) > 10
            assert meta.city_id == "chicago"

    def test_sf_submarket_meta_attributes(self):
        """Verify every SF submarket entry contains complete and valid metadata."""
        expected_divisions = [
            "SAN_FRANCISCO_CORE",
            "EAST_BAY",
            "PENINSULA",
            "SILICON_VALLEY_SOUTH_BAY",
            "MARIN_NORTH_BAY",
        ]
        for name, meta in get_all_submarkets("san_francisco").items():
            assert isinstance(meta, SubmarketMeta)
            assert meta.name == name
            assert meta.borough in expected_divisions
            assert meta.division == meta.borough
            assert SF_METRO_BBOX["min_lat"] <= meta.lat <= SF_METRO_BBOX["max_lat"], f"Lat {meta.lat} out of range for {name}"
            assert SF_METRO_BBOX["min_lng"] <= meta.lng <= SF_METRO_BBOX["max_lng"], f"Lng {meta.lng} out of range for {name}"
            assert meta.zoom > 0
            assert meta.pitch >= 0
            assert meta.base_lims > 0
            assert meta.capex > 0
            assert meta.permit_vel > 0
            assert meta.shift_ratio > 0
            assert meta.sla > 0
            assert len(meta.description) > 10
            assert meta.city_id == "san_francisco"

    def test_filter_submarkets_by_borough_and_division(self):
        """Test filtering submarkets by borough/division with case-insensitivity."""
        # NYC
        manhattan = get_submarkets("manhattan")
        assert len(manhattan) > 0
        for sm in manhattan.values():
            assert sm.borough == "MANHATTAN"

        si_hyphen = get_submarkets("staten-island")
        si_space = get_submarkets("Staten Island")
        si_exact = get_submarkets("STATEN_ISLAND")
        assert len(si_hyphen) == len(si_exact)
        assert len(si_space) == len(si_exact)

        # Chicago
        central = get_submarkets(city_id="chicago", borough_or_division="central-downtown")
        assert len(central) > 0
        for sm in central.values():
            assert sm.borough == "CENTRAL_DOWNTOWN"

        nw = get_submarkets("chicago", "northwest_side")
        assert len(nw) > 0
        for sm in nw.values():
            assert sm.borough == "NORTHWEST_SIDE"

        # San Francisco
        sf_core = get_submarkets("san_francisco", "SAN_FRANCISCO_CORE")
        assert len(sf_core) > 0
        for sm in sf_core.values():
            assert sm.borough == "SAN_FRANCISCO_CORE"

        east_bay = get_submarkets("sf", "east-bay")
        assert len(east_bay) > 0
        for sm in east_bay.values():
            assert sm.borough == "EAST_BAY"

        sv = get_submarkets(city_id="san_francisco", borough_or_division="silicon_valley_south_bay")
        assert len(sv) > 0
        for sm in sv.values():
            assert sm.borough == "SILICON_VALLEY_SOUTH_BAY"

    def test_get_submarket_by_name_multi_city(self):
        """Test exact, case-insensitive, and multi-city submarket lookups."""
        # NYC lookups
        soho = get_submarket_by_name("SoHo")
        assert soho is not None
        assert soho.borough == "MANHATTAN"
        assert soho.city_id == "nyc"
        assert soho.lat == pytest.approx(40.7233, rel=1e-3)

        williamsburg = get_submarket_by_name("williamsburg")
        assert williamsburg is not None
        assert williamsburg.borough == "BROOKLYN"

        # Chicago lookups
        fulton = get_submarket_by_name("Fulton Market")
        assert fulton is not None
        assert fulton.borough == "CENTRAL_DOWNTOWN"
        assert fulton.city_id == "chicago"
        assert fulton.lat == pytest.approx(41.8867, rel=1e-3)

        logan = get_submarket_by_name("LOGAN SQUARE", city_id="chicago")
        assert logan is not None
        assert logan.borough == "NORTHWEST_SIDE"
        assert logan.city_id == "chicago"

        pilsen = get_submarket_by_name("pilsen")
        assert pilsen is not None
        assert pilsen.borough == "SOUTHWEST_SIDE"
        assert pilsen.city_id == "chicago"

        # San Francisco lookups
        soma = get_submarket_by_name("SoMa")
        assert soma is not None
        assert soma.borough == "SAN_FRANCISCO_CORE"
        assert soma.city_id == "san_francisco"
        assert soma.lat == pytest.approx(37.7785, rel=1e-3)

        mission = get_submarket_by_name("mission", city_id="san_francisco")
        assert mission is not None
        assert mission.borough == "SAN_FRANCISCO_CORE"

        rockridge = get_submarket_by_name("ROCKRIDGE")
        assert rockridge is not None
        assert rockridge.borough == "EAST_BAY"

        palo_alto = get_submarket_by_name("Palo Alto University Ave")
        assert palo_alto is not None
        assert palo_alto.borough == "SILICON_VALLEY_SOUTH_BAY"

        sausalito = get_submarket_by_name("sausalito")
        assert sausalito is not None
        assert sausalito.borough == "MARIN_NORTH_BAY"

        # Disambiguation: Chinatown exists in NYC and Chicago, Downtown in SF and Brooklyn/Chicago
        nyc_chinatown = get_submarket_by_name("Chinatown", city_id="nyc")
        chi_chinatown = get_submarket_by_name("Chinatown", city_id="chicago")
        assert nyc_chinatown is not None
        assert chi_chinatown is not None
        assert nyc_chinatown.borough == "MANHATTAN"
        assert nyc_chinatown.city_id == "nyc"
        assert chi_chinatown.borough == "SOUTH_SIDE"
        assert chi_chinatown.city_id == "chicago"
        assert nyc_chinatown.lat != chi_chinatown.lat

        sf_downtown = get_submarket_by_name("Downtown", city_id="san_francisco")
        assert sf_downtown is not None
        assert sf_downtown.borough == "SAN_FRANCISCO_CORE"
        assert sf_downtown.city_id == "san_francisco"

        # Non-existent
        assert get_submarket_by_name("NonExistentSubmarket") is None
        assert get_submarket_by_name("") is None

    def test_city_catalog(self):
        """Test the multi-city catalog metadata."""
        catalog = get_city_catalog()
        assert "nyc" in catalog
        assert "chicago" in catalog
        assert "san_francisco" in catalog

        nyc_meta = catalog["nyc"]
        assert nyc_meta["city_id"] == "nyc"
        assert nyc_meta["name"] == "New York City"
        assert nyc_meta["divisions_count"] == 5
        assert nyc_meta["submarkets_count"] >= 50

        chi_meta = catalog["chicago"]
        assert chi_meta["city_id"] == "chicago"
        assert chi_meta["name"] == "Chicago"
        assert chi_meta["divisions_count"] == 6
        assert chi_meta["submarkets_count"] >= 30

        sf_meta = catalog["san_francisco"]
        assert sf_meta["city_id"] == "san_francisco"
        assert sf_meta["name"] == "San Francisco Bay Area"
        assert sf_meta["divisions_count"] == 5
        assert sf_meta["submarkets_count"] >= 35

    def test_borough_and_division_catalogs(self):
        """Test NYC, Chicago, and SF division catalogs."""
        # NYC Borough catalog
        nyc_catalog = get_borough_catalog("nyc")
        expected_boroughs = {"MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN_ISLAND"}
        assert set(nyc_catalog.keys()) == expected_boroughs

        for b_name, b_data in nyc_catalog.items():
            assert b_data["name"] == b_name
            assert "center_lat" in b_data
            assert "center_lng" in b_data
            assert "zoom" in b_data
            assert "bbox" in b_data
            assert "submarkets" in b_data
            assert len(b_data["submarkets"]) == b_data["submarket_count"]
            assert b_data["submarket_count"] > 0

        # Chicago Division catalog
        chi_catalog = get_division_catalog("chicago")
        expected_divisions = {
            "CENTRAL_DOWNTOWN",
            "NORTH_SIDE",
            "NORTHWEST_SIDE",
            "SOUTH_SIDE",
            "FAR_NORTH_SIDE",
            "SOUTHWEST_SIDE",
        }
        assert set(chi_catalog.keys()) == expected_divisions

        for d_name, d_data in chi_catalog.items():
            assert d_data["name"] == d_name
            assert "center_lat" in d_data
            assert "center_lng" in d_data
            assert "zoom" in d_data
            assert "bbox" in d_data
            assert "submarkets" in d_data
            assert len(d_data["submarkets"]) == d_data["submarket_count"]
            assert d_data["submarket_count"] > 0

        # SF Division catalog
        sf_catalog = get_division_catalog("san_francisco")
        expected_sf_divisions = {
            "SAN_FRANCISCO_CORE",
            "EAST_BAY",
            "PENINSULA",
            "SILICON_VALLEY_SOUTH_BAY",
            "MARIN_NORTH_BAY",
        }
        assert set(sf_catalog.keys()) == expected_sf_divisions

        for d_name, d_data in sf_catalog.items():
            assert d_data["name"] == d_name
            assert "center_lat" in d_data
            assert "center_lng" in d_data
            assert "zoom" in d_data
            assert "bbox" in d_data
            assert "submarkets" in d_data
            assert len(d_data["submarkets"]) == d_data["submarket_count"]
            assert d_data["submarket_count"] > 0


class TestSpatialDistanceAndBoroughs:
    """Test suite for spatial distance calculation, nearest submarket, and division resolution."""

    def test_find_nearest_submarket_nyc(self, sample_nyc_coords):
        """Test nearest submarket identification across NYC boroughs."""
        soho_coord = sample_nyc_coords["soho"]
        nearest_name, dist_km = find_nearest_submarket(soho_coord["lat"], soho_coord["lng"], city_id="nyc")
        assert nearest_name == "SoHo"
        assert dist_km < 0.1

        wb_coord = sample_nyc_coords["williamsburg"]
        nearest_name, dist_km = find_nearest_submarket(wb_coord["lat"], wb_coord["lng"], city_id="nyc")
        assert nearest_name == "Williamsburg"
        assert dist_km < 0.1

        lic_coord = sample_nyc_coords["lic"]
        nearest_name, dist_km = find_nearest_submarket(lic_coord["lat"], lic_coord["lng"], city_id="nyc")
        assert nearest_name == "Long Island City"
        assert dist_km < 0.1

        mh_coord = sample_nyc_coords["mott_haven"]
        nearest_name, dist_km = find_nearest_submarket(mh_coord["lat"], mh_coord["lng"], city_id="nyc")
        assert nearest_name == "Mott Haven"
        assert dist_km < 0.1

        sg_coord = sample_nyc_coords["st_george"]
        nearest_name, dist_km = find_nearest_submarket(sg_coord["lat"], sg_coord["lng"], city_id="nyc")
        assert nearest_name == "St. George"
        assert dist_km < 0.1

    def test_find_nearest_submarket_chicago(self, sample_chicago_coords):
        """Test nearest submarket identification across Chicago divisions."""
        loop_coord = sample_chicago_coords["loop"]
        nearest_name, dist_km = find_nearest_submarket(loop_coord["lat"], loop_coord["lng"], city_id="chicago")
        assert nearest_name == "Loop"
        assert dist_km < 0.1

        fm_coord = sample_chicago_coords["fulton_market"]
        nearest_name, dist_km = find_nearest_submarket(fm_coord["lat"], fm_coord["lng"], city_id="chicago")
        assert nearest_name == "Fulton Market"
        assert dist_km < 0.1

        lp_coord = sample_chicago_coords["lincoln_park"]
        nearest_name, dist_km = find_nearest_submarket(lp_coord["lat"], lp_coord["lng"], city_id="chicago")
        assert nearest_name == "Lincoln Park"
        assert dist_km < 0.1

        wp_coord = sample_chicago_coords["wicker_park"]
        nearest_name, dist_km = find_nearest_submarket(wp_coord["lat"], wp_coord["lng"], city_id="chicago")
        assert nearest_name == "Wicker Park"
        assert dist_km < 0.1

        hp_coord = sample_chicago_coords["hyde_park"]
        nearest_name, dist_km = find_nearest_submarket(hp_coord["lat"], hp_coord["lng"], city_id="chicago")
        assert nearest_name == "Hyde Park"
        assert dist_km < 0.1

        pilsen_coord = sample_chicago_coords["pilsen"]
        nearest_name, dist_km = find_nearest_submarket(pilsen_coord["lat"], pilsen_coord["lng"], city_id="chicago")
        assert nearest_name == "Pilsen"
        assert dist_km < 0.1

    def test_find_nearest_submarket_sf(self, sample_sf_coords):
        """Test nearest submarket identification across SF divisions."""
        dt_coord = sample_sf_coords["downtown"]
        nearest_name, dist_km = find_nearest_submarket(dt_coord["lat"], dt_coord["lng"], city_id="san_francisco")
        assert nearest_name == "Downtown"
        assert dist_km < 0.1

        soma_coord = sample_sf_coords["soma"]
        nearest_name, dist_km = find_nearest_submarket(soma_coord["lat"], soma_coord["lng"], city_id="san_francisco")
        assert nearest_name == "SoMa"
        assert dist_km < 0.1

        oak_coord = sample_sf_coords["oakland_downtown"]
        nearest_name, dist_km = find_nearest_submarket(oak_coord["lat"], oak_coord["lng"], city_id="san_francisco")
        assert nearest_name == "Downtown Oakland"
        assert dist_km < 0.1

        pa_coord = sample_sf_coords["palo_alto"]
        nearest_name, dist_km = find_nearest_submarket(pa_coord["lat"], pa_coord["lng"], city_id="san_francisco")
        assert nearest_name == "Palo Alto University Ave"
        assert dist_km < 0.1

        sau_coord = sample_sf_coords["sausalito"]
        nearest_name, dist_km = find_nearest_submarket(sau_coord["lat"], sau_coord["lng"], city_id="san_francisco")
        assert nearest_name == "Sausalito"
        assert dist_km < 0.1

    def test_get_borough_and_division_for_coordinate(self, sample_nyc_coords, sample_chicago_coords, sample_sf_coords):
        """Test resolving borough/division name for coordinate points across NYC, Chicago, and SF."""
        # NYC
        assert get_borough_for_coordinate(sample_nyc_coords["soho"]["lat"], sample_nyc_coords["soho"]["lng"]) == "MANHATTAN"
        assert get_borough_for_coordinate(sample_nyc_coords["williamsburg"]["lat"], sample_nyc_coords["williamsburg"]["lng"]) == "BROOKLYN"
        assert get_borough_for_coordinate(sample_nyc_coords["lic"]["lat"], sample_nyc_coords["lic"]["lng"]) == "QUEENS"
        assert get_borough_for_coordinate(sample_nyc_coords["mott_haven"]["lat"], sample_nyc_coords["mott_haven"]["lng"]) == "BRONX"
        assert get_borough_for_coordinate(sample_nyc_coords["st_george"]["lat"], sample_nyc_coords["st_george"]["lng"]) == "STATEN_ISLAND"

        # Chicago via get_division_for_coordinate
        assert get_division_for_coordinate(sample_chicago_coords["loop"]["lat"], sample_chicago_coords["loop"]["lng"], city_id="chicago") == "CENTRAL_DOWNTOWN"
        assert get_division_for_coordinate(sample_chicago_coords["lincoln_park"]["lat"], sample_chicago_coords["lincoln_park"]["lng"], city_id="chicago") == "NORTH_SIDE"
        assert get_division_for_coordinate(sample_chicago_coords["wicker_park"]["lat"], sample_chicago_coords["wicker_park"]["lng"], city_id="chicago") == "NORTHWEST_SIDE"
        assert get_division_for_coordinate(sample_chicago_coords["rogers_park"]["lat"], sample_chicago_coords["rogers_park"]["lng"], city_id="chicago") == "FAR_NORTH_SIDE"
        assert get_division_for_coordinate(sample_chicago_coords["hyde_park"]["lat"], sample_chicago_coords["hyde_park"]["lng"], city_id="chicago") == "SOUTH_SIDE"
        assert get_division_for_coordinate(sample_chicago_coords["pilsen"]["lat"], sample_chicago_coords["pilsen"]["lng"], city_id="chicago") == "SOUTHWEST_SIDE"

        # San Francisco via get_division_for_coordinate
        assert get_division_for_coordinate(sample_sf_coords["downtown"]["lat"], sample_sf_coords["downtown"]["lng"], city_id="san_francisco") == "SAN_FRANCISCO_CORE"
        assert get_division_for_coordinate(sample_sf_coords["oakland_downtown"]["lat"], sample_sf_coords["oakland_downtown"]["lng"], city_id="san_francisco") == "EAST_BAY"
        assert get_division_for_coordinate(sample_sf_coords["san_mateo"]["lat"], sample_sf_coords["san_mateo"]["lng"], city_id="san_francisco") == "PENINSULA"
        assert get_division_for_coordinate(sample_sf_coords["palo_alto"]["lat"], sample_sf_coords["palo_alto"]["lng"], city_id="san_francisco") == "SILICON_VALLEY_SOUTH_BAY"
        assert get_division_for_coordinate(sample_sf_coords["sausalito"]["lat"], sample_sf_coords["sausalito"]["lng"], city_id="san_francisco") == "MARIN_NORTH_BAY"

        # Coordinates far outside bounds
        assert get_borough_for_coordinate(0.0, 0.0) is None
        assert get_division_for_coordinate(51.5074, -0.1278, city_id="chicago") is None  # London
        assert get_division_for_coordinate(34.0522, -118.2437, city_id="san_francisco") is None  # Los Angeles

    def test_get_city_for_coordinate(self, sample_nyc_coords, sample_chicago_coords, sample_sf_coords):
        """Test resolving city identifier ('nyc', 'chicago', or 'san_francisco') for coordinate points."""
        assert get_city_for_coordinate(sample_nyc_coords["soho"]["lat"], sample_nyc_coords["soho"]["lng"]) == "nyc"
        assert get_city_for_coordinate(sample_nyc_coords["williamsburg"]["lat"], sample_nyc_coords["williamsburg"]["lng"]) == "nyc"
        assert get_city_for_coordinate(sample_chicago_coords["loop"]["lat"], sample_chicago_coords["loop"]["lng"]) == "chicago"
        assert get_city_for_coordinate(sample_chicago_coords["fulton_market"]["lat"], sample_chicago_coords["fulton_market"]["lng"]) == "chicago"
        assert get_city_for_coordinate(sample_sf_coords["downtown"]["lat"], sample_sf_coords["downtown"]["lng"]) == "san_francisco"
        assert get_city_for_coordinate(sample_sf_coords["oakland_downtown"]["lat"], sample_sf_coords["oakland_downtown"]["lng"]) == "san_francisco"
        assert get_city_for_coordinate(sample_sf_coords["palo_alto"]["lat"], sample_sf_coords["palo_alto"]["lng"]) == "san_francisco"

        assert get_city_for_coordinate(0.0, 0.0) is None
        assert get_city_for_coordinate(34.0522, -118.2437) == "los_angeles"
        assert get_city_for_coordinate(25.7617, -80.1918) == "miami_dade"  # downtown Miami
        assert get_city_for_coordinate(51.5074, -0.1278) is None  # London

    def test_is_in_sf_metro(self, sample_sf_coords, sample_chicago_coords, sample_nyc_coords):
        """Test is_in_sf_metro, is_in_chicago_metro, and is_in_nyc_metro bounding checks."""
        assert is_in_sf_metro(sample_sf_coords["downtown"]["lat"], sample_sf_coords["downtown"]["lng"]) is True
        assert is_in_san_francisco_metro(sample_sf_coords["san_jose"]["lat"], sample_sf_coords["san_jose"]["lng"]) is True
        assert is_in_sf_metro(sample_nyc_coords["soho"]["lat"], sample_nyc_coords["soho"]["lng"]) is False
        assert is_in_sf_metro(sample_chicago_coords["loop"]["lat"], sample_chicago_coords["loop"]["lng"]) is False
        assert is_in_chicago_metro(sample_sf_coords["downtown"]["lat"], sample_sf_coords["downtown"]["lng"]) is False
        assert is_in_nyc_metro(sample_sf_coords["downtown"]["lat"], sample_sf_coords["downtown"]["lng"]) is False

    def test_get_borough_and_division_for_h3(self, sample_nyc_coords, sample_chicago_coords, sample_sf_coords):
        """Test resolving borough and division from Uber H3 indexes at various resolutions."""
        # NYC H3
        soho_h3_res9 = h3.latlng_to_cell(sample_nyc_coords["soho"]["lat"], sample_nyc_coords["soho"]["lng"], 9)
        soho_h3_res8 = h3.latlng_to_cell(sample_nyc_coords["soho"]["lat"], sample_nyc_coords["soho"]["lng"], 8)
        assert get_borough_for_h3(soho_h3_res9) == "MANHATTAN"
        assert get_borough_for_h3(soho_h3_res8) == "MANHATTAN"

        wb_h3 = h3.latlng_to_cell(sample_nyc_coords["williamsburg"]["lat"], sample_nyc_coords["williamsburg"]["lng"], 9)
        assert get_borough_for_h3(wb_h3) == "BROOKLYN"

        # Chicago H3
        loop_h3_res9 = h3.latlng_to_cell(sample_chicago_coords["loop"]["lat"], sample_chicago_coords["loop"]["lng"], 9)
        assert get_division_for_h3(loop_h3_res9, city_id="chicago") == "CENTRAL_DOWNTOWN"

        wp_h3 = h3.latlng_to_cell(sample_chicago_coords["wicker_park"]["lat"], sample_chicago_coords["wicker_park"]["lng"], 9)
        assert get_division_for_h3(wp_h3, city_id="chicago") == "NORTHWEST_SIDE"

        hp_h3 = h3.latlng_to_cell(sample_chicago_coords["hyde_park"]["lat"], sample_chicago_coords["hyde_park"]["lng"], 9)
        assert get_division_for_h3(hp_h3, city_id="chicago") == "SOUTH_SIDE"

        # SF H3
        soma_h3_res9 = h3.latlng_to_cell(sample_sf_coords["soma"]["lat"], sample_sf_coords["soma"]["lng"], 9)
        assert get_division_for_h3(soma_h3_res9, city_id="san_francisco") == "SAN_FRANCISCO_CORE"

        oak_h3 = h3.latlng_to_cell(sample_sf_coords["oakland_downtown"]["lat"], sample_sf_coords["oakland_downtown"]["lng"], 9)
        assert get_division_for_h3(oak_h3, city_id="san_francisco") == "EAST_BAY"

        pa_h3 = h3.latlng_to_cell(sample_sf_coords["palo_alto"]["lat"], sample_sf_coords["palo_alto"]["lng"], 9)
        assert get_division_for_h3(pa_h3, city_id="san_francisco") == "SILICON_VALLEY_SOUTH_BAY"

        # Invalid H3 cell index
        assert get_borough_for_h3("invalid_h3_cell") is None
        assert get_division_for_h3("invalid_h3_cell", city_id="chicago") is None
        assert get_division_for_h3("invalid_h3_cell", city_id="san_francisco") is None

    def test_registry_invariant_and_namespacing(self):
        """Verify registry invariant: no key collision when merging all cities, keys are properly namespaced."""
        from src.spatial.city_registry import REGISTRY
        registered_ids = {cid.value for cid in REGISTRY}
        all_subs = get_all_submarkets("all")
        total_expected = sum(len(reg.submarkets) for reg in REGISTRY.values())
        assert len(all_subs) == total_expected

        # All keys must be namespaced city_id:name
        for k in all_subs:
            assert ":" in k, f"Key {k} is not namespaced"
            cid, name = k.split(":", 1)
            assert cid in registered_ids

        # Chinatown and Financial District exist across cities without collision
        assert "nyc:Chinatown" in all_subs
        assert "chicago:Chinatown" in all_subs
        assert "nyc:Financial District" in all_subs
        assert "san_francisco:Financial District" in all_subs

    def test_ambiguous_submarket_lookup(self):
        """Verify get_submarket_by_name handles ambiguous, namespaced, and city-filtered queries."""
        # Unqualified ambiguous name raises ValueError
        with pytest.raises(ValueError, match="Ambiguous submarket name"):
            get_submarket_by_name("Chinatown")

        with pytest.raises(ValueError, match="Ambiguous submarket name"):
            get_submarket_by_name("Financial District")

        # Qualified by prefix
        nyc_ct = get_submarket_by_name("nyc:Chinatown")
        assert nyc_ct.name == "Chinatown"
        assert nyc_ct.borough == "MANHATTAN"

        chi_ct = get_submarket_by_name("chicago:Chinatown")
        assert chi_ct.name == "Chinatown"
        assert chi_ct.borough == "SOUTH_SIDE"

        # Qualified by city_id argument
        nyc_fd = get_submarket_by_name("Financial District", city_id="nyc")
        assert nyc_fd.borough == "MANHATTAN"

        sf_fd = get_submarket_by_name("Financial District", city_id="san_francisco")
        assert sf_fd.borough == "SAN_FRANCISCO_CORE"

    def test_bay_area_snapping_distance_cap_and_coverage(self):
        """Verify Bay Area regional submarkets resolve locally and do NOT snap across the Bay."""
        # Fremont (37.5485, -121.9886) -> local submarket, NOT Palo Alto
        fremont_sub, dist = find_nearest_submarket(37.5485, -121.9886, city_id="san_francisco")
        assert fremont_sub is not None
        assert fremont_sub == "Fremont Downtown"
        assert dist < 1.0
        assert get_division_for_coordinate(37.5485, -121.9886, city_id="san_francisco") == "EAST_BAY"

        # Walnut Creek (37.9101, -122.0652) -> local submarket, NOT Rockridge
        wc_sub, dist = find_nearest_submarket(37.9101, -122.0652, city_id="san_francisco")
        assert wc_sub is not None
        assert wc_sub == "Walnut Creek Downtown"
        assert dist < 1.0
        assert get_division_for_coordinate(37.9101, -122.0652, city_id="san_francisco") == "EAST_BAY"

        # Concord (37.9780, -122.0311) -> local submarket, NOT Berkeley
        concord_sub, dist = find_nearest_submarket(37.9780, -122.0311, city_id="san_francisco")
        assert concord_sub is not None
        assert concord_sub == "Concord Downtown"
        assert dist < 1.0
        assert get_division_for_coordinate(37.9780, -122.0311, city_id="san_francisco") == "EAST_BAY"

        # Livermore (37.6819, -121.7680) -> local submarket, NOT San Jose
        livermore_sub, dist = find_nearest_submarket(37.6819, -121.7680, city_id="san_francisco")
        assert livermore_sub is not None
        assert livermore_sub == "Livermore Downtown"
        assert dist < 1.0
        assert get_division_for_coordinate(37.6819, -121.7680, city_id="san_francisco") == "EAST_BAY"

        # Far away coordinate (Sacramento: 38.5816, -121.4944) exceeds 25.0 km cap
        sac_sub, dist = find_nearest_submarket(38.5816, -121.4944, city_id="san_francisco")
        assert sac_sub is None
        assert dist > 25.0
