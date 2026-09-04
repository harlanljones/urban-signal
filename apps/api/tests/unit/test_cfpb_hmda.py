"""Unit tests for the CFPB HMDA LAR ingestion leaf module (US-423).

Leaf-only: imports no spine symbols (config / city_registry / geo_utils /
submarkets / producers). Network calls are stubbed; no real HTTP is
performed. Aggregation output is checked for wiring compatibility with
``hmda_metrics.rollup_tract_to_h3`` (US-165).
"""

import pytest

from src.spatial.cfpb_hmda import (
    HmdaLarClient,
    TractHmdaAggregate,
    aggregate_lar_rows,
    normalize_census_tract,
    tract_metrics_for_rollup,
)
from src.spatial.hmda_metrics import denial_rate, investor_purchase_share, rollup_tract_to_h3


def _row(**overrides):
    base = {
        "census_tract": "22071000100",
        "action_taken": "1",
        "loan_purpose": "1",
        "occupancy_type": "1",
        "loan_type": "1",
        "loan_amount": "250000",
    }
    base.update(overrides)
    return base


def test_normalize_census_tract_valid():
    assert normalize_census_tract("22071000100") == "22071000100"


def test_normalize_census_tract_strips_whitespace():
    assert normalize_census_tract("  22071000100  ") == "22071000100"


@pytest.mark.parametrize("raw", [None, "", "NA", "1234", "220710001000", "abcdefghijk"])
def test_normalize_census_tract_invalid_returns_none(raw):
    assert normalize_census_tract(raw) is None


def test_aggregate_lar_rows_skips_rows_without_tract():
    rows = [_row(census_tract=None), _row()]
    aggs = aggregate_lar_rows(rows)
    assert len(aggs) == 1
    assert aggs["22071000100"].total_applications == 1


def test_aggregate_lar_rows_counts_total_applications():
    rows = [_row(), _row(), _row(census_tract="22071000200")]
    aggs = aggregate_lar_rows(rows)
    assert aggs["22071000100"].total_applications == 2
    assert aggs["22071000200"].total_applications == 1


def test_aggregate_lar_rows_purchase_and_investor_share():
    rows = [
        _row(loan_purpose="1", occupancy_type="1"),  # purchase, owner-occ
        _row(loan_purpose="1", occupancy_type="3"),  # purchase, investor
        _row(loan_purpose="1", occupancy_type="3"),  # purchase, investor
        _row(loan_purpose="2"),  # home improvement, not a purchase
    ]
    aggs = aggregate_lar_rows(rows)
    agg = aggs["22071000100"]
    assert agg.purchase == 3
    assert agg.investor_purchase == 2
    assert investor_purchase_share(agg.investor_purchase, agg.purchase) == pytest.approx(2 / 3)


def test_aggregate_lar_rows_home_improvement_volume():
    rows = [
        _row(loan_purpose="2", loan_amount="50000"),
        _row(loan_purpose="2", loan_amount="30000"),
        _row(loan_purpose="1", loan_amount="200000"),  # purchase, excluded
    ]
    agg = aggregate_lar_rows(rows)["22071000100"]
    assert agg.home_improvement_volume == pytest.approx(80000.0)


def test_aggregate_lar_rows_denial_rate():
    rows = [
        _row(action_taken="1"),  # originated -> decided
        _row(action_taken="3"),  # denied -> decided + denied
        _row(action_taken="3"),  # denied -> decided + denied
        _row(action_taken="6"),  # purchased loan -> not a decision
    ]
    agg = aggregate_lar_rows(rows)["22071000100"]
    assert agg.decided == 3
    assert agg.denied == 2
    assert denial_rate(agg.denied, agg.decided) == pytest.approx(2 / 3)


def test_aggregate_lar_rows_government_backed_only_counted_when_decided():
    rows = [
        _row(action_taken="1", loan_type="2"),  # decided + FHA
        _row(action_taken="4", loan_type="2"),  # withdrawn (decided) + FHA
        _row(action_taken="7", loan_type="2"),  # preapproval (not decided) + FHA, excluded
    ]
    agg = aggregate_lar_rows(rows)["22071000100"]
    assert agg.government_backed == 2


def test_aggregate_lar_rows_loan_amount_total():
    rows = [_row(loan_amount="100000"), _row(loan_amount="150000")]
    agg = aggregate_lar_rows(rows)["22071000100"]
    assert agg.loan_amount_total == pytest.approx(250000.0)


def test_aggregate_lar_rows_empty_input():
    assert aggregate_lar_rows([]) == {}


def test_tract_aggregate_as_metrics_shape():
    agg = TractHmdaAggregate(
        census_tract="22071000100",
        total_applications=5,
        purchase=3,
        investor_purchase=1,
        home_improvement_volume=10000.0,
        decided=4,
        denied=1,
        government_backed=2,
        loan_amount_total=500000.0,
    )
    metrics = agg.as_metrics()
    assert metrics["purchase"] == 3.0
    assert metrics["investor_purchase"] == 1.0
    assert metrics["decided"] == 4.0
    assert metrics["denied"] == 1.0
    assert isinstance(metrics["loan_amount_total"], float)


def test_tract_metrics_for_rollup_feeds_hmda_metrics_rollup():
    rows = [
        _row(census_tract="22071000100", loan_purpose="1", occupancy_type="3"),
        _row(census_tract="22071000100", loan_purpose="1", occupancy_type="1"),
        _row(census_tract="22071000200", loan_purpose="1", occupancy_type="1"),
    ]
    aggs = aggregate_lar_rows(rows)
    tract_metrics = tract_metrics_for_rollup(aggs)
    centroids = {
        "22071000100": (29.951, -90.075),
        "22071000200": (29.952, -90.076),
    }
    cells = rollup_tract_to_h3(tract_metrics, centroids, resolution=7)
    assert len(cells) == 1
    cell = next(iter(cells.values()))
    assert cell["purchase"] == 3
    assert cell["investor_purchase"] == 1


class _FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class _FakeHttpClient:
    def __init__(self, csv_text):
        self._csv_text = csv_text
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url, params))
        return _FakeResponse(self._csv_text)


def test_hmda_lar_client_fetch_csv_builds_params():
    fake = _FakeHttpClient("census_tract,action_taken\n22071000100,1\n")
    client = HmdaLarClient(http_client=fake)
    text = client.fetch_csv(states=["ca", "ny"], years=[2025])
    assert text.startswith("census_tract")
    assert fake.calls[0][1]["states"] == "CA,NY"
    assert fake.calls[0][1]["years"] == "2025"


def test_hmda_lar_client_lar_rows_parses_csv():
    csv_text = "census_tract,action_taken,loan_purpose\n22071000100,1,1\n22071000200,3,1\n"
    fake = _FakeHttpClient(csv_text)
    client = HmdaLarClient(http_client=fake)
    rows = client.lar_rows(states=["LA"], years=[2025])
    assert len(rows) == 2
    assert rows[0]["census_tract"] == "22071000100"
    assert rows[1]["action_taken"] == "3"
