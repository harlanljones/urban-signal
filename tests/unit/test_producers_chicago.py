"""Unit tests for Chicago municipal data producer parsers (Permits, 311, Licenses, Deeds)."""

from unittest.mock import MagicMock
import pytest

from src.features.shift_dynamics import ComplaintShiftDynamics
from src.producers.complaints_311_producer import Complaints311Producer
from src.producers.deeds_acris_producer import DeedsACRISProducer
from src.producers.dob_permits_producer import DOBPermitsProducer
from src.producers.scheduler import MunicipalIngestionScheduler
from src.producers.sla_licenses_producer import SLALicensesProducer
from src.schemas.models import ComplaintCategory, JobType


def test_chicago_dob_permits_parser():
    producer = DOBPermitsProducer(bootstrap_servers="localhost:9092")

    row = {
        "id": "100200300",
        "permit_": "100200300",
        "permit_type": "PERMIT - NEW CONSTRUCTION",
        "issue_date": "2026-05-15T00:00:00.000",
        "reported_cost": "1250000.00",
        "community_area": "28",
        "street_number": "123",
        "street_direction": "N",
        "street_name": "MICHIGAN",
        "street_type": "AVE",
        "zipcode": "60601",
        "latitude": "41.881832",
        "longitude": "-87.623177",
        "status": "ISSUED",
    }

    event = producer.parse_socrata_row(row, city_id="chicago")
    assert event is not None
    assert event.city_id == "chicago"
    assert event.job_id == "100200300"
    assert event.job_type == JobType.NB
    assert event.estimated_cost == 1250000.0
    assert event.borough == "CENTRAL_DOWNTOWN"
    assert event.source_neighborhood == "28"
    assert event.address_street == "N MICHIGAN AVE"
    assert event.address_num == "123"
    assert event.zipcode == "60601"
    assert event.latitude == pytest.approx(41.881832)
    assert event.longitude == pytest.approx(-87.623177)
    assert event.h3_res7 is not None
    assert event.h3_res8 is not None
    assert event.h3_res9 is not None
    assert event.issuance_date is not None
    assert event.issuance_date.year == 2026
    assert event.issuance_date.month == 5

    # Test demolition and renovation type mappings
    row_demo = {
        "permit_": "100200301",
        "permit_type": "PERMIT - WRECKING/DEMOLITION",
        "latitude": "41.88",
        "longitude": "-87.62",
    }
    event_demo = producer.parse_socrata_row(row_demo, city_id="chicago")
    assert event_demo.job_type == JobType.DM

    row_renov = {
        "permit_": "100200302",
        "permit_type": "PERMIT - RENOVATION/ALTERATION AND REPAIR",
        "latitude": "41.88",
        "longitude": "-87.62",
    }
    event_renov = producer.parse_socrata_row(row_renov, city_id="chicago")
    assert event_renov.job_type == JobType.A2


def test_chicago_311_complaints_parser():
    producer = Complaints311Producer(bootstrap_servers="localhost:9092")

    # Neglect test (Water in basement)
    row_neglect = {
        "sr_number": "SR26-00012345",
        "sr_type": "Water In Basement Complaint",
        "created_date": "2026-06-01T12:30:00.000",
        "street_address": "456 W RANDOLPH ST",
        "community_area": "28",
        "postal_code": "60661",
        "latitude": "41.8845",
        "longitude": "-87.6398",
        "status": "Open",
    }

    event = producer.parse_socrata_row(row_neglect, city_id="chicago")
    assert event is not None
    assert event.city_id == "chicago"
    assert event.incident_id == "SR26-00012345"
    assert event.complaint_type == "Water In Basement Complaint"
    assert event.category == ComplaintCategory.NEGLECT
    assert event.incident_address == "456 W RANDOLPH ST"
    assert event.borough == "CENTRAL_DOWNTOWN"
    assert event.source_neighborhood == "28"
    assert event.zipcode == "60661"
    assert event.latitude == pytest.approx(41.8845)
    assert event.longitude == pytest.approx(-87.6398)
    assert event.h3_res7 is not None
    assert event.h3_res8 is not None
    assert event.h3_res9 is not None

    # QoL test (Restaurant Noise)
    row_qol = {
        "sr_number": "SR26-00099999",
        "sr_type": "Restaurant Noise Complaint",
        "created_date": "2026-06-02T22:00:00.000",
        "latitude": "41.8845",
        "longitude": "-87.6398",
    }
    event_qol = producer.parse_socrata_row(row_qol, city_id="chicago")
    assert event_qol.category == ComplaintCategory.QOL

    # Additional Chicago taxonomy verification
    shift = ComplaintShiftDynamics()
    neglect_examples = [
        "BUILDING VIOLATION",
        "RODENT BAITING",
        "ALLEY LIGHT OUT",
        "STREET LIGHT OUT",
        "POT HOLE",
        "NO HEAT",
        "ABANDONED VEHICLE",
        "SEWAGE BACKUP",
    ]
    for kw in neglect_examples:
        assert shift.classify_complaint_type(f"Chicago {kw} Report") == ComplaintCategory.NEGLECT

    qol_examples = [
        "GRAFFITI REMOVAL",
        "SPECIAL EVENT",
        "SIDEWALK CAFE",
        "OUTDOOR PATIO",
        "CONSTRUCTION DUST",
        "TREE TRIMMING",
        "FLY DUMPING",
    ]
    for kw in qol_examples:
        assert shift.classify_complaint_type(f"Chicago {kw} Notice") == ComplaintCategory.QOL


