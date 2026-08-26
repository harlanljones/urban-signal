"""Unit and integration tests for FastAPI serving endpoints."""

import asyncio

import httpx
import pytest
from src.serving.app import create_app


class SyncASGIClient:
    """Small synchronous adapter for HTTPX's async ASGI transport."""

    def __init__(self, app):
        self._app = app

    def request(self, method, url, **kwargs):
        async def send():
            transport = httpx.ASGITransport(app=self._app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
                follow_redirects=True,
            ) as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(send())

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)


app = create_app()
client = SyncASGIClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "prediction_requests_total" in response.text


def test_root_metadata():
    """Verify root / serves operational JSON metadata by default."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "dashboard_url" in data


def test_root_dashboard_html():
    """Verify root / serves HTML dashboard when requested with text/html Accept header."""
    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Urban Signal" in response.text
    assert "maplibre" in response.text
    assert "LIMS" in response.text


def test_dashboard_endpoint():
    """Verify /dashboard endpoint serves the geospatial visualization dashboard with 200 OK."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Geospatial Intelligence Dashboard" in response.text
    assert "Real-Time Catalyst Alerts" in response.text


def test_predict_single_coordinate():
    payload = {
        "latitude": 40.7250,
        "longitude": -73.9970,
        "resolution": 9,
        "include_shap": True,
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "h3_index" in data
    assert "lims_score" in data
    assert "delta_6m_p50" in data
    assert "delta_12m_spillover" in data
    assert "prob_18m_macro_outperformance" in data
    assert "shap_attributions" in data
    assert data["inference_latency_ms"] >= 0.0


def test_predict_single_h3_index():
    payload = {
        "h3_index": "892a1072893ffff",
        "resolution": 9,
        "include_shap": False,
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["h3_index"] == "892a1072893ffff"
    assert data["shap_attributions"] is None


def test_catalysts_endpoint():
    response = client.get("/api/v1/catalysts?min_lims=85.0")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "catalysts" in data
    assert isinstance(data["catalysts"], list)
    assert data["count"] >= 1


def test_grid_geojson_endpoint():
    """Verify /api/v1/grid returns valid GeoJSON FeatureCollection covering NYC submarkets."""
    response = client.get("/api/v1/grid?resolution=9&k_ring=1")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert len(data["features"]) > 0

    first_feat = data["features"][0]
    assert first_feat["type"] == "Feature"
    assert "geometry" in first_feat
    assert first_feat["geometry"]["type"] == "Polygon"
    assert "properties" in first_feat
    assert "submarket" in first_feat["properties"]
    assert "lims_score" in first_feat["properties"]
    assert "delta_6m_p50" in first_feat["properties"]


def test_hex_feature_inspection():
    response = client.get("/api/v1/hex/892a1072893ffff/features")
    assert response.status_code == 200
    data = response.json()
    assert data["h3_index"] == "892a1072893ffff"
    assert "features" in data
    assert "boundary_geojson" in data


def test_submarkets_all():
    """Verify /api/v1/submarkets returns all 5-borough submarkets."""
    response = client.get("/api/v1/submarkets")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "submarkets" in data
    assert data["count"] >= 50
    assert "SoHo" in data["submarkets"]
    assert "Williamsburg" in data["submarkets"]
    assert "Astoria" in data["submarkets"]
    assert "Mott Haven" in data["submarkets"]
    assert "St. George" in data["submarkets"]

    soho_meta = data["submarkets"]["SoHo"]
    assert soho_meta["borough"] == "MANHATTAN"
    assert "lat" in soho_meta and "lng" in soho_meta
    assert "base_lims" in soho_meta
    assert soho_meta["base_lims"] >= 0.0


def test_submarkets_borough_filter():
    """Verify /api/v1/submarkets?borough= filters correctly for Manhattan, Bronx, and Staten Island."""
    # Manhattan
    res_m = client.get("/api/v1/submarkets?borough=MANHATTAN")
    assert res_m.status_code == 200
    data_m = res_m.json()
    assert data_m["borough"] == "MANHATTAN"
    assert data_m["count"] >= 10
    for name, meta in data_m["submarkets"].items():
        assert meta["borough"] == "MANHATTAN"
    assert "SoHo" in data_m["submarkets"]
    assert "Williamsburg" not in data_m["submarkets"]

    # Bronx
    res_bx = client.get("/api/v1/submarkets?borough=BRONX")
    assert res_bx.status_code == 200
    data_bx = res_bx.json()
    assert data_bx["borough"] == "BRONX"
    assert data_bx["count"] >= 5
    for name, meta in data_bx["submarkets"].items():
        assert meta["borough"] == "BRONX"
    assert "Mott Haven" in data_bx["submarkets"]

    # Staten Island
    res_si = client.get("/api/v1/submarkets?borough=STATEN_ISLAND")
    assert res_si.status_code == 200
    data_si = res_si.json()
    assert data_si["borough"] == "STATEN_ISLAND"
    assert data_si["count"] >= 4
    for name, meta in data_si["submarkets"].items():
        assert meta["borough"] == "STATEN_ISLAND"
    assert "St. George" in data_si["submarkets"]


def test_grid_borough_filter():
    """Verify /api/v1/grid?borough=BROOKLYN filters hex grid exclusively to Brooklyn."""
    response = client.get("/api/v1/grid?borough=BROOKLYN&k_ring=1")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0
    for feat in data["features"]:
        props = feat["properties"]
        assert props["borough"] == "BROOKLYN"
        assert "submarket" in props
        assert "lims_score" in props


def test_grid_submarket_filter():
    """Verify /api/v1/grid?submarket=Astoria filters hex grid exclusively to Astoria."""
    response = client.get("/api/v1/grid?submarket=Astoria&k_ring=1")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0
    for feat in data["features"]:
        props = feat["properties"]
        assert props["submarket"] == "Astoria"
        assert props["borough"] == "QUEENS"

    # Non-existent submarket should return 404
    err_res = client.get("/api/v1/grid?submarket=UnknownPlace999")
    assert err_res.status_code == 404


def test_catalysts_borough_filter():
    """Verify /api/v1/catalysts?borough=QUEENS returns high-momentum catalysts in Queens."""
    response = client.get("/api/v1/catalysts?borough=QUEENS&min_lims=75.0")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "catalysts" in data
    assert data["count"] >= 1
    assert data["borough"] == "QUEENS"
    for cat in data["catalysts"]:
        assert cat["borough"] == "QUEENS"
        assert cat["lims_score"] >= 75.0


def test_cities_endpoint():
    """Verify /api/v1/cities returns catalog of registered metropolitan regions."""
    response = client.get("/api/v1/cities")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert data["count"] >= 2
    assert "cities" in data
    assert "nyc" in data["cities"]
    assert "chicago" in data["cities"]

    chi = data["cities"]["chicago"]
    assert chi["name"] == "Chicago"
    assert chi["state"] == "IL"
    assert chi["submarkets_count"] >= 30
    assert chi["divisions_count"] == 6


def test_submarkets_chicago():
    """Verify /api/v1/submarkets?city_id=chicago returns Chicago submarkets."""
    response = client.get("/api/v1/submarkets?city_id=chicago")
    assert response.status_code == 200
    data = response.json()
    assert data["city_id"] == "chicago"
    assert data["count"] >= 30
    assert "Fulton Market" in data["submarkets"]
    assert "Logan Square" in data["submarkets"]
    assert "Pilsen" in data["submarkets"]

    # Filter by division
    res_div = client.get("/api/v1/submarkets?city_id=chicago&borough=NORTHWEST_SIDE")
    assert res_div.status_code == 200
    data_div = res_div.json()
    assert data_div["borough"] == "NORTHWEST_SIDE"
    assert "Logan Square" in data_div["submarkets"]
    assert "Wicker Park" in data_div["submarkets"]


def test_grid_chicago():
    """Verify /api/v1/grid?city_id=chicago returns GeoJSON FeatureCollection for Chicago."""
    response = client.get("/api/v1/grid?city_id=chicago&resolution=9&k_ring=1")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert data["city_id"] == "chicago"
    assert len(data["features"]) > 0

    # Test submarket filter
    res_sm = client.get("/api/v1/grid?city_id=chicago&submarket=Fulton Market")
    assert res_sm.status_code == 200
    data_sm = res_sm.json()
    assert len(data_sm["features"]) > 0
    assert data_sm["features"][0]["properties"]["submarket"] == "Fulton Market"


def test_catalysts_chicago():
    """Verify /api/v1/catalysts?city_id=chicago returns Chicago catalysts."""
    response = client.get("/api/v1/catalysts?city_id=chicago&min_lims=80.0")
    assert response.status_code == 200
    data = response.json()
    assert data["city_id"] == "chicago"
    assert data["count"] >= 1
    for cat in data["catalysts"]:
        assert cat["city_id"] == "chicago"
        assert cat["lims_score"] >= 80.0


def test_predict_chicago_coordinate():
    """Verify real-time prediction for Chicago Fulton Market coordinates."""
    payload = {
        "latitude": 41.8860,
        "longitude": -87.6520,
        "resolution": 9,
        "include_shap": True,
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "h3_index" in data
    assert "lims_score" in data
    assert "delta_6m_p50" in data
    assert data["inference_latency_ms"] >= 0.0


def test_submarkets_san_francisco_and_alias():
    """Verify /api/v1/submarkets handles city_id=san_francisco and alias city_id=sf."""
    for cid in ("san_francisco", "sf"):
        response = client.get(f"/api/v1/submarkets?city_id={cid}")
        assert response.status_code == 200
        data = response.json()
        assert data["city_id"] == "san_francisco"
        assert data["count"] >= 35
        assert "Downtown" in data["submarkets"] or "Mission" in data["submarkets"] or "SoMa" in data["submarkets"]

    # Filter by division
    res_div = client.get("/api/v1/submarkets?city_id=sf&borough=SAN_FRANCISCO_CORE")
    assert res_div.status_code == 200
    data_div = res_div.json()
    assert data_div["borough"] == "SAN_FRANCISCO_CORE"
    assert data_div["count"] >= 10
    assert "Mission" in data_div["submarkets"] or "SoMa" in data_div["submarkets"]


def test_spatial_divisions_endpoint():
    """Verify /api/v1/spatial/divisions returns division catalog for SF, Chicago, NYC."""
    # San Francisco & alias
    for cid in ("san_francisco", "sf"):
        res = client.get(f"/api/v1/spatial/divisions?city_id={cid}")
        assert res.status_code == 200
        data = res.json()
        assert data["city_id"] == "san_francisco"
        assert data["count"] == 5
        assert "SAN_FRANCISCO_CORE" in data["divisions"]
        assert "EAST_BAY" in data["divisions"]
        assert "PENINSULA" in data["divisions"]
        assert "SILICON_VALLEY_SOUTH_BAY" in data["divisions"]
        assert "MARIN_NORTH_BAY" in data["divisions"]

    # NYC
    res_nyc = client.get("/api/v1/spatial/divisions?city_id=nyc")
    assert res_nyc.status_code == 200
    assert res_nyc.json()["count"] == 5

    # Chicago
    res_chi = client.get("/api/v1/spatial/divisions?city_id=chicago")
    assert res_chi.status_code == 200
    assert res_chi.json()["count"] == 6


def test_submarket_prediction_endpoint():
    """Verify /api/v1/predictions/submarket/{name} resolves predictions correctly."""
    # SF submarket
    res = client.get("/api/v1/predictions/submarket/Mission?city_id=sf")
    assert res.status_code == 200
    data = res.json()
    assert data["submarket"] == "Mission"
    assert data["borough"] == "SAN_FRANCISCO_CORE"
    assert "lims_score" in data
    assert "delta_6m_p50" in data
    assert "h3_index" in data

    # NYC submarket
    res_nyc = client.get("/api/v1/predictions/submarket/SoHo?city_id=nyc")
    assert res_nyc.status_code == 200
    assert res_nyc.json()["submarket"] == "SoHo"

    # Non-existent submarket
    res_404 = client.get("/api/v1/predictions/submarket/NonExistentPlace999")
    assert res_404.status_code == 404


def test_dashboard_metrics_endpoint():
    """Verify /api/v1/dashboard/metrics returns aggregated metrics for SF, Chicago, NYC."""
    for cid in ("san_francisco", "sf"):
        res = client.get(f"/api/v1/dashboard/metrics?city_id={cid}")
        assert res.status_code == 200
        data = res.json()
        assert data["city_id"] == "san_francisco"
        assert data["submarkets_count"] >= 35
        assert data["divisions_count"] == 5
        assert data["avg_lims_score"] > 0
        assert data["total_capex"] > 0
        assert len(data["top_momentum_submarkets"]) > 0

    res_nyc = client.get("/api/v1/dashboard/metrics?city_id=nyc")
    assert res_nyc.status_code == 200
    assert res_nyc.json()["divisions_count"] == 5


def test_grid_san_francisco():
    """Verify /api/v1/grid?city_id=san_francisco returns FeatureCollection."""
    res = client.get("/api/v1/grid?city_id=sf&resolution=9&k_ring=1")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert data["city_id"] == "san_francisco"
    assert len(data["features"]) > 0


def test_catalysts_san_francisco():
    """Verify /api/v1/catalysts?city_id=sf returns active catalysts."""
    res = client.get("/api/v1/catalysts?city_id=sf&min_lims=80.0")
    assert res.status_code == 200
    data = res.json()
    assert data["city_id"] == "san_francisco"
    assert data["count"] >= 1
    for cat in data["catalysts"]:
        assert cat["city_id"] == "san_francisco"


def test_dashboard_html_sf_integration():
    """Verify dashboard HTML includes San Francisco Bay Area metro metadata."""
    res = client.get("/dashboard")
    assert res.status_code == 200
    html = res.text
    assert "san_francisco: { name: 'San Francisco Bay Area' }" in html
    assert 'id="metro-chips"' in html
    assert "renderMetroChips" in html
    assert "selectMetro" in html


def test_dashboard_shows_all_metros_without_city_selection():
    """The national map renders every metro at once: the per-city selector and
    the compare menu are gone, replaced by navigation-only metro chips."""
    res = client.get("/dashboard")
    assert res.status_code == 200
    html = res.text

    # Selection/comparison machinery is fully removed.
    for removed in (
        'id="city-select"',
        "changeCity(",
        'id="compare-options"',
        "renderCompareOptions",
        "COMPARE_RADIUS_MILES",
        "applyComparison",
    ):
        assert removed not in html

    # Metro chips are present and are navigation, not data scoping.
    assert 'id="metro-chips"' in html
    assert "activeMetroChip" in html
    assert "fitNationalView" in html


def test_dashboard_html_national_view_and_lazy_tiles():
    """Verify the dashboard boots into a CONUS-wide view and lazy-loads cells
    from res-5 viewport tiles instead of fetching whole-city grids."""
    res = client.get("/dashboard")
    assert res.status_code == 200
    html = res.text

    # National camera + zoom floor hint.
    assert "-96.6, 38.9" in html
    assert "ZOOM_FLOOR" in html
    assert 'id="zoom-hint"' in html

    # Viewport-driven tile loading against the manifest tile index.
    assert "updateViewportTiles" in html
    assert "/api/v1/gridtiles?parents=" in html
    assert "snapshotManifest.tile_index" in html
    assert "fetchManifest" in html

    # Whole-city grid fetches no longer happen from the client.
    assert "/api/v1/grid?" not in html

    # Deep links stay valid as camera presets (product site links to them).
    assert "deepLinkedCity" in html

    # No geolocation prompt: everyone lands on the national view.
    assert "navigator.geolocation" not in html
    assert "detectUserDefaultCity" not in html


def test_dashboard_html_normalizes_cross_metro_metrics():
    """Map paints read build-time percentile ranks so 27 metros share one
    comparable color scale; raw scores remain visible in tooltips."""
    res = client.get("/dashboard")
    assert res.status_code == 200
    html = res.text

    assert "lims_score_national_pct" in html
    assert "National Pct:" in html
    assert "Metro Pct:" in html
    # Raw-only ramps are gone from layer paints.
    assert "['get', 'lims_score']" not in html


def test_unknown_city_rejection_400():
    """Verify endpoints reject unknown/unsupported city_id with HTTP 400 Bad Request."""
    res1 = client.get("/api/v1/submarkets?city_id=atlanta")
    assert res1.status_code == 400
    assert "Unsupported city_id" in res1.json()["detail"]

    res2 = client.get("/api/v1/grid?city_id=london")
    assert res2.status_code == 400
    assert "Unsupported city_id" in res2.json()["detail"]

    res3 = client.get("/api/v1/catalysts?city_id=tokyo")
    assert res3.status_code == 400

    res4 = client.get("/api/v1/dashboard/metrics?city_id=atlantis")
    assert res4.status_code == 400


def test_no_cross_city_leakage():
    """Verify /grid and /predictions/submarket do not leak submarkets across cities."""
    # Wicker Park is in Chicago, not San Francisco -> 404
    res_grid = client.get("/api/v1/grid?city_id=sf&submarket=Wicker Park")
    assert res_grid.status_code == 404

    res_pred = client.get("/api/v1/predictions/submarket/Wicker Park?city_id=sf")
    assert res_pred.status_code == 404

    # Financial District resolves correctly within respective city
    res_sf_fd = client.get("/api/v1/predictions/submarket/Financial District?city_id=sf")
    assert res_sf_fd.status_code == 200
    assert res_sf_fd.json()["city_id"] == "san_francisco"
    assert res_sf_fd.json()["borough"] == "SAN_FRANCISCO_CORE"

    res_nyc_fd = client.get("/api/v1/predictions/submarket/Financial District?city_id=nyc")
    assert res_nyc_fd.status_code == 200
    assert res_nyc_fd.json()["city_id"] == "nyc"
    assert res_nyc_fd.json()["borough"] == "MANHATTAN"

    # Chinatown exists in Chicago and NYC, not SF
    res_chi_ct = client.get("/api/v1/predictions/submarket/Chinatown?city_id=chicago")
    assert res_chi_ct.status_code == 200
    assert res_chi_ct.json()["city_id"] == "chicago"
    assert res_chi_ct.json()["borough"] == "SOUTH_SIDE"

    res_nyc_ct = client.get("/api/v1/predictions/submarket/Chinatown?city_id=nyc")
    assert res_nyc_ct.status_code == 200
    assert res_nyc_ct.json()["city_id"] == "nyc"
    assert res_nyc_ct.json()["borough"] == "MANHATTAN"
