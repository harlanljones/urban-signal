"""Unit tests for TIGER/Line block group geometry client and parser (US-438)."""

from shapely.geometry import Polygon

from src.spatial.tiger_client import (
    parse_tiger_block_groups_from_geojson,
    tiger_block_group_url,
)


def test_tiger_block_group_url():
    url = tiger_block_group_url(year=2023, state_fips="06")
    assert url == "https://www2.census.gov/geo/tiger/TIGER2023/BG/tl_2023_06_bg.zip"


def test_parse_tiger_block_groups_from_geojson_dict():
    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "GEOID": "060750101001",
                    "COUNTYFP": "075",
                    "STATEFP": "06",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-122.42, 37.77],
                            [-122.40, 37.77],
                            [-122.40, 37.79],
                            [-122.42, 37.79],
                            [-122.42, 37.77],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "GEOID": "060010101001",
                    "COUNTYFP": "001",
                    "STATEFP": "06",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-122.25, 37.80],
                            [-122.23, 37.80],
                            [-122.23, 37.82],
                            [-122.25, 37.82],
                            [-122.25, 37.80],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "GEOID": "060370101001",  # Los Angeles (not Bay Area)
                    "COUNTYFP": "037",
                    "STATEFP": "06",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-118.25, 34.05],
                            [-118.23, 34.05],
                            [-118.23, 34.07],
                            [-118.25, 34.07],
                            [-118.25, 34.05],
                        ]
                    ],
                },
            },
        ],
    }

    # Filter for SF (075) and Alameda (001)
    geoms = parse_tiger_block_groups_from_geojson(
        geojson_data, county_fips=["075", "001"]
    )
    assert len(geoms) == 2
    assert "060750101001" in geoms
    assert "060010101001" in geoms
    assert "060370101001" not in geoms
    assert isinstance(geoms["060750101001"], Polygon)
    assert geoms["060750101001"].is_valid
