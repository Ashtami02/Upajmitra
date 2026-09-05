"""
Loads the trained CatBoost model once at process start, and exposes:
  - predict_yield(profile_dict) -> float
  - explain_yield(profile_dict) -> (base_value, [(feature, value, shap), ...])
  - economics(profile_dict, yield_val) -> (revenue, cost, profit)

This is Tier 3 (ML & Explainability) from the architecture slide.
"""
import json
import os

import numpy as np
import pandas as pd
import shap
from catboost import CatBoostRegressor, Pool

_ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "..", "model_artifacts")

_model: CatBoostRegressor | None = None
_meta: dict | None = None
_explainer: shap.TreeExplainer | None = None


def _load():
    global _model, _meta, _explainer
    if _model is not None:
        return
    with open(os.path.join(_ARTIFACT_DIR, "feature_names.json")) as f:
        _meta = json.load(f)
    _model = CatBoostRegressor()
    _model.load_model(os.path.join(_ARTIFACT_DIR, "yield_model.cbm"))
    _explainer = shap.TreeExplainer(_model)


def _profile_to_row(profile: dict) -> pd.DataFrame:
    _load()
    row = {feat: profile[feat] for feat in _meta["feature_order"]}
    return pd.DataFrame([row], columns=_meta["feature_order"])


def _cat_feature_indices():
    _load()
    return [_meta["feature_order"].index(c) for c in _meta["categorical_features"]]


def predict_yield(profile: dict) -> float:
    _load()
    row = _profile_to_row(profile)
    pool = Pool(row, cat_features=_cat_feature_indices())
    pred = float(_model.predict(pool)[0])
    return max(pred, 0.0)


def explain_yield(profile: dict):
    """Returns (base_value, list of (feature, display_value, shap_value))
    sorted by |shap_value| descending -- this is what powers the SHAP bar
    chart on the frontend (Stage 3: Explain)."""
    _load()
    row = _profile_to_row(profile)
    pool = Pool(row, cat_features=_cat_feature_indices())

    shap_values = _explainer.shap_values(pool)[0]
    base_value = float(_explainer.expected_value)

    contributions = []
    for feat, sv in zip(_meta["feature_order"], shap_values):
        contributions.append((feat, str(row.iloc[0][feat]), float(sv)))

    contributions.sort(key=lambda t: abs(t[2]), reverse=True)
    return base_value, contributions


def economics(profile: dict, yield_val: float):
    """Simple economic model: revenue = yield * market price;
    cost = fertilizer + irrigation + fixed costs; profit = revenue - cost."""
    fert_cost = (
        profile["nitrogen_kg_per_acre"]
        + profile["phosphorus_kg_per_acre"]
        + profile["potassium_kg_per_acre"]
    ) * profile["fertilizer_cost_per_kg"]
    irrigation_cost = profile["irrigation_mm_per_week"] * 13 * profile["irrigation_cost_per_mm"]  # ~13 wk season
    total_cost = fert_cost + irrigation_cost + profile["fixed_cost_per_acre"]
    revenue = yield_val * profile["market_price_per_quintal"]
    profit = revenue - total_cost
    return revenue, total_cost, profit


def get_meta() -> dict:
    _load()
    return _meta
