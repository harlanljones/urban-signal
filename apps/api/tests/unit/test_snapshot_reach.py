"""Every snapshot feed reads the rows it exists for (2026-09-30).

A snapshot poll re-reads its source and stops at the job's ``batch_limit``
(1,000 unless the spec declares more). Read in table order, a source larger
than its cap hands every poll the same slice and never the rows past it. A
feed avoids that in one of two ways:

- **Full read:** the cap clears the whole filtered table by half again, so
  every poll reads every row.
- **Newest-first window:** the order starts with a ``DESC`` date term, so the
  cap is a window on recent rows. The window holds half again the rows dated
  in the last 90 days, so batch updates and late recordings land inside it.

Every other snapshot feed is a known gap with its reason. The counts are live
measurements from 2026-09-30 (``docs/research/snapshot-reach-2026-09-30.md``);
a new snapshot feed has to bring its own. SNAP retailer feeds are checked by
``test_producers_snap.py::TestSnapMetroScope``, and GBFS feeds stream rather
than poll, so neither is in scope here.
"""

import pytest

from src.producers.scheduler import _NEWEST_FIRST, JobConfig
from src.spatial.city_registry import REGISTRY, CityId, FeedType, settings

DEFAULT_CAP = JobConfig.batch_limit

# Rows in the filtered source table, for feeds read in full.
FULL_READ_ROWS = {
    # City of Allentown building permits issued in the spec's 90-day window,
    # newest 2026-09-29, read 2026-09-30.
    ("allentown", "permits"): 819,
    # City of Asheville permits opened in the spec's 90-day window, less the
    # right-of-way, event, vendor, over-the-counter and home-business
    # records, newest 2026-09-29, read 2026-09-30; 7 carry no point.
    ("asheville", "permits"): 697,
    # Deschutes County sales on the four township-ranges under Bend's metro
    # box, dated in the spec's 90-day window, read 2026-09-30 (1,019 of them
    # fall in the box).
    ("bend", "deeds"): 1_048,
    ("bend", "sla"): 5_981,
    # Chandler, Glendale, Phoenix, Scottsdale and Tempe deeds (Maricopa
    # Assessor): the deeds dated in each spec's 90-day window inside its
    # JURISDICTION, read 2026-09-30.
    ("chandler", "deeds"): 1_573,
    # Mecklenburg County transfers dated in the spec's 90-day window, newest
    # 2026-09-22, read 2026-09-30.
    ("charlotte", "deeds"): 8_925,
    ("cincinnati", "deeds"): 1_078,
    # Denver, Hartford and Nashville deeds: the transfers dated in each
    # spec's own 90-day window, read 2026-09-30.
    ("denver", "deeds"): 2_445,
    ("eugene", "sla"): 752,
    ("fort_collins", "permits"): 2_183,
    ("glendale_az", "deeds"): 1_263,
    ("hartford", "deeds"): 353,
    ("inland_empire", "sla"): 10_585,
    # Jackson County sales whose SiteCity is MEDFORD, dated in the spec's
    # 90-day window, read 2026-09-30.
    ("medford", "deeds"): 304,
    ("milwaukee", "deeds"): 5_685,
    ("milwaukee", "sla"): 1_275,
    ("modesto", "sla"): 4_574,
    ("montgomery", "sla"): 1_084,
    ("nashville", "deeds"): 4_373,
    ("nyc", "childcare"): 2_752,
    ("oakland", "sla"): 5_103,
    ("phoenix", "deeds"): 9_224,
    # The same Pierce County sales as Tacoma's, placed anywhere in the county
    # (2,317 of them on 2026-09-30).
    ("pierce", "deeds"): 2_432,
    ("portland", "sla"): 6_079,
    # Chesterfield County offenses in the metro box over the last 120 days.
    ("richmond", "crime"): 1_249,
    # The transfers since the same day a year before (Excel, 2026-09-23 workbook).
    ("richmond", "deeds"): 6_650,
    ("santa_rosa", "sla"): 4_979,
    ("scottsdale", "deeds"): 2_507,
    ("st_louis", "sla"): 1_799,
    ("stockton", "sla"): 1_369,
    # Pierce County sales dated in the spec's 90-day window, county-wide
    # (2026-09-25 extract, read 2026-09-30); 452 of them place in Tacoma.
    ("tacoma", "deeds"): 2_432,
    ("tempe", "deeds"): 783,
    # Lucas County sales recorded in the spec's 90-day window, county-wide,
    # newest 2026-09-25, read 2026-09-30; 2,154 of them lie in the metro box.
    ("toledo", "deeds"): 2_296,
    ("washington_dc", "childcare"): 452,
}

# Rows dated in the 90 days before 2026-09-30, for newest-first windows.
WINDOW_RECENT_ROWS = {
    ("allentown", "deeds"): 304,
    ("anaheim", "sla"): 322,
    ("asheville", "deeds"): 2_653,
    ("aurora", "sla"): 238,
    ("baltimore", "deeds"): 2_459,
    ("baton_rouge", "sla"): 344,
    ("charleston_wv", "deeds"): 3,
    ("chattanooga", "deeds"): 1_661,
    ("cleveland", "deeds"): 3_509,
    ("durham", "deeds"): 574,
    ("frederick", "deeds"): 270,
    ("glendale_az", "sla"): 518,
    ("henderson", "sla"): 579,
    ("miami_dade", "sla"): 2_128,
    ("montgomery", "deeds"): 2_042,
    ("oxnard_ventura", "sla"): 3_839,
    ("prince_georges", "deeds"): 1_231,
    ("providence", "deeds"): 791,
    ("raleigh", "deeds"): 3_240,
    ("san_diego", "sla"): 2_275,
    ("tucson", "sla"): 2,
}

