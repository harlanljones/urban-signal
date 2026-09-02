"""Tests for the CalEnviroScreen 5.0 → H3 res-8 crosswalk client.

Tests parsing and H3-tagging of a fixture row; the live fetch is marked
@pytest.mark.live and is never run by the default test suite.
"""


import pytest

from src.producers.calenviroscreen_client import (
    _load_centroids,
    _resolve_tract_h3,
    parse_csv_bytes,
)

# A CES 5.0 CSV row (Berkeley tract 6001400100, Alameda County)
_FIXTURE_CSV = (
    "tract,zipcode,approx_loc,county,region,ACS2024Pop,CIscore,CIscoreP,"
    "ozone,ozoneP,pm,pmP,diesel,dieselP,pest,pestP,RSEIhaz,RSEIhazP,"
    "traffic,trafficP,drink,drinkP,lead,leadP,cleanups,cleanupsP,"
    "gwthreats,gwthreatsP,haz,hazP,iwb,iwbP,swis,swisP,SmATS,SmATSP,"
    "Pollution,PollutionS,PollutionP,asthma,asthmaP,lbw,lbwP,cvd,cvdP,"
    "diabetes,diabetesP,edu,eduP,ling,lingP,pov,povP,unemp,unempP,"
    "housingB,housingBP,PopChar,PopCharSco,PopCharP,pop_und10,pop_10_64,"
    "pop_ov64,hisp,white,black,amind,asian,pacisl,othmult\n"
    "6001400100,94720,Berkeley,Alameda,Bay Area,3132,7.44202244437926,"
    "5.76774050702978,0.02857946698,5.71052053591039,6.882156052,"
    "12.8706347463211,0.097241556,66.5604045289656,0,0,575.7389933,"
    "55.1096902215853,539.417,60.3495657909201,2.836099813,"
    "3.57260635374299,17.7705902853367,16.0825199645075,0.9,"
    "11.4164904862579,8.5,42.1068075117371,4.375,94.3125734430082,3,"
    "28.5067084857989,0.5,19.6480406386067,38.15,31.0170633138752,"
    "30.9661998384563,3.75832701931293,18.4713375796178,17.74,"
    "10.415518571586,6.84,76.10559566787,7.32,4.83480176211454,9.8,"
    "27.8280044101433,0,0,0.598354525056096,2.35984666986104,"
    "7.36707238949391,6.02809423736312,3.97982062780269,"
    "25.7870730893314,7.63636363636364,8.3370288248337,"
    "19.1491943336032,1.98014233624081,5.63489427654157,10.86,59,"
    "30.14,6.83,65.49,4.98,0,17.37,0,5.33\n"
)

_FIXTURE_CENTROIDS = {"6001400100": (37.861751, -122.23152)}


def test_load_centroids_returns_valid_lookup():
    centroids = _load_centroids()
    assert len(centroids) > 9000
    # Berkeley tract
    lat, lng = centroids["6001400100"]
    assert 37.0 < lat < 38.0
    assert -123.0 < lng < -122.0


def test_resolve_tract_h3_returns_res8_cell():
    h3_tags = _resolve_tract_h3("6001400100", _FIXTURE_CENTROIDS)
    assert h3_tags is not None
    # Berkeley tract center should be in a valid H3 res-8 cell
    h8 = h3_tags["h3_res8"]
    assert h8.startswith("8")  # H3 hex IDs start with the res prefix digit
    # Res-8 cells are hex strings of length 15
    assert len(h8) == 15
    # Res-7 parent is a valid parent
    assert h3_tags["h3_res7"] is not None
    assert len(h3_tags["h3_res7"]) == 15


def test_resolve_tract_h3_unknown_returns_none():
    assert _resolve_tract_h3("999999999999", _FIXTURE_CENTROIDS) is None


def test_parse_csv_bytes_returns_readings():
    centroids = _FIXTURE_CENTROIDS
    readings = parse_csv_bytes(_FIXTURE_CSV.encode("utf-8"), centroids)
    assert len(readings) == 1
    r = readings[0]
    assert r.source == "calenviroscreen"
    assert r.metric == "ci_score"
    assert r.asset_id == "6001400100"
    assert r.h3_res8 is not None
    assert r.extra["ci_score_pct"] == 5.76774050702978
    assert r.extra["ozone_pct"] == 5.71052053591039
    assert r.extra["poverty_pct"] == 6.02809423736312
    assert r.extra["county"] == "Alameda"


def test_parse_csv_bytes_max_records():
    read = parse_csv_bytes(_FIXTURE_CSV.encode("utf-8"), _FIXTURE_CENTROIDS, max_records=0)
    assert len(read) == 0


def test_parse_csv_bytes_unknown_tract_skipped():
    raw = _FIXTURE_CSV.replace("6001400100", "999999999999")
    read = parse_csv_bytes(raw.encode("utf-8"), _FIXTURE_CENTROIDS)
    assert len(read) == 0


@pytest.mark.live
def test_live_fetch_resolves_berkeley():
    """End-to-end live fetch of the CES CSV — verify the URL is reachable.
    Skipped by default; run with ``pytest -m live``.
    """
    import httpx

    from src.producers.calenviroscreen_client import CalEnviroScreenClient

    client = CalEnviroScreenClient(httpx.Client(timeout=120.0, follow_redirects=True))
    readings = client.fetch(max_records=10)
    assert len(readings) >= 1
    assert readings[0].source == "calenviroscreen"