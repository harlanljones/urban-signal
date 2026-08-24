"""Pytest fixtures and mock datasets for Urban Predictor pipeline testing."""

from datetime import datetime, timedelta, timezone
import pytest
from src.schemas.models import (
    Complaint311Event,
    ComplaintCategory,
    DeedEvent,
    JobType,
    PermitEvent,
    SLALicenseEvent,
)


@pytest.fixture
def sample_nyc_coords():
    """Returns sample lat/lng coordinates across all 5 NYC boroughs."""
    return {
        "soho": {"lat": 40.7233, "lng": -74.0030},
        "williamsburg": {"lat": 40.7145, "lng": -73.9555},
        "lic": {"lat": 40.7447, "lng": -73.9485},
        "mott_haven": {"lat": 40.8090, "lng": -73.9225},
        "st_george": {"lat": 40.6437, "lng": -74.0764},
        "manhattan": {"lat": 40.7589, "lng": -73.9851},
        "brooklyn": {"lat": 40.6782, "lng": -73.9442},
        "queens": {"lat": 40.7282, "lng": -73.7949},
        "bronx": {"lat": 40.8448, "lng": -73.8648},
        "staten_island": {"lat": 40.5795, "lng": -74.1502},
    }


@pytest.fixture
def sample_chicago_coords():
    """Returns sample lat/lng coordinates across all 6 Chicago divisions."""
    return {
        "loop": {"lat": 41.8819, "lng": -87.6278},
        "fulton_market": {"lat": 41.8867, "lng": -87.6536},
        "lincoln_park": {"lat": 41.9214, "lng": -87.6513},
        "wicker_park": {"lat": 41.9088, "lng": -87.6796},
        "logan_square": {"lat": 41.9288, "lng": -87.7077},
        "rogers_park": {"lat": 42.0094, "lng": -87.6695},
        "hyde_park": {"lat": 41.7943, "lng": -87.5907},
        "bronzeville": {"lat": 41.8252, "lng": -87.6186},
        "pilsen": {"lat": 41.8562, "lng": -87.6563},
        "little_village": {"lat": 41.8458, "lng": -87.7058},
    }


@pytest.fixture
def sample_sf_coords():
    """Returns sample lat/lng coordinates across all 5 San Francisco Bay Area divisions."""
    return {
        "downtown": {"lat": 37.7879, "lng": -122.4074},
        "soma": {"lat": 37.7785, "lng": -122.3950},
        "mission": {"lat": 37.7599, "lng": -122.4148},
        "oakland_downtown": {"lat": 37.8044, "lng": -122.2711},
        "berkeley_downtown": {"lat": 37.8703, "lng": -122.2681},
        "san_mateo": {"lat": 37.5630, "lng": -122.3255},
        "palo_alto": {"lat": 37.4444, "lng": -122.1609},
        "san_jose": {"lat": 37.3382, "lng": -121.8863},
        "sausalito": {"lat": 37.8590, "lng": -122.4853},
        "san_rafael": {"lat": 37.9735, "lng": -122.5311},
    }



@pytest.fixture
def sample_permit_event():
    return PermitEvent(
        city_id="nyc",
        job_id="M001234567",
        job_type=JobType.A1,
        borough="MANHATTAN",
        block="485",
        lot="22",
        bbl="1004850022",
        address_street="BROADWAY",
        address_num="594",
        zipcode="10012",
        latitude=40.7250,
        longitude=-73.9970,
        estimated_cost=1500000.0,
        proposed_dwelling_units=12,
        existing_dwelling_units=4,
        proposed_stories=6,
        issuance_date=datetime.now(timezone.utc) - timedelta(days=30),
        status="ISSUED",
        h3_res7="872a1072bffffff",
        h3_res8="882a107289fffff",
        h3_res9="892a1072893ffff",
    )


@pytest.fixture
def sample_complaint_event():
    return Complaint311Event(
        city_id="nyc",
        incident_id="SR-998877",
        complaint_type="Noise - Commercial",
        category=ComplaintCategory.QOL,
        incident_address="120 BEDFORD AVE",
        borough="BROOKLYN",
        zipcode="11249",
        latitude=40.7190,
        longitude=-73.9580,
        created_date=datetime.now(timezone.utc) - timedelta(days=10),
        status="Closed",
    )


@pytest.fixture
def sample_sla_event():
    return SLALicenseEvent(
        city_id="nyc",
        license_id="1345980",
        license_type="OP - On-Premises Liquor",
        premises_name="THE CATALYST TAVERN LLC",
        dba="Catalyst Lounge",
        address="150 WYTHE AVE",
        latitude=40.7185,
        longitude=-73.9590,
        effective_date=datetime.now(timezone.utc) - timedelta(days=45),
        license_status="ACTIVE",
    )


@pytest.fixture
def sample_deed_event():
    return DeedEvent(
        city_id="nyc",
        doc_id="CRFN-202600012345",
        doc_type="DEED",
        bbl="3023000010",
        borough="BROOKLYN",
        block="2300",
        lot="10",
        document_amount=4800000.0,
        recorded_date=datetime.now(timezone.utc) - timedelta(days=60),
        latitude=40.7185,
        longitude=-73.9590,
    )
