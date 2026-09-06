"""Unit tests for Census ACS variable definitions and Bay Area catalog (US-438)."""

from src.spatial.acs_variables import (
    ACS_DASYMETRIC_VARIABLES,
    BAY_AREA_COUNTIES,
    BAY_AREA_COUNTY_GEOIDS,
    VariableType,
    get_required_acs_variable_codes,
)


def test_bay_area_counties_count():
    assert len(BAY_AREA_COUNTIES) == 9
    assert "075" in BAY_AREA_COUNTIES  # San Francisco
    assert "001" in BAY_AREA_COUNTIES  # Alameda
    assert "085" in BAY_AREA_COUNTIES  # Santa Clara
    assert len(BAY_AREA_COUNTY_GEOIDS) == 9
    assert "06075" in BAY_AREA_COUNTY_GEOIDS


def test_required_variables_catalog():
    # Intensive variables
    assert "median_household_income" in ACS_DASYMETRIC_VARIABLES
    assert ACS_DASYMETRIC_VARIABLES["median_household_income"].estimate_var == "B19013_001E"
    assert ACS_DASYMETRIC_VARIABLES["median_household_income"].moe_var == "B19013_001M"
    assert ACS_DASYMETRIC_VARIABLES["median_household_income"].var_type == VariableType.INTENSIVE

    assert "median_home_value" in ACS_DASYMETRIC_VARIABLES
    assert ACS_DASYMETRIC_VARIABLES["median_home_value"].estimate_var == "B25077_001E"
    assert ACS_DASYMETRIC_VARIABLES["median_home_value"].var_type == VariableType.INTENSIVE

    assert "median_gross_rent" in ACS_DASYMETRIC_VARIABLES
    assert ACS_DASYMETRIC_VARIABLES["median_gross_rent"].estimate_var == "B25064_001E"
    assert ACS_DASYMETRIC_VARIABLES["median_gross_rent"].var_type == VariableType.INTENSIVE

    # Extensive variables: Population
    assert "total_population" in ACS_DASYMETRIC_VARIABLES
    assert ACS_DASYMETRIC_VARIABLES["total_population"].estimate_var == "B01003_001E"
    assert ACS_DASYMETRIC_VARIABLES["total_population"].var_type == VariableType.EXTENSIVE

    # Extensive variables: Housing Units (B25002_001E - 003E)
    assert "housing_units_total" in ACS_DASYMETRIC_VARIABLES
    assert ACS_DASYMETRIC_VARIABLES["housing_units_total"].estimate_var == "B25002_001E"
    assert ACS_DASYMETRIC_VARIABLES["housing_units_total"].var_type == VariableType.EXTENSIVE

    assert "housing_units_occupied" in ACS_DASYMETRIC_VARIABLES
    assert ACS_DASYMETRIC_VARIABLES["housing_units_occupied"].estimate_var == "B25002_002E"

    assert "housing_units_vacant" in ACS_DASYMETRIC_VARIABLES
    assert ACS_DASYMETRIC_VARIABLES["housing_units_vacant"].estimate_var == "B25002_003E"

    # Extensive variables: Commute (B08301_001E - 021E)
    assert "commute_total" in ACS_DASYMETRIC_VARIABLES
    assert ACS_DASYMETRIC_VARIABLES["commute_total"].estimate_var == "B08301_001E"
    assert "commute_worked_from_home" in ACS_DASYMETRIC_VARIABLES
    assert ACS_DASYMETRIC_VARIABLES["commute_worked_from_home"].estimate_var == "B08301_021E"


def test_get_required_acs_variable_codes():
    codes = get_required_acs_variable_codes()
    assert len(codes) > 50
    assert "B19013_001E" in codes
    assert "B19013_001M" in codes
    assert "B01003_001E" in codes
    assert "B01003_001M" in codes
    assert "B08301_021E" in codes
    assert "B08301_021M" in codes
