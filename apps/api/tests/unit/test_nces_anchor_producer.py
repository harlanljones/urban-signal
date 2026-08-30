"""Unit tests for the US-375 NCES anchor-institution flow."""

import io
import zipfile
from unittest.mock import MagicMock

import pytest

from src.producers.anchor_events_spec import (
    ANCHOR_TOPIC,
    CCD_STATUS_EVENT_TYPE,
    AnchorInstitutionEvent,
)
from src.producers.nces_anchor_producer import NcesAnchorProducer
from src.producers.nces_ccd_client import EDGE_LAYOUT


@pytest.fixture(scope="module")
def edge_zip_payload():
    """In-memory EDGE-style zip with 3 geocoded schools."""
    edge_rows = [
        {"ncessch": "480001000001", "school_name": "New School", "address": "1 SCHOOL LN",
         "city": "DALLAS", "state": "TX", "zip": "75201", "latitude": "32.7767", "longitude": "-96.797"},
        {"ncessch": "480001000002", "school_name": "Old School", "address": "2 SCHOOL LN",
         "city": "DALLAS", "state": "TX", "zip": "75201", "latitude": "32.7800", "longitude": "-96.800"},
        {"ncessch": "480001000003", "school_name": "Ghost School", "address": "3 SCHOOL LN",
         "city": "DALLAS", "state": "TX", "zip": "75201", "latitude": "32.7850", "longitude": "-96.805"},
    ]
    lines = "\n".join(
        "|".join((r["ncessch"], "0100005", r["school_name"], "01", r["address"], r["city"],
                  r["state"], r["zip"], "01", "01095", "County", "01",
                  r["latitude"], r["longitude"], "10700", "Metro", "2", "290",
                  "Metro, ST", "0104", "01026", "01009", "2023-2024"))
        for r in edge_rows
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("EDGE_GEOCODE_PUBLICSCH_2324.TXT", lines)
    return buf.getvalue()


def _mock_client(ccd_batches, edge_payload):
    """Build a MagicMock client that returns the provided CCD batches and EDGE file."""
    client = MagicMock()
    client.school_rows.return_value = iter(ccd_batches)
    # Use function for side_effect so keyword args work.
    client.geocode_rows.side_effect = lambda school_year="", fetched=None: _parse_edge(fetched or edge_payload)
    return client


def _parse_edge(payload):
    archive = zipfile.ZipFile(io.BytesIO(payload))
    member = [n for n in archive.namelist() if n.lower().endswith(".txt")][0]
    rows = []
    for line in archive.read(member).decode().splitlines():
        fields = line.split("|")
        rows.append({name: fields[i].strip() for name, i in EDGE_LAYOUT.items() if i < len(fields)})
    return iter([rows])


def _ccd_row(ncessch, name, status, effective="09/01/2023", recon="No", charter="No"):
    """One CCD row with pre-normalized (lowercase underscore) keys."""
    return {
        "sch_name": name, "ncessch": ncessch, "mstreet1": "1 SCHOOL LN",
        "lcity": "DALLAS", "lstate": "TX", "lzip": "75201",
        "updated_status": status, "updated_status_text": status,
        "effective_date": effective, "recon_status": recon, "charter_text": charter,
    }


def _producer(ccd_batches, edge_payload, crosswalk=True):
    client = _mock_client(ccd_batches, edge_payload)
    indexer = MagicMock()
    indexer.get_multi_res_hierarchy.return_value = {"h3_res7": "7", "h3_res8": "8", "h3_res9": "9"}
    if crosswalk is True:
        cw = MagicMock()
        cw.city_for_point.return_value = "dallas"
    else:
        cw = crosswalk
    return NcesAnchorProducer(client=client, indexer=indexer, crosswalk=cw, producer=MagicMock())


class TestStatusMapping:
    def test_every_mapped_status_is_an_event_type(self):
        assert CCD_STATUS_EVENT_TYPE["New"] == "opened"
        assert CCD_STATUS_EVENT_TYPE["Closed"] == "closed"
        assert CCD_STATUS_EVENT_TYPE["Reopened"] == "reopened"

    def test_mapping_does_not_invent_closures(self):
        assert "Inactive" in CCD_STATUS_EVENT_TYPE


class TestProcessYear:
    def test_new_and_closed_become_events(self, edge_zip_payload):
        batches = [[
            _ccd_row("480001000001", "New School", "New"),
            _ccd_row("480001000002", "Old School", "Closed"),
            _ccd_row("480001000099", "Ghost School", "Closed"),
            _ccd_row("480001000004", "Boundary School", "New", recon="Yes"),
            _ccd_row("480001000005", "Open School", "Open"),
        ]]
        producer = _producer(batches, edge_zip_payload)
        counts = producer.process_year("2023-24")
        assert counts["events"] == 2  # New + 1x Closed (ghost absent from EDGE)
        assert counts["inventory"] == 1
        assert counts["filtered_recon"] == 1

    def test_unsited_row_dlqs_not_guesses(self, edge_zip_payload):
        batches = [[
            _ccd_row("480001000001", "New School", "New"),
            _ccd_row("480001000099", "Ghost School", "Closed"),
        ]]
        producer = _producer(batches, edge_zip_payload)
        counts = producer.process_year("2023-24")
        assert counts["dlq_unmatched"] == 1  # 480001000003 absent from EDGE
        assert counts["events"] == 1  # only 480001000001 emitted

    def test_out_of_scope_without_crosswalk(self, edge_zip_payload):
        batches = [[
            _ccd_row("480001000001", "New School", "New"),
            _ccd_row("480001000002", "Old School", "Closed"),
        ]]
        producer = _producer(batches, edge_zip_payload, crosswalk=None)
        counts = producer.process_year("2023-24")
        assert counts["out_of_scope"] == 2
        assert counts["events"] == 0

    def test_charter_flag_flips_category(self, edge_zip_payload):
        batches = [[
            _ccd_row("480001000001", "Charter School", "New", charter="Yes"),
        ]]
        producer = _producer(batches, edge_zip_payload)
        producer.producer = MagicMock()
        counts = producer.process_year("2023-24")
        assert counts["events"] == 1
        payload = producer.producer.produce.call_args.kwargs["payload"]
        assert payload.category == "charter"

    def test_event_uses_anchor_topic(self, edge_zip_payload):
        batches = [[_ccd_row("480001000001", "New School", "New")]]
        producer = _producer(batches, edge_zip_payload)
        producer.producer = MagicMock()
        producer.process_year("2023-24")
        kwargs = producer.producer.produce.call_args.kwargs
        assert kwargs["topic"] == ANCHOR_TOPIC
        payload = kwargs["payload"]
        assert payload.institution_id == "480001000001"
        assert payload.event_type == "opened"
        assert AnchorInstitutionEvent.model_validate(payload.model_dump())
