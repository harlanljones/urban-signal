"""Unit tests for San Francisco municipal data producer parsers (Permits, 311, Licenses, Deeds)."""

from unittest.mock import MagicMock
import pytest

from src.features.shift_dynamics import ComplaintShiftDynamics
from src.producers.complaints_311_producer import Complaints311Producer
from src.producers.deeds_acris_producer import DeedsACRISProducer
from src.producers.dob_permits_producer import DOBPermitsProducer
from src.producers.scheduler import MunicipalIngestionScheduler
from src.producers.sla_licenses_producer import SLALicensesProducer
from src.schemas.models import ComplaintCategory, JobType


def test_sf_dob_permits_parser():
    producer = DOBPermitsProducer(bootstrap_servers="localhost:9092")

    # 1. New Construction permit
    row_nb = {
        "permit_number": "202601019999",
        "permit_type_definition": "new construction",
        "filed_date": "2026-01-15T00:00:00.000",
        "issued_date": "2026-03-20T00:00:00.000",
        "estimated_cost": "4500000.00",
        "revised_cost": "5000000.00",
        "street_number": "500",
        "street_name": "Howard",
        "street_suffix": "St",
        "zipcode": "94105",
        "analysis_neighborhood": "Financial District South",
        "supervisor_district": "6",
        "block": "3721",
        "lot": "001",
        "proposed_units": "24",
        "existing_units": "0",
        "proposed_stories": "8",
        "location": {
            "latitude": "37.7885",
            "longitude": "-122.3980",
        },
        "current_status": "issued",
    }

    event = producer.parse_socrata_row(row_nb, city_id="san_francisco")
    assert event is not None
    assert event.city_id == "san_francisco"
    assert event.job_id == "202601019999"
    assert event.job_type == JobType.NB
    assert event.estimated_cost == 5000000.0
    assert event.borough == "SAN_FRANCISCO_CORE"
    assert event.source_neighborhood == "Financial District South"
    assert event.address_street == "Howard St"
    assert event.address_num == "500"
    assert event.zipcode == "94105"
    assert event.block == "3721"
    assert event.lot == "001"
    assert event.proposed_dwelling_units == 24
    assert event.existing_dwelling_units == 0
    assert event.proposed_stories == 8
    assert event.latitude == pytest.approx(37.7885)
    assert event.longitude == pytest.approx(-122.3980)
    assert event.h3_res7 is not None
    assert event.h3_res8 is not None
    assert event.h3_res9 is not None
    assert event.issuance_date is not None
    assert event.issuance_date.year == 2026
    assert event.issuance_date.month == 3

    # 2. Demolition permit & auto-detection of city
    row_dm = {
        "permit_number": "202602021111",
        "permit_type_definition": "demolitions",
        "revised_cost": "150000",
        "location": {
            "coordinates": [-122.4194, 37.7749],
        },
    }
    event_dm = producer.parse_socrata_row(row_dm)
    assert event_dm is not None
    assert event_dm.city_id == "san_francisco"
    assert event_dm.job_type == JobType.DM
    assert event_dm.estimated_cost == 150000.0
    assert event_dm.latitude == pytest.approx(37.7749)
    assert event_dm.longitude == pytest.approx(-122.4194)

    # 3. Alterations / additions permit
    row_alt = {
        "permit_number": "202603032222",
        "permit_type_definition": "alterations",
        "estimated_cost": "250000",
        "latitude": "37.7600",
        "longitude": "-122.4200",
    }
    event_alt = producer.parse_socrata_row(row_alt, city_id="sf")
    assert event_alt is not None
    assert event_alt.city_id == "san_francisco"
    assert event_alt.job_type == JobType.A2


def test_sf_311_complaints_parser():
    producer = Complaints311Producer(bootstrap_servers="localhost:9092")

    # 1. Neglect / Infrastructure complaint (Sewer / Street defect)
    row_neglect = {
        "service_request_id": "18492011",
        "service_name": "Street Defects",
        "service_details": "Pothole in roadway",
        "requested_datetime": "2026-05-10T14:22:00.000",
        "address": "100 Market St",
        "neighborhoods_sffind_boundaries": "Financial District",
        "zipcode": "94105",
        "point": {
            "latitude": "37.7936",
            "longitude": "-122.3965",
        },
        "status": "Open",
    }

    event = producer.parse_socrata_row(row_neglect, city_id="san_francisco")
    assert event is not None
    assert event.city_id == "san_francisco"
    assert event.incident_id == "18492011"
    assert event.complaint_type == "Street Defects"
    assert event.descriptor == "Pothole in roadway"
    assert event.category == ComplaintCategory.NEGLECT
    assert event.incident_address == "100 Market St"
    assert event.borough == "SAN_FRANCISCO_CORE"
    assert event.source_neighborhood == "Financial District"
    assert event.zipcode == "94105"
    assert event.latitude == pytest.approx(37.7936)
    assert event.longitude == pytest.approx(-122.3965)
    assert event.h3_res7 is not None
    assert event.h3_res8 is not None
    assert event.h3_res9 is not None

    # 2. QoL complaint (Street and Sidewalk Cleaning / Graffiti)
    row_qol = {
        "service_request_id": "18492099",
        "service_name": "Street and Sidewalk Cleaning",
        "service_details": "Graffiti on sidewalk",
        "requested_datetime": "2026-05-11T09:15:00.000",
        "point": {
            "coordinates": [-122.4180, 37.7650],
        },
    }
    event_qol = producer.parse_socrata_row(row_qol, city_id="sf")
    assert event_qol is not None
    assert event_qol.city_id == "san_francisco"
    assert event_qol.category == ComplaintCategory.QOL
    assert event_qol.latitude == pytest.approx(37.7650)
    assert event_qol.longitude == pytest.approx(-122.4180)

    # 3. Verify taxonomy mappings
    shift = ComplaintShiftDynamics()
    sf_neglect_types = [
        "Blighted Properties",
        "Damaged Property",
        "Sewer Issues",
        "Sidewalk or Curb Issues",
        "Streetlights Damage",
        "Encampments Concern",
        "Homeless Concerns",
    ]
    for n_type in sf_neglect_types:
        assert shift.classify_complaint_type(n_type) == ComplaintCategory.NEGLECT

    sf_qol_types = [
        "Street and Sidewalk Cleaning",
        "Graffiti Removal",
        "Illegal Postings",
        "Noise Report",
        "Commercial Notice",
        "Tree Maintenance",
    ]
    for q_type in sf_qol_types:
        assert shift.classify_complaint_type(q_type) == ComplaintCategory.QOL