def test_chicago_licenses_parser():
    producer = SLALicensesProducer(bootstrap_servers="localhost:9092")

    row = {
        "license_id": "2849102",
        "legal_name": "LOOP HOSPITALITY LLC",
        "doing_business_as_name": "THE GOTHAM LOUNGE",
        "license_description": "Consumption on Premises - Incidental Activity",
        "address": "200 N LA SALLE ST",
        "latitude": "41.8858",
        "longitude": "-87.6324",
        "date_issued": "2026-01-15T00:00:00.000",
        "license_term_expiration_date": "2028-01-15T00:00:00.000",
        "license_status": "AAI",
    }

    event = producer.parse_socrata_row(row, city_id="chicago")
    assert event is not None
    assert event.city_id == "chicago"
    assert event.license_id == "2849102"
    assert event.premises_name == "LOOP HOSPITALITY LLC"
    assert event.dba == "THE GOTHAM LOUNGE"
    assert event.license_type == "Consumption on Premises - Incidental Activity"
    assert event.address == "200 N LA SALLE ST"
    assert event.effective_date is not None
    assert event.expiration_date is not None
    assert event.latitude == pytest.approx(41.8858)
    assert event.longitude == pytest.approx(-87.6324)
    assert event.h3_res7 is not None
    assert event.h3_res8 is not None
    assert event.h3_res9 is not None


def test_chicago_deeds_parser():
    producer = DeedsACRISProducer(bootstrap_servers="localhost:9092")

    row = {
        "doc_id": "DOC-2026-CC-8888",
        "doc_type": "DEED",
        "pin": "17-09-200-010-0000",
        "township": "NORTH CHICAGO",
        "sale_price": "3500000.00",
        "recorded_datetime": "2026-04-10T14:00:00.000",
        "grantor": "WEST LOOP INVESTMENTS LLC",
        "grantee": "MIDWEST URBAN HOLDINGS LP",
        "latitude": "41.8830",
        "longitude": "-87.6450",
    }

    event = producer.parse_socrata_row(row, city_id="chicago")
    assert event is not None
    assert event.city_id == "chicago"
    assert event.doc_id == "DOC-2026-CC-8888"
    assert event.doc_type == "DEED"
    assert event.bbl == "17-09-200-010-0000"
    assert event.borough == "CENTRAL_DOWNTOWN"
    assert event.source_neighborhood == "NORTH CHICAGO"
    assert event.document_amount == 3500000.0
    assert event.party1_grantor == "WEST LOOP INVESTMENTS LLC"
    assert event.party2_grantee == "MIDWEST URBAN HOLDINGS LP"
    assert event.latitude == pytest.approx(41.8830)
    assert event.longitude == pytest.approx(-87.6450)
    assert event.h3_res7 is not None
    assert event.h3_res8 is not None
    assert event.h3_res9 is not None


def test_chicago_scheduler_integration():
    mock_dlq = MagicMock()
    scheduler = MunicipalIngestionScheduler(
        dlq_producer=mock_dlq,
        rate_limit_delay_seconds=0.0,
        dedup_capacity=1000,
    )
    for p in scheduler.producers.values():
        p.producer = MagicMock()

    # Verify all Chicago jobs are present in config and metadata
    assert "permits_chicago" in scheduler.configs
    assert "311_chicago" in scheduler.configs
    assert "sla_chicago" in scheduler.configs
    assert "deeds_chicago" in scheduler.configs

    # Mock Chicago permit poll
    mock_rows = [
        {
            "id": "CHI-P001",
            "permit_": "CHI-P001",
            "latitude": "41.88",
            "longitude": "-87.62",
            "permit_type": "PERMIT - NEW CONSTRUCTION",
            "reported_cost": "2000000",
            "issue_date": "2026-07-01T10:00:00.000",
        }
    ]
    scheduler.producers["permits"].socrata.paginate = MagicMock(return_value=[mock_rows])

    res = scheduler.poll_job("permits_chicago", limit=10)
    assert res["job"] == "permits_chicago"
    assert res["status"] == "SUCCESS"
    assert res["records_published"] == 1
    assert res["high_watermark"] == "2026-07-01T10:00:00"

    # Check produce call key contains chicago
    called_args = scheduler.producers["permits"].producer.produce.call_args
    assert called_args is not None
    assert called_args.kwargs["key"].startswith("chicago:")
