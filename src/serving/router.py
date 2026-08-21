"""FastAPI router endpoints for real-time predictions, catalyst queries, and health checks."""

from dataclasses import asdict
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from src.features.pipeline import SpatialFeaturePipeline
from src.schemas.models import PredictionRequest, PredictionResponse
from src.serving.engine import MultiHorizonInferenceEngine
from src.spatial.city_registry import CityId, REGISTRY, normalize_city
from src.spatial.geo_utils import get_borough_for_coordinate
from src.spatial.h3_indexer import H3SpatialIndexer
from src.spatial.submarkets import (
    NYC_BOROUGHS,
    NYC_SUBMARKETS as SPATIAL_NYC_SUBMARKETS,
    SubmarketMeta,
    get_all_submarkets,
    get_city_catalog,
    get_division_catalog,
    get_submarket_by_name,
    get_submarkets,
)

router = APIRouter()
indexer = H3SpatialIndexer()

# Shared singleton instances (injected via app state or lazy init)
_inference_engine: Optional[MultiHorizonInferenceEngine] = None
_feature_pipeline: Optional[SpatialFeaturePipeline] = None


def _get_validated_city_id(
    city_id: Optional[str], default: str = "nyc", allow_all: bool = False
) -> str:
    """Validate and normalize city identifier, raising HTTP 400 on unknown."""
    if not city_id:
        return default
    c = str(city_id).strip().lower()
    if allow_all and c in ("all", "*"):
        return "all"
    cid = normalize_city(c)
    if cid is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported city_id '{city_id}'. Supported cities: {[c.value for c in CityId]}.",
        )
    return cid.value


def _normalize_city(city_id: Optional[str]) -> str:
    """Backward-compatible wrapper for city normalization."""
    return _get_validated_city_id(city_id, default="nyc", allow_all=True)


def _normalize_lims(val: float) -> float:
    """Normalize LIMS score to [0, 100] scale if given in [0, 1]."""
    if val <= 1.0:
        return round(val * 100.0, 2)
    return round(val, 2)


def _submarket_to_dict(meta: Any) -> Dict[str, Any]:
    """Convert SubmarketMeta or dict to standard dictionary with normalized base_lims."""
    if hasattr(meta, "__dataclass_fields__"):
        d = asdict(meta)
    elif isinstance(meta, dict):
        d = dict(meta)
    else:
        d = {
            "name": getattr(meta, "name", ""),
            "borough": getattr(meta, "borough", ""),
            "lat": getattr(meta, "lat", 0.0),
            "lng": getattr(meta, "lng", 0.0),
            "zoom": getattr(meta, "zoom", 14.5),
            "pitch": getattr(meta, "pitch", 45.0),
            "base_lims": getattr(meta, "base_lims", 80.0),
            "capex": getattr(meta, "capex", 500000.0),
            "permit_vel": getattr(meta, "permit_vel", 0.35),
            "shift_ratio": getattr(meta, "shift_ratio", 2.5),
            "sla": getattr(meta, "sla", 3),
            "description": getattr(meta, "description", ""),
            "city_id": getattr(meta, "city_id", "nyc"),
        }
    d["base_lims"] = _normalize_lims(float(d.get("base_lims", 80.0)))
    return d


# Reference NYC commercial submarkets for backward compatibility
NYC_SUBMARKETS: Dict[str, Dict[str, Any]] = {
    name: _submarket_to_dict(meta)
    for name, meta in SPATIAL_NYC_SUBMARKETS.items()
}


def get_inference_engine() -> MultiHorizonInferenceEngine:
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = MultiHorizonInferenceEngine()
    return _inference_engine


def get_feature_pipeline() -> SpatialFeaturePipeline:
    global _feature_pipeline
    if _feature_pipeline is None:
        _feature_pipeline = SpatialFeaturePipeline()
    return _feature_pipeline


@router.get("/cities")
async def list_cities():
    """Retrieve catalog of all supported metropolitan regions."""
    catalog = get_city_catalog()
    return {
        "count": len(catalog),
        "cities": catalog,
    }


