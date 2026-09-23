"""Unit tests for the Redfin ZIP-code market tracker ingestion (US-440).

Fixture rows are trimmed from the live ``zip_code_market_tracker.tsv000.gz``
release fetched 2026-09-13 (13 consecutive months for ZIP 94610 / Oakland,
plus one Bay Area low-volume ZIP with an ``NA`` metric and one non-Bay-Area
ZIP to exercise the scope filter). Network-free: every test feeds
``parse_redfin_tsv`` decompressed text directly.
"""

from datetime import date

import pytest

from src.producers.redfin_client import (
    EXTENSIVE_REDFIN_METRICS,
    INTENSIVE_REDFIN_METRICS,
    REDFIN_METRICS,
    RedfinRow,
    parse_redfin_tsv,
    redfin_rows_to_observations,
)
from src.spatial.bay_area_zips import is_bay_area_zip, normalize_zip

_HEADER = (
    "PERIOD_BEGIN\tPERIOD_END\tPERIOD_DURATION\tREGION_TYPE\tREGION_TYPE_ID\tTABLE_ID\t"
    "IS_SEASONALLY_ADJUSTED\tREGION\tCITY\tSTATE\tSTATE_CODE\tPROPERTY_TYPE\t"
    "PROPERTY_TYPE_ID\tMEDIAN_SALE_PRICE\tMEDIAN_SALE_PRICE_MOM\tMEDIAN_SALE_PRICE_YOY\t"
    "MEDIAN_LIST_PRICE\tMEDIAN_LIST_PRICE_MOM\tMEDIAN_LIST_PRICE_YOY\tMEDIAN_PPSF\t"
    "MEDIAN_PPSF_MOM\tMEDIAN_PPSF_YOY\tMEDIAN_LIST_PPSF\tMEDIAN_LIST_PPSF_MOM\t"
    "MEDIAN_LIST_PPSF_YOY\tHOMES_SOLD\tHOMES_SOLD_MOM\tHOMES_SOLD_YOY\tPENDING_SALES\t"
    "PENDING_SALES_MOM\tPENDING_SALES_YOY\tNEW_LISTINGS\tNEW_LISTINGS_MOM\t"
    "NEW_LISTINGS_YOY\tINVENTORY\tINVENTORY_MOM\tINVENTORY_YOY\tMONTHS_OF_SUPPLY\t"
    "MONTHS_OF_SUPPLY_MOM\tMONTHS_OF_SUPPLY_YOY\tMEDIAN_DOM\tMEDIAN_DOM_MOM\t"
    "MEDIAN_DOM_YOY\tAVG_SALE_TO_LIST\tAVG_SALE_TO_LIST_MOM\tAVG_SALE_TO_LIST_YOY\t"
    "SOLD_ABOVE_LIST\tSOLD_ABOVE_LIST_MOM\tSOLD_ABOVE_LIST_YOY\tPRICE_DROPS\t"
    "PRICE_DROPS_MOM\tPRICE_DROPS_YOY\tOFF_MARKET_IN_TWO_WEEKS\t"
    "OFF_MARKET_IN_TWO_WEEKS_MOM\tOFF_MARKET_IN_TWO_WEEKS_YOY\tPARENT_METRO_REGION\t"
    "PARENT_METRO_REGION_METRO_CODE\tLAST_UPDATED"
)


def _row(
    period_begin: str,
    period_end: str,
    region: str = "Zip Code: 94610",
    property_type_id: str = "-1",
    median_sale_price: str = "1450000",
    homes_sold: str = "67",
    price_drops: str = "0.15",
) -> str:
    cells = ["x"] * 58
    cells[0] = period_begin
    cells[1] = period_end
    cells[7] = region
    cells[12] = property_type_id
    cells[13] = median_sale_price
    cells[16] = "1095000"  # MEDIAN_LIST_PRICE
    cells[19] = "777.7"  # MEDIAN_PPSF
    cells[25] = homes_sold
    cells[28] = "83"  # PENDING_SALES
    cells[34] = "45"  # INVENTORY
    cells[40] = "13"  # MEDIAN_DOM
    cells[49] = price_drops
    return "\t".join(cells)


# 13 consecutive months, real values for Oakland 94610, trimmed from the
# 2026-09-13 live release (verifies >= 12 months of history parses cleanly).
_TWELVE_MONTHS = [
    _row("2025-03-01", "2025-05-31", median_sale_price="1270000", homes_sold="67"),
    _row("2025-04-01", "2025-06-30", median_sale_price="1150000", homes_sold="75"),
    _row("2025-05-01", "2025-07-31", median_sale_price="1100000", homes_sold="69"),
    _row("2025-06-01", "2025-08-31", median_sale_price="892500", homes_sold="66"),
    _row("2025-07-01", "2025-09-30", median_sale_price="1077500", homes_sold="66"),
    _row("2025-08-01", "2025-10-31", median_sale_price="1125000", homes_sold="79"),
    _row("2025-09-01", "2025-11-30", median_sale_price="1250000", homes_sold="85"),
    _row("2025-10-01", "2025-12-31", median_sale_price="1015000", homes_sold="78"),
    _row("2025-11-01", "2026-01-31", median_sale_price="900000", homes_sold="51"),
    _row("2025-12-01", "2026-02-28", median_sale_price="1200000", homes_sold="45"),
    _row("2026-01-01", "2026-03-31", median_sale_price="1475000", homes_sold="38"),
    _row("2026-02-01", "2026-04-30", median_sale_price="1365250", homes_sold="58"),
    _row("2026-03-01", "2026-05-31", median_sale_price="1450000", homes_sold="67"),
]


