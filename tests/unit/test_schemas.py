"""Unit tests for Pydantic models and Avro schema serialization/deserialization."""

import io
import json
from pathlib import Path
import fastavro
import pytest
from src.schemas.models import (
    CatalystAlert,
    Complaint311Event,
    DeedEvent,
    EnrichedH3Feature,
    PermitEvent,
    SLALicenseEvent,
)


def _validate_avro_roundtrip(schema_filename: str, record_dict: dict):
    schema_path = Path(__file__).parent.parent.parent / "src" / "schemas" / "avro" / schema_filename
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


def test_pydantic_cost_parsing():
    # Test string parsing with $ and commas
    p = PermitEvent(
        job_id="TEST01",
        latitude=40.7128,
        longitude=-74.0060,
        estimated_cost="$2,450,000.00",
    )
    assert p.estimated_cost == 2450000.0
