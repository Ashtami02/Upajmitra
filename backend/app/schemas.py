from typing import Optional
from pydantic import BaseModel, Field


class FarmProfile(BaseModel):
    """Stage 1 (Farm Profile) input -- mirrors the pitch deck's controllable +
    contextual features. Frontend collects this via a form."""

    crop_type: str = Field(..., examples=["Wheat"])
    soil_type: str = Field(..., examples=["Alluvial"])
    region: str = Field(..., examples=["North"])

    nitrogen_kg_per_acre: float = Field(..., ge=0, le=300)
    phosphorus_kg_per_acre: float = Field(..., ge=0, le=200)
    potassium_kg_per_acre: float = Field(..., ge=0, le=200)
    irrigation_mm_per_week: float = Field(..., ge=0, le=150)
    soil_ph: float = Field(..., ge=3.5, le=9.5)
    organic_carbon_pct: float = Field(..., ge=0, le=5)
    avg_temp_c: float = Field(..., ge=0, le=50)
    rainfall_mm_season: float = Field(..., ge=0, le=4000)
    sowing_density_kg_per_acre: float = Field(..., ge=1, le=100)
    pesticide_applications: int = Field(..., ge=0, le=15)

    # Visual/vision-derived feature -- see vision.py. Defaults to a neutral
    # 60 (average) if the farmer hasn't uploaded a photo; overwritten with
    # a real analyzed value once they do. This is a genuine CatBoost input
    # feature (see FEATURE_ORDER in train_model.py), not a display-only
    # add-on -- its SHAP contribution shows up in /api/explain like any
    # other feature.
    canopy_health_index: float = Field(default=60.0, ge=0, le=100)

    # Economics -- used by the optimizer / profit calc, not the yield model
    fertilizer_cost_per_kg: float = Field(default=25.0, ge=0)
    irrigation_cost_per_mm: float = Field(default=8.0, ge=0)
    market_price_per_quintal: float = Field(default=2200.0, ge=0)
    fixed_cost_per_acre: float = Field(default=8000.0, ge=0)


class PredictionResponse(BaseModel):
    predicted_yield_quintal_per_acre: float
    estimated_revenue: float
    estimated_input_cost: float
    estimated_profit: float


class ShapContribution(BaseModel):
    feature: str
    value: str
    shap_value: float


class FarmerReason(BaseModel):
    """One plain-language reason behind the prediction -- the
    farmer-facing counterpart to a ShapContribution row."""
    feature: str
    label: str
    message: str
    direction: str  # "positive" | "negative"


class ExplainResponse(BaseModel):
    predicted_yield_quintal_per_acre: float
    base_value: float
    contributions: list[ShapContribution]
    headline: str
    farmer_reasons: list[FarmerReason]


class WhatIfRequest(BaseModel):
    baseline: FarmProfile
    modified: FarmProfile


class WhatIfResponse(BaseModel):
    baseline: PredictionResponse
    modified: PredictionResponse
    yield_delta_pct: float
    profit_delta: float
    cost_delta: float


class OptimizeRequest(BaseModel):
    profile: FarmProfile
    n_generations: int = Field(default=40, ge=5, le=200)
    population_size: int = Field(default=40, ge=10, le=200)


class ParetoPoint(BaseModel):
    nitrogen_kg_per_acre: float
    phosphorus_kg_per_acre: float
    potassium_kg_per_acre: float
    irrigation_mm_per_week: float
    predicted_yield_quintal_per_acre: float
    estimated_cost: float
    estimated_profit: float


class OptimizeAdviceStep(BaseModel):
    """One farmer-facing step explaining HOW to move a single controllable
    lever (nitrogen/phosphorus/potassium/irrigation) from its current value
    to the optimizer's recommended value."""
    feature: str
    label: str
    current: float
    recommended: float
    direction: str  # "increase" | "decrease" | "same"
    message: str


class OptimizeResponse(BaseModel):
    pareto_front: list[ParetoPoint]
    recommended: ParetoPoint
    recommendation_summary: str
    advice_headline: str
    advice_steps: list[OptimizeAdviceStep]
    advice_general_tip: str


class SaveProfileRequest(BaseModel):
    name: str
    profile: FarmProfile


class SavedProfileSummary(BaseModel):
    id: int
    name: str
    created_at: str


class SavedProfileDetail(BaseModel):
    id: int
    name: str
    created_at: str
    profile: FarmProfile


class CanopyAnalysisResponse(BaseModel):
    green_pixel_ratio: float
    canopy_health_index: float
    health_label: str