@router.get("/submarkets")
async def list_submarkets(
    city_id: Optional[str] = Query(default="nyc", description="City identifier ('nyc', 'chicago', or 'san_francisco' / 'sf')"),
    borough: Optional[str] = Query(default=None, description="Optional borough/division filter (e.g. MANHATTAN, CENTRAL_DOWNTOWN, SAN_FRANCISCO_CORE)"),
):
    """Retrieve metadata for submarkets, optionally filtered by city and borough/division."""
    norm_city = _get_validated_city_id(city_id, default="nyc", allow_all=True)
    filtered = get_submarkets(city_id=norm_city, borough_or_division=borough)
    result = {name: _submarket_to_dict(meta) for name, meta in filtered.items()}
    return {
        "city_id": norm_city,
        "count": len(result),
        "borough": borough.upper() if borough else None,
        "submarkets": result,
    }


@router.get("/spatial/divisions")
async def list_spatial_divisions(
    city_id: Optional[str] = Query(default="nyc", description="City identifier ('nyc', 'chicago', or 'san_francisco' / 'sf')"),
):
    """Retrieve structured catalog of all divisions/boroughs for the specified metropolitan region."""
    norm_city = _get_validated_city_id(city_id, default="nyc")
    divisions = get_division_catalog(city_id=norm_city)
    return {
        "city_id": norm_city,
        "count": len(divisions),
        "divisions": divisions,
    }


@router.post("/predict", response_model=PredictionResponse, status_code=status.HTTP_200_OK)
async def predict_single(
    request: PredictionRequest,
    engine: MultiHorizonInferenceEngine = Depends(get_inference_engine),
    pipeline: SpatialFeaturePipeline = Depends(get_feature_pipeline),
):
    """Real-time multi-horizon property value appreciation prediction for a coordinate or H3 cell."""
    # Resolve H3 index with validation
    if request.h3_index:
        h3_cell = request.h3_index.strip()
    elif request.latitude is not None and request.longitude is not None:
        if not (-90.0 <= request.latitude <= 90.0 and -180.0 <= request.longitude <= 180.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Coordinates out of bounds: latitude ({request.latitude}) must be [-90, 90], longitude ({request.longitude}) must be [-180, 180].",
            )
        h3_cell = indexer.latlng_to_h3(request.latitude, request.longitude, resolution=request.resolution)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'h3_index' or ('latitude', 'longitude').",
        )

    # Pull current features for cell
    feat_dict = pipeline.compute_h3_cell_features(h3_cell, resolution=request.resolution, as_of_date=None)

    # Run inference
    result = engine.predict_cell_features(
        h3_index=h3_cell,
        feature_dict=feat_dict,
        include_shap=request.include_shap,
    )

    return PredictionResponse(**result)


@router.post("/predict/batch", response_model=List[PredictionResponse])
async def predict_batch(
    requests: List[PredictionRequest],
    engine: MultiHorizonInferenceEngine = Depends(get_inference_engine),
    pipeline: SpatialFeaturePipeline = Depends(get_feature_pipeline),
):
    """Batch prediction across multiple spatial coordinates / H3 cells."""
    responses = []
    for req in requests:
        if req.h3_index:
            h3_cell = req.h3_index.strip()
        elif req.latitude is not None and req.longitude is not None:
            if not (-90.0 <= req.latitude <= 90.0 and -180.0 <= req.longitude <= 180.0):
                continue
            h3_cell = indexer.latlng_to_h3(req.latitude, req.longitude, resolution=req.resolution)
        else:
            continue

        feat_dict = pipeline.compute_h3_cell_features(h3_cell, resolution=req.resolution, as_of_date=None)
        res = engine.predict_cell_features(h3_cell, feat_dict, include_shap=req.include_shap)
        responses.append(PredictionResponse(**res))

    return responses


