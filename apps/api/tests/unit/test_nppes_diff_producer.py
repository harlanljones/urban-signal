"""Focused, network-free contracts for the US-374 NPPES leaf producer."""

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from src.producers.nppes_diff_producer import (
    InMemoryNppesStateStore,
    NppesDiffProducer,
    classify_taxonomy,
    practice_address,
)


class FakeProducer:
    def __init__(self):
        self.dlq = []

    def route_to_dlq(self, *args):
        self.dlq.append(args)


def row(**overrides):
    value = {
        "NPI": "1234567890",
        "Provider Organization Name (Legal Business Name)": "Neighborhood Clinic",
        "Provider Business Practice Location Address First Line": "100 Main St",
        "Provider Business Practice Location Address City Name": "New York",
        "Provider Business Practice Location Address State Name": "NY",
        "Provider Business Practice Location Address Postal Code": "10001",
        "Provider Enumeration Date": "01/02/2026",
        "Healthcare Provider Taxonomy Code_1": "207Q00000X",
        "Healthcare Provider Primary Taxonomy Switch_1": "Y",
    }
    value.update(overrides)
    return value


def producer(**kwargs):
    return NppesDiffProducer(producer=FakeProducer(), **kwargs)


def test_practice_address_excludes_mailing_address_and_normalizes():
    assert practice_address(row(**{"Provider Business Mailing Address First Line": "PO Box 9"})) == (
        "100 MAIN ST NEW YORK NY 10001"
    )


def test_primary_taxonomy_excludes_dme_supplier_family():
    assert classify_taxonomy(row(**{"Healthcare Provider Taxonomy Code_1": "332B00000X"})) is None


def test_primary_dme_taxonomy_falls_through_to_another_clinical_taxonomy():
    assert classify_taxonomy(
        row(
            **{
                "Healthcare Provider Taxonomy Code_1": "332B00000X",
                "Healthcare Provider Taxonomy Code_2": "207Q00000X",
                "Healthcare Provider Primary Taxonomy Switch_2": "Y",
            }
        )
    ) == "207Q00000X"


def test_new_provider_uses_zip_centroid_without_geocoding():
    calls = []
    p = producer(
    )
    centroids = {"10001": (40.75, -73.99)}
    events = p.diff_rows(
        [row()],
        InMemoryNppesStateStore(),
        geocoder=lambda address: calls.append(address),
        zip_centroids=centroids,
        metro_bboxes={"nyc": {"min_lat": 40.0, "max_lat": 41.0, "min_lng": -75.0, "max_lng": -73.0}},
    )
    assert len(events) == 1
    assert events[0].license_id.startswith("1234567890:")
    assert events[0].city_id == "nyc"
    assert calls == []


def test_relocation_emits_close_and_open_with_composite_ids():
    p = producer()
    state = InMemoryNppesStateStore()
    bbox = {"nyc": {"min_lat": 40.0, "max_lat": 41.0, "min_lng": -75.0, "max_lng": -73.0}}
    geocoder = lambda address: (40.75, -73.99) if "100 MAIN" in address else (40.76, -73.98)
    p.diff_rows([row()], state, geocoder=geocoder, metro_bboxes=bbox)
    events = p.diff_rows(
        [row(**{"Provider Business Practice Location Address First Line": "200 5th Ave"})],
        state,
        geocoder=geocoder,
        metro_bboxes=bbox,
    )
    assert [event.license_status for event in events] == ["INACTIVE", "ACTIVE"]
    assert len({event.license_id for event in events}) == 2


def test_relocation_out_of_metro_closes_previous_metro_license():
    p = producer()
    state = InMemoryNppesStateStore()
    bbox = {"nyc": {"min_lat": 40.0, "max_lat": 41.0, "min_lng": -75.0, "max_lng": -73.0}}
    geocoder = lambda address: (40.75, -73.99) if "100 MAIN" in address else (34.05, -118.25)
    p.diff_rows([row()], state, geocoder=geocoder, metro_bboxes=bbox)

    events = p.diff_rows(
        [row(**{"Provider Business Practice Location Address First Line": "200 Sunset Blvd"})],
        state,
        geocoder=geocoder,
        metro_bboxes=bbox,
    )

    assert [(event.city_id, event.license_status) for event in events] == [("nyc", "INACTIVE")]


def test_weekly_zip_reader_decodes_csv_member():
    payload = BytesIO()
    with ZipFile(payload, "w", ZIP_DEFLATED) as archive:
        archive.writestr("npidata_20260824-20260830.csv", "NPI,foo\n123,bar\n")
    rows = NppesDiffProducer.read_weekly_zip(payload.getvalue())
    assert rows == [{"NPI": "123", "foo": "bar"}]
