"""US-72: FeedType/topic taxonomy extension (crime, street_cut, evictions, str)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.config import settings
from src.consumers.feature_aggregation_worker import FeatureAggregationWorker
from src.spatial.city_registry import (
    REGISTRY,
    CityId,
    FeedType,
    get_dataset,
    get_job_name,
)

NEW_SIGNAL_FEEDS = (FeedType.CRIME, FeedType.STREET_CUT, FeedType.EVICTIONS, FeedType.STR)


def test_feedtype_has_signal_survey_members():
    values = set(FeedType.__members__.values())
    for feed in NEW_SIGNAL_FEEDS:
        assert feed in values


def test_new_feeds_have_configured_raw_topics():
    for feed in NEW_SIGNAL_FEEDS:
        topic = getattr(settings, f"topic_{feed.value}")
        assert topic == f"raw.municipal.{feed.value}"
        assert topic.startswith("raw.municipal.")


def test_get_job_name_is_generic_for_new_feeds():
    assert get_job_name(FeedType.CRIME, CityId.NYC) == "crime"
    assert get_job_name(FeedType.CRIME, CityId.CHICAGO) == "crime_chicago"
    assert get_job_name(FeedType.STREET_CUT, CityId.NEW_ORLEANS) == "street_cut_nola"
    assert get_job_name(FeedType.EVICTIONS, CityId.BOSTON) == "evictions_boston"
    assert get_job_name(FeedType.STR, CityId.SEATTLE) == "str_seattle"


def test_unregistered_new_feeds_raise_readable_get_dataset_error():
    # Boston registers none of the signal-survey feeds (US-71/81/92/93).
    for feed in NEW_SIGNAL_FEEDS:
        with pytest.raises(KeyError) as excinfo:
            get_dataset(CityId.BOSTON, feed)
        message = str(excinfo.value)
        assert "boston" in message and feed.value in message


def test_only_cleared_signal_feeds_are_registered():
    """US-72 made the taxonomy ingestible; US-71 registered crime in the four
    metros with a verified live feed, US-81 registered street-cut in the
    one metro with a geocodable feed (Chicago CDOT street closures; NYC's
    current rows are address-only), and US-93 registered NYC-only evictions
    as context/validation. STR remains unregistered (US-92 closed not-worth-it)."""
    registered_for = {
        FeedType.CRIME: {CityId.NYC, CityId.CHICAGO, CityId.SAN_FRANCISCO, CityId.SEATTLE},
        FeedType.STREET_CUT: {CityId.CHICAGO},
        FeedType.EVICTIONS: {CityId.NYC},
        FeedType.STR: set(),
    }
    for city, reg in REGISTRY.items():
        for feed in NEW_SIGNAL_FEEDS:
            registered = feed in reg.datasets
            assert registered == (city in registered_for[feed]), (city, feed)


# ---------------------------------------------------------------------------
# Partition/keying review (scaling notes): enriched topic keyed city_id:h3
# ---------------------------------------------------------------------------

def _feat_dict(h3_index: str) -> dict:
    return {
        "h3_index": h3_index,
        "h3_resolution": 9,
        "capex_density_decayed": 0.0,
        "permit_count_60d": 0,
        "permit_count_180d": 0,
        "permit_velocity": 0.0,
        "complaints_neglect_count": 0,
        "complaints_qol_count": 0,
        "shift_ratio_311": 1.0,
        "sla_active_licenses": 0,
        "sla_new_filings_90d": 0,
        "sla_move_ins_90d": 0,
        "sla_move_outs_90d": 0,
        "deed_total_volume_180d": 0.0,
        "deed_transaction_count_180d": 0,
        "lims_score": 0.0,
    }


def test_enriched_records_key_by_city_and_cell(monkeypatch):
    producers = [MagicMock(), MagicMock()]
    with (
        patch("src.consumers.feature_aggregation_worker.BaseKafkaProducer", side_effect=producers),
        patch("src.consumers.feature_aggregation_worker.SpatialFeaturePipeline"),
    ):
        worker = FeatureAggregationWorker(city_id="chicago")
    h3_index = "89275936477ffff"
    worker.feature_pipeline.compute_h3_cell_features.return_value = _feat_dict(h3_index)
    worker.process_and_emit_cell(
        h3_index=h3_index,
        resolution=9,
        as_of_date=datetime.now(timezone.utc),
        city_id="chicago",
    )
    enriched_producer = producers[0]
    _, kwargs = enriched_producer.produce.call_args
    assert kwargs["key"] == f"chicago:{h3_index}"
    assert kwargs["topic"] == settings.topic_enriched_h3
    assert kwargs["payload"].city_id == "chicago"