@router.get("/catalysts")
async def get_active_catalysts(
    city_id: Optional[str] = Query(default="nyc", description="City identifier ('nyc', 'chicago', 'san_francisco', 'sf')"),
    min_lims: float = Query(default=85.0, ge=0.0, le=100.0),
    resolution: int = Query(default=9, ge=7, le=9),
    borough: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    engine: MultiHorizonInferenceEngine = Depends(get_inference_engine),
):
    """Retrieve current top high-momentum catalyst clusters across metropolitan divisions."""
    catalysts = []
    seen_cells = set()
    norm_city = _get_validated_city_id(city_id, default="nyc")

    # Target submarkets for catalyst search
    submarkets_map = get_submarkets(city_id=norm_city, borough_or_division=borough)
    norm_borough = borough.strip().upper().replace(" ", "_").replace("-", "_") if borough else None

    # Evaluate submarket centers and adjacent k-ring cells
    for sm_name, meta in submarkets_map.items():
        if len(catalysts) >= limit:
            break
        meta_dict = _submarket_to_dict(meta)
        center_cell = indexer.latlng_to_h3(meta_dict["lat"], meta_dict["lng"], resolution=resolution)
        cells_to_eval = [center_cell] + list(indexer.get_k_ring(center_cell, k=1))

        for idx, cell in enumerate(cells_to_eval):
            if cell in seen_cells:
                continue
            seen_cells.add(cell)
            score = max(meta_dict["base_lims"] - idx * 1.5, 0.0)
            if score >= min_lims:
                synthetic_feats = {
                    "capex_density_decayed": max(meta_dict["capex"] * (1.0 - idx * 0.05), 0.0),
                    "permit_velocity": meta_dict["permit_vel"] if meta_dict["permit_vel"] <= 1.0 else meta_dict["permit_vel"] / 100.0,
                    "shift_ratio_311": meta_dict["shift_ratio"],
                    "sla_new_filings_90d": int(meta_dict["sla"]),
                    "lims_score": score,
                }
                pred = engine.predict_cell_features(cell, synthetic_feats, include_shap=True)
                pred["submarket"] = meta_dict["name"]
                pred["borough"] = meta_dict["borough"]
                pred["city_id"] = norm_city
                catalysts.append(pred)
                if len(catalysts) >= limit:
                    break

    return {
        "city_id": norm_city,
        "count": len(catalysts[:limit]),
        "threshold": min_lims,
        "borough": norm_borough,
        "catalysts": catalysts[:limit],
    }


@router.get("/grid")
async def get_grid_geojson(
    city_id: Optional[str] = Query(default="nyc", description="City identifier ('nyc', 'chicago', 'san_francisco', 'sf')"),
    resolution: int = Query(default=9, ge=7, le=9),
    k_ring: int = Query(default=1, ge=0, le=3),
    borough: Optional[str] = Query(default=None),
    submarket: Optional[str] = Query(default=None),
    include_shap: bool = Query(default=False),
    engine: MultiHorizonInferenceEngine = Depends(get_inference_engine),
):
    """Retrieve GeoJSON FeatureCollection of H3 hex grid covering commercial submarkets with optional borough and submarket filtering."""
    features = []
    seen_cells = set()
    norm_city = _get_validated_city_id(city_id, default="nyc")

    # Determine submarket list to render
    if submarket:
        sm_meta = get_submarket_by_name(submarket, city_id=norm_city)
        if sm_meta is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Submarket '{submarket}' not found in city '{norm_city}'.",
            )
        sm_name = sm_meta.name if hasattr(sm_meta, "name") else sm_meta["name"]
        target_submarkets = {sm_name: sm_meta}
    else:
        target_submarkets = get_submarkets(city_id=norm_city, borough_or_division=borough)

    for sm_name, meta in target_submarkets.items():
        meta_dict = _submarket_to_dict(meta)
        center_cell = indexer.latlng_to_h3(meta_dict["lat"], meta_dict["lng"], resolution=resolution)
        ring_cells = indexer.get_k_ring(center_cell, k=k_ring)
        for cell in ring_cells:
            if cell in seen_cells:
                continue
            seen_cells.add(cell)
            boundary = indexer.h3_to_boundary(cell, geojson_format=True)
            if boundary and boundary[0] != boundary[-1]:
                boundary.append(boundary[0])

            synthetic_feats = {
                "capex_density_decayed": meta_dict["capex"],
                "permit_velocity": meta_dict["permit_vel"] if meta_dict["permit_vel"] <= 1.0 else meta_dict["permit_vel"] / 100.0,
                "shift_ratio_311": meta_dict["shift_ratio"],
                "sla_new_filings_90d": int(meta_dict["sla"]),
                "lims_score": meta_dict["base_lims"],
            }
            pred = engine.predict_cell_features(cell, synthetic_feats, include_shap=include_shap)
            features.append({
                "type": "Feature",
                "id": cell,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [boundary],
                },
                "properties": {
                    "submarket": meta_dict["name"],
                    "borough": meta_dict["borough"],
                    "city_id": meta_dict.get("city_id", norm_city),
                    **synthetic_feats,
                    **pred,
                },
            })

    return {
        "type": "FeatureCollection",
        "city_id": norm_city,
        "features": features,
    }