def test_sf_licenses_parser():
    producer = SLALicensesProducer(bootstrap_servers="localhost:9092")

    row = {
        "location_id": "1002938-04-221",
        "ownership_name": "BAY AREA RESTAURANTS GROUP INC",
        "dba_name": "MISSION TAVERN & LOUNGE",
        "naics_code_description": "Food and Beverage Services - Full Service Restaurant",
        "street_address": "850 Valencia St",
        "business_start_date": "2026-02-01T00:00:00.000",
        "location_start_date": "2026-02-01T00:00:00.000",
        "business_location": {
            "latitude": "37.7592",
            "longitude": "-122.4215",
        },
    }

    event = producer.parse_socrata_row(row, city_id="san_francisco")
    assert event is not None
    assert event.city_id == "san_francisco"
    assert event.license_id == "1002938-04-221"
    assert event.premises_name == "BAY AREA RESTAURANTS GROUP INC"
    assert event.dba == "MISSION TAVERN & LOUNGE"
    assert event.license_type == "Food and Beverage Services - Full Service Restaurant"
    assert event.address == "850 Valencia St"
    assert event.effective_date is not None
    assert event.effective_date.year == 2026
    assert event.license_status == "ACTIVE"
    assert event.latitude == pytest.approx(37.7592)
    assert event.longitude == pytest.approx(-122.4215)
    assert event.h3_res7 is not None
    assert event.h3_res8 is not None
    assert event.h3_res9 is not None


def test_sf_deeds_parser():
    producer = DeedsACRISProducer(bootstrap_servers="localhost:9092")

    row = {
        "parcel_number": "3721001",
        "block_and_lot_number": "3721001",
        "property_location": "500 Howard St",
        "analysis_neighborhood": "Financial District South",
        "assessed_land_value": "3500000.00",
        "assessed_improvement_value": "4200000.00",
        "assessed_fixtures_value": "150000.00",
        "total_assessed_value": "7850000.00",
        "closed_roll_year": "2026",
        "owner_name": "HOWARD TOWER HOLDINGS LLC",
        "property_class_code_definition": "Commercial Office High Rise",
        "the_geom": {
            "latitude": "37.7885",
            "longitude": "-122.3980",
        },
    }

    event = producer.parse_socrata_row(row, city_id="san_francisco")
    assert event is not None
    assert event.city_id == "san_francisco"
    assert event.doc_id == "3721001"
    assert event.bbl == "3721001"
    assert event.block == "3721"
    assert event.lot == "001"
    assert event.document_amount == 7850000.0
    assert event.borough == "SAN_FRANCISCO_CORE"
    assert event.source_neighborhood == "Financial District South"
    assert event.party1_grantor == "HOWARD TOWER HOLDINGS LLC"
    assert event.latitude == pytest.approx(37.7885)
    assert event.longitude == pytest.approx(-122.3980)
    assert event.h3_res7 is not None
    assert event.h3_res8 is not None
    assert event.h3_res9 is not None


def test_sf_scheduler_integration():
    mock_dlq = MagicMock()
    scheduler = MunicipalIngestionScheduler(
        dlq_producer=mock_dlq,
        rate_limit_delay_seconds=0.0,
        dedup_capacity=1000,
    )
    for p in scheduler.producers.values():
        p.producer = MagicMock()

    # Verify all San Francisco jobs are present in config and metadata
    assert "permits_sf" in scheduler.configs
    assert "311_sf" in scheduler.configs
    assert "sla_sf" in scheduler.configs
    assert "deeds_sf" in scheduler.configs

    # Mock SF permit poll
    mock_rows = [
        {
            "permit_number": "SF-P-2026-01",
            "permit_type_definition": "new construction",
            "revised_cost": "3200000",
            "issued_date": "2026-08-01T11:00:00.000",
            "location": {
                "latitude": "37.7749",
                "longitude": "-122.4194",
            },
        }
    ]
    scheduler.producers["permits"].socrata.paginate = MagicMock(return_value=[mock_rows])

    res = scheduler.poll_job("permits_sf", limit=10)
    assert res["job"] == "permits_sf"
    assert res["status"] == "SUCCESS"
    assert res["records_published"] == 1
    assert res["high_watermark"] == "2026-08-01T11:00:00"

    # Check produce call key contains san_francisco
    called_args = scheduler.producers["permits"].producer.produce.call_args
    assert called_args is not None
    assert called_args.kwargs["key"].startswith("san_francisco:")
