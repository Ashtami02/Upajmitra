"""
UpajMitra Backend -- FastAPI entrypoint.

Endpoints map directly onto the 5-stage pipeline from the pitch deck:
  POST /api/predict   -> Stage 2 (Predict)
  POST /api/explain   -> Stage 3 (Explain)
  POST /api/whatif    -> Stage 4 (Recommend / What-If)
  POST /api/optimize  -> Stage 5 (Optimize, NSGA-II)
  GET  /api/meta      -> dropdown options for the frontend form (crops, soils, regions)

Run locally:
    uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import farmer_explain as farmer_explain_module
from . import locations as locations_module
from . import model as model_module
from . import optimizer as optimizer_module
from . import soil as soil_module
from . import storage as storage_module
from . import vision as vision_module
from . import weather as weather_module
from .schemas import (
    CanopyAnalysisResponse,
    ExplainResponse,
    FarmerReason,
    FarmProfile,
    OptimizeAdviceStep,
    OptimizeRequest,
    OptimizeResponse,
    ParetoPoint,
    PredictionResponse,
    SavedProfileDetail,
    SavedProfileSummary,
    SaveProfileRequest,
    ShapContribution,
    WhatIfRequest,
    WhatIfResponse,
)

app = FastAPI(title="UpajMitra API", version="0.1.0")

# Dev-friendly CORS -- tighten allow_origins before deploying beyond a hackathon demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage_module.init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    m = model_module.get_meta()
    return {
        "crops": m["crops"],
        "soil_types": m["soil_types"],
        "regions": m["regions"],
        "model_val_mape_pct": m["val_mape_pct"],
    }


@app.get("/api/locations")
def locations():
    """Farmer-friendly location picker data: districts grouped by region,
    each with a lat/lon under the hood -- so a farmer can pick their area
    by name instead of typing coordinates. See locations.py."""
    return locations_module.get_locations()


@app.get("/api/soil")
def soil(lat: float, lon: float, region: str | None = None):
    """Day 2: auto-fill soil_ph / organic_carbon_pct. Tries SoilGrids
    first, falls back to a regional estimate on any failure -- see
    soil.py docstring (SoilGrids currently has an announced outage).
    This endpoint always returns 200; check the `source` field to know
    whether you got a live reading or a regional fallback."""
    return soil_module.fetch_soil_properties(lat, lon, region=region)


@app.get("/api/weather")
def weather(lat: float, lon: float, region: str | None = None):
    """Day 2: auto-fill avg_temp_c / rainfall_mm_season. Always returns
    200; check `source` for "open-meteo" vs "regional_estimate"."""
    return weather_module.fetch_season_weather(lat, lon, region=region)


@app.post("/api/canopy-analysis", response_model=CanopyAnalysisResponse)
async def canopy_analysis(photo: UploadFile = File(...)):
    """Day 4: heuristic canopy-health read from an uploaded field photo.
    See vision.py docstring -- this is a green-pixel-ratio proxy, not a
    trained CNN. Frontend should present it as "estimated from your
    photo", not as ground truth."""
    try:
        image_bytes = await photo.read()
        return vision_module.analyze_canopy_greenness(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not analyze photo: {e}")


def _predict_response(profile: FarmProfile) -> PredictionResponse:
    profile_dict = profile.model_dump()
    yield_val = model_module.predict_yield(profile_dict)
    revenue, cost, profit = model_module.economics(profile_dict, yield_val)
    return PredictionResponse(
        predicted_yield_quintal_per_acre=round(yield_val, 2),
        estimated_revenue=round(revenue, 2),
        estimated_input_cost=round(cost, 2),
        estimated_profit=round(profit, 2),
    )


@app.post("/api/predict", response_model=PredictionResponse)
def predict(profile: FarmProfile):
    try:
        return _predict_response(profile)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/explain", response_model=ExplainResponse)
def explain(profile: FarmProfile, lang: str = "en"):
    """Stage 3 (Explain). Returns both the technical SHAP contributions
    (for anyone who wants them) and a plain-language `headline` +
    `farmer_reasons` layer on top -- see farmer_explain.py for why."""
    try:
        profile_dict = profile.model_dump()
        yield_val = model_module.predict_yield(profile_dict)
        base_value, contributions = model_module.explain_yield(profile_dict)
        headline, reasons = farmer_explain_module.build_farmer_summary(
            yield_val, base_value, contributions, lang=lang
        )
        return ExplainResponse(
            predicted_yield_quintal_per_acre=round(yield_val, 2),
            base_value=round(base_value, 2),
            contributions=[
                ShapContribution(feature=f, value=v, shap_value=round(sv, 3))
                for f, v, sv in contributions
            ],
            headline=headline,
            farmer_reasons=[FarmerReason(**r) for r in reasons],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/whatif", response_model=WhatIfResponse)
def whatif(req: WhatIfRequest):
    try:
        baseline_resp = _predict_response(req.baseline)
        modified_resp = _predict_response(req.modified)

        yield_delta_pct = 0.0
        if baseline_resp.predicted_yield_quintal_per_acre > 0:
            yield_delta_pct = (
                (modified_resp.predicted_yield_quintal_per_acre - baseline_resp.predicted_yield_quintal_per_acre)
                / baseline_resp.predicted_yield_quintal_per_acre
                * 100
            )

        return WhatIfResponse(
            baseline=baseline_resp,
            modified=modified_resp,
            yield_delta_pct=round(yield_delta_pct, 2),
            profit_delta=round(modified_resp.estimated_profit - baseline_resp.estimated_profit, 2),
            cost_delta=round(modified_resp.estimated_input_cost - baseline_resp.estimated_input_cost, 2),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest, lang: str = "en"):
    try:
        profile_dict = req.profile.model_dump()
        pareto_points, recommended, summary = optimizer_module.run_optimization(
            profile_dict,
            n_generations=req.n_generations,
            population_size=req.population_size,
            lang=lang,
        )
        advice_headline, advice_steps, advice_general_tip = farmer_explain_module.build_optimize_advice(
            profile_dict, recommended, lang=lang
        )
        return OptimizeResponse(
            pareto_front=[ParetoPoint(**p) for p in pareto_points],
            recommended=ParetoPoint(**recommended),
            recommendation_summary=summary,
            advice_headline=advice_headline,
            advice_steps=[OptimizeAdviceStep(**s) for s in advice_steps],
            advice_general_tip=advice_general_tip,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Day 3: Saved farm profiles (SQLite) -- lets a demo pre-load a polished
# farm instantly instead of retyping the form every time.
# ---------------------------------------------------------------------------

@app.post("/api/profiles", response_model=SavedProfileSummary)
def save_profile(req: SaveProfileRequest):
    profile_id = storage_module.save_profile(req.name, req.profile.model_dump())
    saved = storage_module.get_profile(profile_id)
    return SavedProfileSummary(id=saved["id"], name=saved["name"], created_at=saved["created_at"])


@app.get("/api/profiles", response_model=list[SavedProfileSummary])
def list_profiles():
    return [SavedProfileSummary(**p) for p in storage_module.list_profiles()]


@app.get("/api/profiles/{profile_id}", response_model=SavedProfileDetail)
def get_profile(profile_id: int):
    saved = storage_module.get_profile(profile_id)
    if saved is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return SavedProfileDetail(**saved)


@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: int):
    deleted = storage_module.delete_profile(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"deleted": True}