@router.get("/predictions/submarket/{name}")
async def get_submarket_prediction(
    name: str,
    city_id: Optional[str] = Query(default=None, description="Optional city identifier ('nyc', 'chicago', 'san_francisco', 'sf')"),
    include_shap: bool = Query(default=True, description="Whether to include SHAP attributions"),
    resolution: int = Query(default=9, ge=7, le=9),
    engine: MultiHorizonInferenceEngine = Depends(get_inference_engine),
):
    """Retrieve real-time property value predictions and metadata for a specific submarket by name."""
    norm_city = _get_validated_city_id(city_id) if city_id else None
    sm_meta = get_submarket_by_name(name, city_id=norm_city)
    if sm_meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submarket '{name}' not found.",
        )

    meta_dict = _submarket_to_dict(sm_meta)
    center_cell = indexer.latlng_to_h3(meta_dict["lat"], meta_dict["lng"], resolution=resolution)

    synthetic_feats = {
        "capex_density_decayed": meta_dict["capex"],
        "permit_velocity": meta_dict["permit_vel"] if meta_dict["permit_vel"] <= 1.0 else meta_dict["permit_vel"] / 100.0,
        "shift_ratio_311": meta_dict["shift_ratio"],
        "sla_new_filings_90d": int(meta_dict["sla"]),
        "lims_score": meta_dict["base_lims"],
    }
    pred = engine.predict_cell_features(center_cell, synthetic_feats, include_shap=include_shap)

    return {
        "submarket": meta_dict["name"],
        "borough": meta_dict["borough"],
        "division": meta_dict["borough"],
        "city_id": meta_dict.get("city_id", norm_city or "nyc"),
        "centroid": {"lat": meta_dict["lat"], "lng": meta_dict["lng"]},
        **meta_dict,
        **pred,
    }


@router.get("/dashboard/metrics")
async def get_dashboard_metrics(
    city_id: Optional[str] = Query(default="nyc", description="City identifier ('nyc', 'chicago', 'san_francisco', 'sf')"),
):
    """Retrieve aggregated dashboard metrics and summary statistics for a given city."""
    norm_city = _get_validated_city_id(city_id, default="nyc")
    submarkets_map = get_submarkets(city_id=norm_city)
    divisions_map = get_division_catalog(city_id=norm_city)

    submarket_dicts = [_submarket_to_dict(m) for m in submarkets_map.values()]
    avg_lims = round(sum(d["base_lims"] for d in submarket_dicts) / len(submarket_dicts), 2) if submarket_dicts else 0.0
    total_capex = sum(d["capex"] for d in submarket_dicts) if submarket_dicts else 0.0
    sorted_by_lims = sorted(submarket_dicts, key=lambda d: d["base_lims"], reverse=True)
    top_submarket = sorted_by_lims[0]["name"] if sorted_by_lims else ""

    return {
        "city_id": norm_city,
        "submarkets_count": len(submarkets_map),
        "divisions_count": len(divisions_map),
        "avg_lims_score": avg_lims,
        "total_capex": total_capex,
        "top_submarket": top_submarket,
        "divisions": list(divisions_map.keys()),
        "top_momentum_submarkets": [
            {"name": s["name"], "borough": s["borough"], "base_lims": s["base_lims"]}
            for s in sorted_by_lims[:5]
        ],
    }


@router.get("/hex/{h3_index}/features")
async def get_hex_features(
    h3_index: str,
    resolution: int = Query(default=9, ge=7, le=9),
    pipeline: SpatialFeaturePipeline = Depends(get_feature_pipeline),
):
    """Inspect raw spatio-temporal feature attributes for an individual H3 cell."""
    lat, lng = indexer.h3_to_latlng(h3_index)
    feats = pipeline.compute_h3_cell_features(h3_index, resolution=resolution, as_of_date=None)
    boundary = indexer.h3_to_boundary(h3_index, geojson_format=True)
    return {
        "h3_index": h3_index,
        "centroid": {"latitude": lat, "longitude": lng},
        "boundary_geojson": boundary,
        "features": feats,
    }
