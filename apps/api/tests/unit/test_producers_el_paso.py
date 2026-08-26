"""Contract tests for El Paso, TX 311 leaf artifacts.

These tests run WITHOUT requiring El Paso's spine registration (REGISTRY entry,
aliases, dashboard wiring). They validate the leaf-only deliverables:

  * ``src/spatial/cities/el_paso.py`` geometry + submarket/division consistency
  * ``src/producers/field_maps_el_paso.py`` FIELD_MAP, exercised through the
    shared ``first_mapped`` helper and the real 311 producer (with the field
    map injected so no registry lookup is needed).

Spine registration is verified separately by the interlock gate once the
interlock is held.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_el_paso import FIELD_MAP
from src.spatial.cities.el_paso import (
    EL_PASO_DIVISION_BBOXES,
    EL_PASO_DIVISIONS,
    EL_PASO_METRO_BBOX,
    EL_PASO_SUBMARKETS,
    is_in_el_paso_metro,
)

# A realistic Accela/Cityworks 311 row shaped as El Paso publishes it.
SAMPLE_ROW = {
    "OBJECTID": 68351,
    "id": 81132,
    "request_category": "Code Enforcement",
    "request_type": "Noise Complaint",
    "status": "Submitted",
    "address": "140 W CASTELLANO, EL PASO, TX, 79912",
    "created_at": "2026-08-25T04:45:43+00:00",
    "request_id": "ENEC26-32064",
    "district": "8",
    "latitude": 31.807431000313844,
    "longitude": -106.51260599993472,
}


def test_el_paso_geometry_is_self_consistent():
    assert is_in_el_paso_metro(31.7619, -106.4850)
    assert is_in_el_paso_metro(31.8074, -106.5126)
    assert not is_in_el_paso_metro(40.7128, -74.0060)
    assert not is_in_el_paso_metro(None, None)

    # Every division bbox nests inside the metro bbox.
    for name, bbox in EL_PASO_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= EL_PASO_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= EL_PASO_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= EL_PASO_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= EL_PASO_METRO_BBOX["max_lng"], name

    # Every submarket coordinate nests inside its division bbox.
    for sm in EL_PASO_SUBMARKETS.values():
        div = EL_PASO_DIVISION_BBOXES[sm.borough]
        assert div["min_lat"] <= sm.lat <= div["max_lat"], sm.name
        assert div["min_lng"] <= sm.lng <= div["max_lng"], sm.name

    # Division submarket membership round-trips.
    claimed = [name for div in EL_PASO_DIVISIONS.values() for name in div.submarkets]
    assert sorted(claimed) == sorted(EL_PASO_SUBMARKETS)
    assert {meta.city_id for meta in EL_PASO_SUBMARKETS.values()} == {"el_paso"}


def test_el_paso_field_map_extracts_sample_row():
    assert first_mapped(SAMPLE_ROW, FIELD_MAP, "incident_id") == 81132
    assert (
        first_mapped(SAMPLE_ROW, FIELD_MAP, "created_date")
        == "2026-08-25T04:45:43+00:00"
    )
    assert first_mapped(SAMPLE_ROW, FIELD_MAP, "complaint_type") == "Noise Complaint"
    assert first_mapped(SAMPLE_ROW, FIELD_MAP, "incident_address") == SAMPLE_ROW["address"]
    assert first_mapped(SAMPLE_ROW, FIELD_MAP, "borough") == "8"
    assert first_mapped(SAMPLE_ROW, FIELD_MAP, "status") == "Submitted"


@pytest.fixture
def producer():
    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        from src.producers.complaints_311_producer import Complaints311Producer

        yield Complaints311Producer()


def test_el_paso_producer_parses_with_field_map(producer):
    # Inject the leaf field map so the producer needs no spine registration.
    with patch(
        "src.producers.field_maps.resolve_field_map", return_value=FIELD_MAP
    ):
        event = producer.parse_socrata_row(SAMPLE_ROW, city_id="el_paso")
    assert event is not None
    assert event.city_id == "el_paso"
    assert event.incident_id == "81132"
    assert event.complaint_type == "Noise Complaint"
    assert event.status == "Submitted"
    assert event.incident_address == SAMPLE_ROW["address"]
    # Producer resolves borough from coordinates; the field-map `district`
    # value lands in source_neighborhood.
    assert event.borough == "EL_PASO_CORE"
    assert event.source_neighborhood == "8"
    assert event.latitude == pytest.approx(31.807431000313844)
    assert event.longitude == pytest.approx(-106.51260599993472)