class TestBayAreaZipFilter:
    def test_normalize_handles_redfin_region_label(self):
        assert normalize_zip("Zip Code: 94104") == "94104"

    def test_normalize_handles_zip_plus_four_and_float(self):
        assert normalize_zip("94104-1234") == "94104"
        assert normalize_zip(94104.0) == "94104"

    def test_bay_area_prefixes(self):
        assert is_bay_area_zip("94610")  # Oakland
        assert is_bay_area_zip("95113")  # San Jose
        assert not is_bay_area_zip("10001")  # NYC
        assert not is_bay_area_zip("90210")  # LA


class TestParseRedfinTsv:
    def test_twelve_plus_months_parse_in_order(self):
        text = _HEADER + "\n" + "\n".join(_TWELVE_MONTHS) + "\n"
        rows = list(parse_redfin_tsv(text))
        assert len(rows) == 13
        assert all(r.zcta == "94610" for r in rows)
        periods = [r.period for r in rows]
        assert periods == sorted(periods)
        assert periods[0] == date(2025, 5, 1)  # from PERIOD_END, normalized
        assert periods[-1] == date(2026, 5, 1)
        assert rows[-1].metrics["median_sale_price"] == pytest.approx(1450000.0)
        assert rows[-1].metrics["homes_sold"] == pytest.approx(67.0)

    def test_non_bay_area_zip_is_dropped(self):
        text = _HEADER + "\n" + _row("2026-01-01", "2026-03-31", region="Zip Code: 10001") + "\n"
        assert list(parse_redfin_tsv(text)) == []

    def test_non_aggregate_property_type_is_dropped(self):
        text = (
            _HEADER
            + "\n"
            + _row("2026-01-01", "2026-03-31", property_type_id="3")  # single-family slice
            + "\n"
        )
        assert list(parse_redfin_tsv(text)) == []

    def test_all_na_row_yields_nothing(self):
        cells = ["NA"] * 58
        cells[0], cells[1] = "2026-01-01", "2026-03-31"
        cells[7] = "Zip Code: 94104"
        cells[12] = "-1"
        text = _HEADER + "\n" + "\t".join(cells) + "\n"
        assert list(parse_redfin_tsv(text)) == []

    def test_missing_metric_falls_back_gracefully(self):
        # A ZIP with too few transactions reports NA for some but not all
        # metrics (verified live: MEDIAN_DOM/PRICE_DROPS often NA for
        # low-volume Bay Area ZIPs while sale price still prints).
        cells = _row("2026-01-01", "2026-03-31", region="Zip Code: 94104").split("\t")
        cells[40] = "NA"  # MEDIAN_DOM
        cells[49] = "NA"  # PRICE_DROPS
        text = _HEADER + "\n" + "\t".join(cells) + "\n"
        rows = list(parse_redfin_tsv(text))
        assert len(rows) == 1
        assert "median_dom" not in rows[0].metrics
        assert "price_drops" not in rows[0].metrics
        assert "median_sale_price" in rows[0].metrics


class TestObservationConversion:
    def test_one_row_yields_one_observation_per_metric(self):
        row = RedfinRow(
            zcta="94610",
            period=date(2026, 5, 1),
            metrics={"median_sale_price": 1450000.0, "homes_sold": 67.0},
        )
        observations = redfin_rows_to_observations(iter([row]), vintage="2026-09-13")
        assert len(observations) == 2
        series_ids = {o.series_id for o in observations}
        assert series_ids == {"redfin_median_sale_price_zip", "redfin_homes_sold_zip"}
        for obs in observations:
            assert obs.geography_id == "94610"
            assert obs.period == date(2026, 5, 1)
            assert obs.source_vintage == "2026-09-13"
            assert obs.city_id == "san_francisco"

    def test_metric_families_are_disjoint_and_cover_the_registry(self):
        assert set(INTENSIVE_REDFIN_METRICS) & set(EXTENSIVE_REDFIN_METRICS) == set()
        assert set(INTENSIVE_REDFIN_METRICS) | set(EXTENSIVE_REDFIN_METRICS) == set(
            REDFIN_METRICS
        )


class TestStreamedFetch:
    """``fetch_bay_area_zip_tracker`` streams to disk and parses line by line."""

    def test_fetch_parses_gzip_file_from_disk(self, monkeypatch: pytest.MonkeyPatch):
        import gzip

        from src.producers import redfin_client

        text = _HEADER + "\n" + "\n".join(_TWELVE_MONTHS) + "\n"

        def fake_download(url, dest, timeout_seconds):
            dest.write_bytes(gzip.compress(text.encode("utf-8")))

        monkeypatch.setattr(redfin_client, "_download_to_file", fake_download)
        observations = redfin_client.fetch_bay_area_zip_tracker(vintage="2026-09-13")
        sale = [o for o in observations if o.series_id == "redfin_median_sale_price_zip"]
        assert len(sale) == 13
        assert {o.geography_id for o in sale} == {"94610"}

    def test_fetch_rejects_non_gzip_payload(self, monkeypatch: pytest.MonkeyPatch):
        from src.producers import redfin_client

        monkeypatch.setattr(
            redfin_client,
            "_download_to_file",
            lambda url, dest, timeout_seconds: dest.write_bytes(b"<html>AccessDenied</html>"),
        )
        with pytest.raises(redfin_client.RedfinFetchError, match="not a valid gzip payload"):
            redfin_client.fetch_bay_area_zip_tracker()