KNOWN_GAPS = {
    ("kansas_city", "sla"): "28,245 rows and no date to window on (only a text licence year)",
    ("boston", "deeds"): (
        "the id is the CKAN package, not a resource (404); the FY2026 resource has "
        "no coordinates and none of the mapped column names"
    ),
    ("ocala", "permits"): (
        "the statewide cadastral polygon layer now requires a token (499), and "
        "CO_NO 42 is Jackson County (FDOR numbers Marion 52)"
    ),
    ("orlando", "permits"): (
        "the statewide cadastral polygon layer now requires a token (499), and "
        "CO_NO 48 is Levy County (FDOR numbers Orange 58)"
    ),
}


def _key_id(key):
    return ":".join(key)


def _spec(key):
    city, feed = key
    return REGISTRY[CityId(city)].datasets[FeedType(feed)]


def _polled_snapshots():
    """Every snapshot spec the scheduler polls, SNAP retailers aside."""
    return {
        (city_id.value, feed.value)
        for city_id, reg in REGISTRY.items()
        for feed, ds in reg.datasets.items()
        if ds.ingestion_mode == "snapshot"
        and ds.platform != "gbfs"
        and ds.endpoint != settings.arcgis_snap_retailers_url
    }


def test_every_snapshot_feed_is_classified():
    """A new snapshot feed has to say how it reaches its rows, with a count."""
    groups = (set(FULL_READ_ROWS), set(WINDOW_RECENT_ROWS), set(KNOWN_GAPS))
    assert not (groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2])
    assert _polled_snapshots() == groups[0] | groups[1] | groups[2]


@pytest.mark.parametrize("key", sorted(FULL_READ_ROWS), ids=_key_id)
def test_full_read_cap_clears_the_table(key):
    rows = FULL_READ_ROWS[key]
    spec = _spec(key)
    assert (spec.batch_limit or DEFAULT_CAP) >= 1.5 * rows
    # A cap is declared only where the default falls short.
    assert (spec.batch_limit is None) == (1.5 * rows <= DEFAULT_CAP)


@pytest.mark.parametrize("key", sorted(WINDOW_RECENT_ROWS), ids=_key_id)
def test_window_reads_newest_first_and_holds_ninety_days(key):
    recent = WINDOW_RECENT_ROWS[key]
    spec = _spec(key)
    assert _NEWEST_FIRST.match(spec.order_by or ""), spec.order_by
    if spec.watermark_col:
        # The window runs on the date the feed already tracks.
        assert spec.order_by.split()[0] == spec.watermark_col
    assert (spec.batch_limit or DEFAULT_CAP) >= 1.5 * recent
    assert (spec.batch_limit is None) == (1.5 * recent <= DEFAULT_CAP)


@pytest.mark.parametrize("key", sorted(WINDOW_RECENT_ROWS), ids=_key_id)
def test_window_that_spans_pages_breaks_ties(key):
    """Paging a date sort is only stable with a unique second term; many rows
    share a sale or issue date. CSV sources sort in memory, so they are exempt."""
    spec = _spec(key)
    if (spec.batch_limit or DEFAULT_CAP) <= DEFAULT_CAP or spec.platform == "csv":
        return
    terms = [term.strip() for term in spec.order_by.split(",")]
    assert len(terms) == 2, spec.order_by
    tiebreak = terms[1].split()[0]
    assert tiebreak == (":id" if spec.platform == "socrata" else spec.oid_field)


@pytest.mark.parametrize("key", sorted({**FULL_READ_ROWS, **WINDOW_RECENT_ROWS}), ids=_key_id)
def test_multi_page_poll_runs_at_most_every_half_hour(key):
    """A poll that reads more than one page runs at most every 30 minutes, so
    the extra pages do not multiply the load on the source (every one of these
    sources updates daily at the most). A CSV source is one download a poll."""
    spec = _spec(key)
    cap = spec.batch_limit or DEFAULT_CAP
    rows_read = min(cap, FULL_READ_ROWS[key]) if key in FULL_READ_ROWS else cap
    if spec.platform == "csv" or rows_read <= DEFAULT_CAP:
        return
    assert spec.interval_seconds >= 1800.0


def test_raleigh_window_skips_parcels_without_a_sale():
    """Wake County sorts null sale dates first under DESC; without the guard
    the window fills with parcels that never sold."""
    assert _spec(("raleigh", "deeds")).where == "SALE_DATE IS NOT NULL"


def test_cleveland_window_is_bounded_to_recent_transfers():
    """Sorting all 162,874 Cuyahoga parcels by transfer date outlasts the
    client's 30-second timeout; bounding the sort to 180 days answers in
    seconds and still holds more than the window."""
    spec = _spec(("cleveland", "deeds"))
    assert spec.where == "last_transfer_date >= CURRENT_DATE - INTERVAL '180' DAY"


@pytest.mark.parametrize("key", sorted(KNOWN_GAPS), ids=_key_id)
def test_known_gap_is_still_unfixed(key):
    """A gap that gains a window or a cap moves to its table with a count."""
    spec = _spec(key)
    assert spec.batch_limit is None, KNOWN_GAPS[key]
    assert not _NEWEST_FIRST.match(spec.order_by or ""), KNOWN_GAPS[key]
