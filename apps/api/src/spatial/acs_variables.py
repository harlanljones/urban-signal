"""Census ACS variable definitions, catalog, and Bay Area constants (US-438).

Defines the intensive and extensive Census ACS 5-year variables required for
the 9-county Bay Area dasymetric interpolation pipeline:
- Intensive (medians): income, home value, gross rent
- Extensive (counts): total population, housing units (total, occupied, vacant),
  means of transportation to work (21 sub-categories)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum


class VariableType(str, Enum):
    """Aggregation type for dasymetric interpolation."""

    EXTENSIVE = "extensive"  # Counts/sums (population, housing units, workers)
    INTENSIVE = "intensive"  # Medians/rates/densities (median income, rent, home value)


@dataclass(frozen=True)
class ACSVariableSpec:
    """Specification of an ACS variable to ingest and interpolate."""

    name: str
    estimate_var: str
    moe_var: str
    var_type: VariableType
    description: str
    table_id: str


# 9 Bay Area Counties: 3-digit county FIPS -> County Name (State FIPS 06)
BAY_AREA_COUNTIES: dict[str, str] = {
    "001": "Alameda County",
    "013": "Contra Costa County",
    "041": "Marin County",
    "055": "Napa County",
    "075": "San Francisco County",
    "081": "San Mateo County",
    "085": "Santa Clara County",
    "095": "Solano County",
    "097": "Sonoma County",
}

# 5-digit GEOID prefix mapping
BAY_AREA_COUNTY_GEOIDS: list[str] = [f"06{cf}" for cf in sorted(BAY_AREA_COUNTIES.keys())]

# Complete catalog of US-438 ACS variables
ACS_DASYMETRIC_VARIABLES: dict[str, ACSVariableSpec] = {
    # Intensive variables: Medians
    "median_household_income": ACSVariableSpec(
        name="median_household_income",
        estimate_var="B19013_001E",
        moe_var="B19013_001M",
        var_type=VariableType.INTENSIVE,
        description="Median Household Income in the past 12 months (in inflation-adjusted dollars)",
        table_id="B19013",
    ),
    "median_home_value": ACSVariableSpec(
        name="median_home_value",
        estimate_var="B25077_001E",
        moe_var="B25077_001M",
        var_type=VariableType.INTENSIVE,
        description="Median Value of Owner-Occupied Housing Units",
        table_id="B25077",
    ),
    "median_gross_rent": ACSVariableSpec(
        name="median_gross_rent",
        estimate_var="B25064_001E",
        moe_var="B25064_001M",
        var_type=VariableType.INTENSIVE,
        description="Median Gross Rent (dollars)",
        table_id="B25064",
    ),
    # Extensive variables: Population & Housing Units
    "total_population": ACSVariableSpec(
        name="total_population",
        estimate_var="B01003_001E",
        moe_var="B01003_001M",
        var_type=VariableType.EXTENSIVE,
        description="Total Population",
        table_id="B01003",
    ),
    "housing_units_total": ACSVariableSpec(
        name="housing_units_total",
        estimate_var="B25002_001E",
        moe_var="B25002_001M",
        var_type=VariableType.EXTENSIVE,
        description="Total Housing Units (Occupancy Status)",
        table_id="B25002",
    ),
    "housing_units_occupied": ACSVariableSpec(
        name="housing_units_occupied",
        estimate_var="B25002_002E",
        moe_var="B25002_002M",
        var_type=VariableType.EXTENSIVE,
        description="Occupied Housing Units",
        table_id="B25002",
    ),
    "housing_units_vacant": ACSVariableSpec(
        name="housing_units_vacant",
        estimate_var="B25002_003E",
        moe_var="B25002_003M",
        var_type=VariableType.EXTENSIVE,
        description="Vacant Housing Units",
        table_id="B25002",
    ),
    # Extensive variables: Means of Transportation to Work (B08301_001E through B08301_021E)
    "commute_total": ACSVariableSpec(
        name="commute_total",
        estimate_var="B08301_001E",
        moe_var="B08301_001M",
        var_type=VariableType.EXTENSIVE,
        description="Total Workers 16 Years and Over (Means of Transportation)",
        table_id="B08301",
    ),
    "commute_car_truck_van_total": ACSVariableSpec(
        name="commute_car_truck_van_total",
        estimate_var="B08301_002E",
        moe_var="B08301_002M",
        var_type=VariableType.EXTENSIVE,
        description="Car, truck, or van",
        table_id="B08301",
    ),
    "commute_drove_alone": ACSVariableSpec(
        name="commute_drove_alone",
        estimate_var="B08301_003E",
        moe_var="B08301_003M",
        var_type=VariableType.EXTENSIVE,
        description="Drove alone",
        table_id="B08301",
    ),
    "commute_carpooled_total": ACSVariableSpec(
        name="commute_carpooled_total",
        estimate_var="B08301_004E",
        moe_var="B08301_004M",
        var_type=VariableType.EXTENSIVE,
        description="Carpooled",
        table_id="B08301",
    ),
    "commute_carpooled_2person": ACSVariableSpec(
        name="commute_carpooled_2person",
        estimate_var="B08301_005E",
        moe_var="B08301_005M",
        var_type=VariableType.EXTENSIVE,
        description="In 2-person carpool",
        table_id="B08301",
    ),
    "commute_carpooled_3person": ACSVariableSpec(
        name="commute_carpooled_3person",
        estimate_var="B08301_006E",
        moe_var="B08301_006M",
        var_type=VariableType.EXTENSIVE,
        description="In 3-person carpool",
        table_id="B08301",
    ),
    "commute_carpooled_4person": ACSVariableSpec(
        name="commute_carpooled_4person",
        estimate_var="B08301_007E",
        moe_var="B08301_007M",
        var_type=VariableType.EXTENSIVE,
        description="In 4-person carpool",
        table_id="B08301",
    ),
    "commute_carpooled_5_6person": ACSVariableSpec(
        name="commute_carpooled_5_6person",
        estimate_var="B08301_008E",
        moe_var="B08301_008M",
        var_type=VariableType.EXTENSIVE,
        description="In 5- or 6-person carpool",
        table_id="B08301",
    ),
    "commute_carpooled_7plus_person": ACSVariableSpec(
        name="commute_carpooled_7plus_person",
        estimate_var="B08301_009E",
        moe_var="B08301_009M",
        var_type=VariableType.EXTENSIVE,
        description="In 7-or-more-person carpool",
        table_id="B08301",
    ),
    "commute_public_transit_total": ACSVariableSpec(
        name="commute_public_transit_total",
        estimate_var="B08301_010E",
        moe_var="B08301_010M",
        var_type=VariableType.EXTENSIVE,
        description="Public transportation (excluding taxicab)",
        table_id="B08301",
    ),
    "commute_bus": ACSVariableSpec(
        name="commute_bus",
        estimate_var="B08301_011E",
        moe_var="B08301_011M",
        var_type=VariableType.EXTENSIVE,
        description="Bus",
        table_id="B08301",
    ),
    "commute_subway": ACSVariableSpec(
        name="commute_subway",
        estimate_var="B08301_012E",
        moe_var="B08301_012M",
        var_type=VariableType.EXTENSIVE,
        description="Subway or elevated rail",
        table_id="B08301",
    ),
    "commute_railroad": ACSVariableSpec(
        name="commute_railroad",
        estimate_var="B08301_013E",
        moe_var="B08301_013M",
        var_type=VariableType.EXTENSIVE,
        description="Long-distance train or commuter rail",
        table_id="B08301",
    ),
    "commute_streetcar": ACSVariableSpec(
        name="commute_streetcar",
        estimate_var="B08301_014E",
        moe_var="B08301_014M",
        var_type=VariableType.EXTENSIVE,
        description="Light rail, streetcar, or trolley",
        table_id="B08301",
    ),
    "commute_ferryboat": ACSVariableSpec(
        name="commute_ferryboat",
        estimate_var="B08301_015E",
        moe_var="B08301_015M",
        var_type=VariableType.EXTENSIVE,
        description="Ferryboat",
        table_id="B08301",
    ),
    "commute_taxicab": ACSVariableSpec(
        name="commute_taxicab",
        estimate_var="B08301_016E",
        moe_var="B08301_016M",
        var_type=VariableType.EXTENSIVE,
        description="Taxicab",
        table_id="B08301",
    ),
    "commute_motorcycle": ACSVariableSpec(
        name="commute_motorcycle",
        estimate_var="B08301_017E",
        moe_var="B08301_017M",
        var_type=VariableType.EXTENSIVE,
        description="Motorcycle",
        table_id="B08301",
    ),
    "commute_bicycle": ACSVariableSpec(
        name="commute_bicycle",
        estimate_var="B08301_018E",
        moe_var="B08301_018M",
        var_type=VariableType.EXTENSIVE,
        description="Bicycle",
        table_id="B08301",
    ),
    "commute_walked": ACSVariableSpec(
        name="commute_walked",
        estimate_var="B08301_019E",
        moe_var="B08301_019M",
        var_type=VariableType.EXTENSIVE,
        description="Walked",
        table_id="B08301",
    ),
    "commute_other_means": ACSVariableSpec(
        name="commute_other_means",
        estimate_var="B08301_020E",
        moe_var="B08301_020M",
        var_type=VariableType.EXTENSIVE,
        description="Other means",
        table_id="B08301",
    ),
    "commute_worked_from_home": ACSVariableSpec(
        name="commute_worked_from_home",
        estimate_var="B08301_021E",
        moe_var="B08301_021M",
        var_type=VariableType.EXTENSIVE,
        description="Worked from home",
        table_id="B08301",
    ),
}


def get_required_acs_variable_codes(
    variables: Mapping[str, ACSVariableSpec] | None = None,
) -> list[str]:
    """Return all estimate and MOE variable codes needed for Census API queries."""
    catalog = variables or ACS_DASYMETRIC_VARIABLES
    codes: set[str] = set()
    for spec in catalog.values():
        codes.add(spec.estimate_var)
        codes.add(spec.moe_var)
    return sorted(codes)
