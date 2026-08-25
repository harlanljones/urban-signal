"""Unit tests for Pydantic models and Avro schema serialization/deserialization."""

import io
import json
from datetime import datetime, timezone
from pathlib import Path
import fastavro
import pytest
from src.schemas.models import (
    CatalystAlert,
    Complaint311Event,
    CrimeEvent,
    DeedEvent,
    EnrichedH3Feature,
    PermitEvent,
    SLALicenseEvent,
    StreetCutEvent,
)


def _validate_avro_roundtrip(schema_filename: str, record_dict: dict):
    schema_path = Path(__file__).resolve().parents[4] / "apps" / "api" / "src" / "schemas" / "avro" / schema_filename
    assert schema_path.exists(), f"Missing schema file {schema_path}"

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = fastavro.parse_schema(json.load(f))

    # Serialize
    buf = io.BytesIO()
    fastavro.schemaless_writer(buf, schema, record_dict)
    raw_bytes = buf.getvalue()
    assert len(raw_bytes) > 0

    # Deserialize
    buf.seek(0)
    deserialized = fastavro.schemaless_reader(buf, schema)
    return deserialized


def test_permit_event_avro_serialization(sample_permit_event):
    data = sample_permit_event.model_dump(mode="json")
    # Date fields as string in Avro
    deserialized = _validate_avro_roundtrip("permit_event.avsc", data)
    assert deserialized["job_id"] == sample_permit_event.job_id
    assert deserialized["latitude"] == sample_permit_event.latitude
    assert deserialized["estimated_cost"] == sample_permit_event.estimated_cost


def test_complaint_311_avro_serialization(sample_complaint_event):
    data = sample_complaint_event.model_dump(mode="json")
    deserialized = _validate_avro_roundtrip("complaint_311_event.avsc", data)
    assert deserialized["incident_id"] == sample_complaint_event.incident_id
    assert deserialized["category"] == sample_complaint_event.category.value


def test_sla_license_avro_serialization(sample_sla_event):
    data = sample_sla_event.model_dump(mode="json")
    deserialized = _validate_avro_roundtrip("sla_license_event.avsc", data)
    assert deserialized["license_id"] == sample_sla_event.license_id
    assert deserialized["license_status"] == sample_sla_event.license_status


def test_deed_event_avro_serialization(sample_deed_event):
    data = sample_deed_event.model_dump(mode="json")
    deserialized = _validate_avro_roundtrip("deed_event.avsc", data)
    assert deserialized["doc_id"] == sample_deed_event.doc_id
    assert deserialized["document_amount"] == sample_deed_event.document_amount


def test_crime_event_avro_serialization():
    event = CrimeEvent(
        city_id="chicago",
        incident_id="14295750",
        offense_type="THEFT",
        offense_class="PART1",
        latitude=41.744201882,
        longitude=-87.665713523,
        h3_res9="89275936477ffff",
    )
    data = event.model_dump(mode="json")
    deserialized = _validate_avro_roundtrip("crime_event.avsc", data)
    assert deserialized["incident_id"] == "14295750"
    assert deserialized["offense_class"] == "PART1"
    assert deserialized["latitude"] == 41.744201882


def test_street_cut_event_avro_serialization():
    event = StreetCutEvent(
        city_id="chicago",
        permit_id="320086",
        permit_type="DOT_PWO",
        work_type="Opening in the Public Way",
        status="Open",
        latitude=41.9124265497,
        longitude=-87.7571380905,
        issued_date=datetime(2026, 8, 23, 12, 54, 52, tzinfo=timezone.utc),
        h3_res9="89c28c0a26fffff",
    )
    data = event.model_dump(mode="json")
    deserialized = _validate_avro_roundtrip("street_cut_event.avsc", data)
    assert deserialized["permit_id"] == "320086"
    assert deserialized["work_type"] == "Opening in the Public Way"
    assert deserialized["latitude"] == 41.9124265497


def test_enriched_h3_feature_avro_serialization():
    feature = EnrichedH3Feature(
        h3_index="892a1072893ffff",
        h3_resolution=9,
        timestamp=datetime.now(timezone.utc),
        sla_move_ins_90d=3,
        sla_move_outs_90d=2,
    )
    data = feature.model_dump(mode="json")
    deserialized = _validate_avro_roundtrip("enriched_h3_feature.avsc", data)
    assert deserialized["h3_index"] == "892a1072893ffff"
    assert deserialized["sla_move_ins_90d"] == 3
    assert deserialized["sla_move_outs_90d"] == 2


def test_pydantic_cost_parsing():
    # Test string parsing with $ and commas
    p = PermitEvent(
        job_id="TEST01",
        latitude=40.7128,
        longitude=-74.0060,
        estimated_cost="$2,450,000.00",
    )
    assert p.estimated_cost == 2450000.0
