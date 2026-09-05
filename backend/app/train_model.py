"""
UpajMitra - Yield Model Training Script
=========================================
Generates a physically-plausible SYNTHETIC agronomic dataset (since no
real farm dataset is available in a hackathon timeframe) and trains a
CatBoost Regressor to predict crop yield (quintals/acre) from farm
inputs. Swap `generate_synthetic_dataset()` for a real CSV loader the
moment you have actual data (e.g. ICAR / state agri-dept datasets) --
the rest of the pipeline (features, model, SHAP, API) does not change.

Run:
    python app/train_model.py
Produces:
    model_artifacts/yield_model.cbm
    model_artifacts/feature_names.json
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool
from sklearn.model_selection import train_test_split

RNG = np.random.default_rng(42)

CROPS = ["Wheat", "Rice", "Maize", "Cotton", "Sugarcane"]
SOIL_TYPES = ["Alluvial", "Black", "Red", "Laterite", "Sandy"]
REGIONS = ["North", "South", "East", "West", "Central"]

CATEGORICAL_FEATURES = ["crop_type", "soil_type", "region"]

NUMERIC_FEATURES = [
    "nitrogen_kg_per_acre",
    "phosphorus_kg_per_acre",
    "potassium_kg_per_acre",
    "irrigation_mm_per_week",
    "soil_ph",
    "organic_carbon_pct",
    "avg_temp_c",
    "rainfall_mm_season",
    "sowing_density_kg_per_acre",
    "pesticide_applications",
    "canopy_health_index",
]

FEATURE_ORDER = CATEGORICAL_FEATURES + NUMERIC_FEATURES


def generate_synthetic_dataset(n_rows: int = 6000) -> pd.DataFrame:
    """Simulates yield response using domain-plausible relationships:
    diminishing returns on NPK/irrigation, crop-specific base yields,
    and a soil-quality (pH/organic carbon) multiplier -- with noise.
    """
    crop_type = RNG.choice(CROPS, n_rows)
    soil_type = RNG.choice(SOIL_TYPES, n_rows)
    region = RNG.choice(REGIONS, n_rows)

    nitrogen = RNG.uniform(20, 160, n_rows)
    phosphorus = RNG.uniform(10, 80, n_rows)
    potassium = RNG.uniform(10, 80, n_rows)
    irrigation = RNG.uniform(0, 60, n_rows)
    soil_ph = RNG.uniform(5.0, 8.5, n_rows)
    organic_carbon = RNG.uniform(0.2, 1.8, n_rows)
    avg_temp = RNG.uniform(15, 38, n_rows)
    rainfall = RNG.uniform(200, 1800, n_rows)
    sowing_density = RNG.uniform(8, 45, n_rows)
    pesticide_apps = RNG.integers(0, 6, n_rows)

    # Canopy health index (0-100): what a farm photo's visual analysis
    # would plausibly report. Modeled here as loosely downstream of the
    # SAME underlying agronomic conditions a real photo would visually
    # reflect (good nutrition + water + soil quality + benign climate ->
    # a visibly healthier-looking canopy), plus its own independent noise
    # -- since real vision analysis also has its own sensing error and
    # picks up things the tabular features don't fully capture (e.g. a
    # visible pest outbreak the day of the photo).
    canopy_base = (
        50
        + 12 * np.sqrt(nitrogen / 160)
        + 8 * np.sqrt(irrigation / 60)
        + 10 * (organic_carbon / 1.8)
        - 6 * np.clip(np.abs(soil_ph - 6.5) - 0.5, 0, None)
    )
    canopy_health_index = np.clip(canopy_base + RNG.normal(0, 8, n_rows), 0, 100)

    base_yield = {
        "Wheat": 18, "Rice": 22, "Maize": 20, "Cotton": 8, "Sugarcane": 350,
    }
    crop_base = np.array([base_yield[c] for c in crop_type])

    # Diminishing-returns response curves (sqrt) for nutrients/water
    npk_response = (
        1.0
        + 0.55 * np.sqrt(nitrogen / 160)
        + 0.30 * np.sqrt(phosphorus / 80)
        + 0.25 * np.sqrt(potassium / 80)
    )
    water_response = 1.0 + 0.35 * np.sqrt(np.clip(irrigation, 0, None) / 60)

    # Soil quality multiplier: pH close to 6.5 is ideal, higher organic C helps
    ph_penalty = 1.0 - 0.12 * np.abs(soil_ph - 6.5)
    oc_bonus = 1.0 + 0.20 * (organic_carbon / 1.8)
    soil_quality = np.clip(ph_penalty, 0.55, 1.05) * oc_bonus

    # Climate stress: too hot or too little/too much rain hurts yield
    temp_stress = 1.0 - 0.015 * np.clip(np.abs(avg_temp - 26) - 4, 0, None)
    rain_ideal = {"Wheat": 500, "Rice": 1400, "Maize": 700, "Cotton": 750, "Sugarcane": 1500}
    rain_target = np.array([rain_ideal[c] for c in crop_type])
    rain_stress = 1.0 - 0.00025 * np.abs(rainfall - rain_target)
    climate_factor = np.clip(temp_stress, 0.6, 1.05) * np.clip(rain_stress, 0.55, 1.05)

    density_response = 1.0 + 0.10 * np.sqrt(sowing_density / 45)
    pest_response = 1.0 + 0.02 * pesticide_apps - 0.003 * pesticide_apps**2

    # Canopy health carries some genuinely independent signal (e.g. a
    # visible pest outbreak or wilting the day of the photo that the
    # tabular features don't capture) -- modest weight since it's mostly
    # correlated with factors already represented elsewhere.
    canopy_response = 0.85 + 0.30 * (canopy_health_index / 100)

    noise = RNG.normal(1.0, 0.06, n_rows)

    yield_val = (
        crop_base
        * npk_response
        * water_response
        * soil_quality
        * climate_factor
        * density_response
        * pest_response
        * canopy_response
        * noise
    )
    yield_val = np.clip(yield_val, 0.5, None)

    df = pd.DataFrame({
        "crop_type": crop_type,
        "soil_type": soil_type,
        "region": region,
        "nitrogen_kg_per_acre": nitrogen,
        "phosphorus_kg_per_acre": phosphorus,
        "potassium_kg_per_acre": potassium,
        "irrigation_mm_per_week": irrigation,
        "soil_ph": soil_ph,
        "organic_carbon_pct": organic_carbon,
        "avg_temp_c": avg_temp,
        "rainfall_mm_season": rainfall,
        "sowing_density_kg_per_acre": sowing_density,
        "pesticide_applications": pesticide_apps,
        "canopy_health_index": canopy_health_index,
        "yield_quintal_per_acre": yield_val,
    })
    return df


# Maps Indian states -> the 5 broad regions our schema uses. Extend/adjust
# freely -- this is a simplification for feature-engineering purposes only.
_STATE_TO_REGION = {
    "Punjab": "North", "Haryana": "North", "Uttar Pradesh": "North",
    "Himachal Pradesh": "North", "Uttarakhand": "North", "Delhi": "North",
    "Jammu and Kashmir": "North", "Rajasthan": "North",
    "Tamil Nadu": "South", "Karnataka": "South", "Kerala": "South",
    "Andhra Pradesh": "South", "Telangana": "South", "Puducherry": "South",
    "West Bengal": "East", "Bihar": "East", "Odisha": "East",
    "Jharkhand": "East", "Assam": "East", "Sikkim": "East",
    "Maharashtra": "West", "Gujarat": "West", "Goa": "West",
    "Madhya Pradesh": "Central", "Chhattisgarh": "Central",
}


def load_real_dataset(csv_path: str) -> pd.DataFrame:
    """Loads a real crop-yield CSV in the schema of Kaggle's "Crop Yield in
    Indian States Dataset" (akshatgupta7) -- columns:
        State_Name, Crop_Year, Season, Crop, Area, Production,
        Annual_Rainfall, Fertilizer, Pesticide
    (Area in hectares, Production in tonnes, Fertilizer/Pesticide in kg
    for the WHOLE cultivated area for that row, not per-acre.)

    Maps these onto our FEATURE_ORDER schema. Columns this source dataset
    does NOT capture (soil pH, organic carbon, irrigation, sowing density,
    per-nutrient NPK split) are backfilled with literature-typical
    constants / a standard 4:2:1 N:P:K application ratio -- clearly a
    simplification. Priority follow-up: replace the backfilled soil
    columns using the SoilGrids integration from Day 2, keyed by district
    centroid lat/lon if your source data has district names.

    If you're using a DIFFERENT real dataset with different column names,
    adjust the column references below -- everything downstream (model,
    SHAP, API, frontend) is unaffected as long as you still end up with a
    DataFrame containing FEATURE_ORDER + 'yield_quintal_per_acre'.
    """
    raw = pd.read_csv(csv_path)
    required = ["State_Name", "Crop", "Area", "Production", "Annual_Rainfall", "Fertilizer", "Pesticide"]
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise ValueError(
            f"Real dataset is missing expected columns {missing}. "
            "Either rename your columns to match, or edit load_real_dataset() "
            "to map your actual schema onto FEATURE_ORDER."
        )

    raw = raw.dropna(subset=["Area", "Production", "Fertilizer", "Pesticide", "Annual_Rainfall"])
    raw = raw[raw["Area"] > 0].copy()

    ACRES_PER_HECTARE = 2.471
    area_acres = raw["Area"] * ACRES_PER_HECTARE

    df = pd.DataFrame()
    df["crop_type"] = raw["Crop"].astype(str).str.strip().str.title()
    df["region"] = raw["State_Name"].map(_STATE_TO_REGION).fillna("Central")
    df["soil_type"] = "Alluvial"  # not in source data -- backfill; refine via SoilGrids per-row if you have coordinates

    npk_per_acre = (raw["Fertilizer"] / area_acres).clip(lower=0)
    # Typical reported Indian NPK application ratio is roughly 4:2:1 (N:P:K)
    df["nitrogen_kg_per_acre"] = (npk_per_acre * 4 / 7).clip(0, 300)
    df["phosphorus_kg_per_acre"] = (npk_per_acre * 2 / 7).clip(0, 200)
    df["potassium_kg_per_acre"] = (npk_per_acre * 1 / 7).clip(0, 200)

    df["irrigation_mm_per_week"] = 20.0  # not in source -- backfill; refine via Day 2 weather API
    df["soil_ph"] = 6.5
    df["organic_carbon_pct"] = 0.75
    df["avg_temp_c"] = 26.0
    df["rainfall_mm_season"] = raw["Annual_Rainfall"].clip(0, 4000)
    df["sowing_density_kg_per_acre"] = 20.0
    df["pesticide_applications"] = (raw["Pesticide"] / area_acres / 0.5).round().clip(0, 15)
    df["canopy_health_index"] = 60.0  # not in source (no photos) -- neutral default

    df["yield_quintal_per_acre"] = (raw["Production"] * 10 / area_acres).clip(lower=0.1)
    # Production is in tonnes; 1 tonne = 10 quintals.

    return df[FEATURE_ORDER + ["yield_quintal_per_acre"]]


def train_and_save(output_dir: str = None, data_path: str = None):
    output_dir = output_dir or os.path.join(os.path.dirname(__file__), "..", "model_artifacts")
    os.makedirs(output_dir, exist_ok=True)

    if data_path:
        print(f"Loading real dataset from {data_path} ...")
        df = load_real_dataset(data_path)
        print(f"Loaded {len(df)} real rows after cleaning.")
    else:
        print("No --data path given -- using synthetic dataset (see README Day 1).")
        df = generate_synthetic_dataset()

    df.to_csv(os.path.join(output_dir, "training_data_used.csv"), index=False)

    X = df[FEATURE_ORDER]
    y = df["yield_quintal_per_acre"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)

    cat_idx = [X.columns.get_loc(c) for c in CATEGORICAL_FEATURES]
    train_pool = Pool(X_train, y_train, cat_features=cat_idx)
    test_pool = Pool(X_test, y_test, cat_features=cat_idx)

    model = CatBoostRegressor(
        iterations=600,
        depth=6,
        learning_rate=0.05,
        loss_function="RMSE",
        random_seed=42,
        verbose=False,
    )
    model.fit(train_pool, eval_set=test_pool, early_stopping_rounds=50, verbose=False)

    preds = model.predict(test_pool)
    rmse = float(np.sqrt(np.mean((preds - y_test.values) ** 2)))
    mape = float(np.mean(np.abs((preds - y_test.values) / y_test.values)) * 100)
    print(f"Validation RMSE: {rmse:.3f} quintal/acre | MAPE: {mape:.2f}%")

    model_path = os.path.join(output_dir, "yield_model.cbm")
    model.save_model(model_path)

    meta = {
        "feature_order": FEATURE_ORDER,
        "categorical_features": CATEGORICAL_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "crops": CROPS,
        "soil_types": SOIL_TYPES,
        "regions": REGIONS,
        "val_rmse": rmse,
        "val_mape_pct": mape,
    }
    with open(os.path.join(output_dir, "feature_names.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Saved model to {model_path}")
    return model_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the UpajMitra yield model.")
    parser.add_argument(
        "--data", type=str, default=None,
        help="Path to a real crop-yield CSV (see load_real_dataset() docstring for expected "
             "columns). If omitted, trains on the synthetic dataset instead.",
    )
    args = parser.parse_args()
    train_and_save(data_path=args.data)
