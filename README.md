# UpajMitra 🌾

UpajMitra ("upaj" = yield/produce, "mitra" = friend) is a farm-yield app built for Indian farmers who want a straight answer to one question: *what should I actually do this season to get a better harvest, without wasting money on fertilizer or water I don't need?*

You type in (or auto-fill) details about your farm — crop, soil, region, how much fertilizer and water you're planning to use — and the app tells you:

1. **What yield to expect**, and what that means for your profit after costs.
2. **Why** the model is predicting that number, in plain language, not a chart full of jargon.
3. **What happens if you change something** — more nitrogen, less water, a different sowing rate — before you actually spend the money.
4. **The exact combination of inputs** that gets you the best profit for the least cost, worked out by an optimizer, not a guess.

Everything's available in English and Hindi.

## Why we built it this way

Most "AI for agriculture" demos stop at a number: "your yield will be 42 quintals per acre." That's not very useful to a farmer on its own — it doesn't say *why*, and it doesn't say *what to do differently*. So instead of just predicting, UpajMitra tries to explain and recommend too. The prediction, the explanation, and the recommendation all come from the same model, so a farmer isn't getting a black-box number followed by generic advice bolted on afterward — the "why" and the "what to do" are computed from the actual model, not written by us.

We also tried to be honest about what's real. A few things in here are proper, tested pipelines (the yield model, the SHAP explanations, the optimizer). A couple of things are deliberately simple stand-ins for a bigger idea we didn't have time to build properly (the canopy photo score is a green-pixel heuristic, not a trained vision model — more on that below). We'd rather say that plainly than pretend it's more than it is.

## How it works, step by step

**1. Farm profile.** You enter your crop, region, soil type, fertilizer plan, irrigation, and a few other basics. If you don't know your soil pH or seasonal rainfall off the top of your head (most people don't), you can pick your district from a list instead of typing coordinates, and the app fetches your soil and weather data for you — from SoilGrids and Open-Meteo when they're reachable, or from a table of regional averages if they're not. Either way you get sensible numbers, and the app tells you honestly which one you got.

**2. Photo (optional).** You can upload a photo of your field. The app looks at how much green is in the picture and turns that into a "canopy health" score from 0–100. That score becomes a real input to the yield model alongside everything else you typed — it's not just a picture for decoration, it actually moves the prediction. It's a rough heuristic, not a trained CNN, and we say so in the app.

**3. Predict + Explain.** A CatBoost model trained on crop yield data predicts your yield, revenue, cost, and profit. Underneath, we run SHAP to see which factors pushed the number up or down, and then translate that into a short, plain-language summary — "your nitrogen is a bit low for this soil, that's costing you yield" — instead of a bar chart of feature names. The technical SHAP numbers are still there if you want them, just tucked under a "see technical details" toggle.

**4. What-if.** Drag a slider — more water, less fertilizer, a different sowing rate — and see the yield and profit change live, before you spend a single rupee on it.

**5. Optimize.** This is the part that actually answers "so what should I do?" We run a multi-objective genetic algorithm (NSGA-II) across thousands of fertilizer/water/sowing combinations to find the ones that give you the best trade-off between yield, cost, and profit. The single best-fit recommendation is shown as a clear "Recommended Plan" card at the top — exact kilograms of N/P/K, exact irrigation — not buried in a table you have to interpret yourself.

You can save a farm profile so you don't have to retype it every time, and switch the whole thing between English and Hindi with one click in the header.

## What's real, what's a stand-in

We wanted to be upfront about this instead of letting a demo imply more than it delivers:

| Piece | Status |
|---|---|
| Yield prediction (CatBoost) | Real, trained model |
| SHAP explanations | Real, computed from the model, not scripted |
| Plain-language "why" summary | Real, generated from the actual SHAP output |
| Optimizer (NSGA-II) | Real, runs a genuine search over the input space |
| Soil / weather auto-fill | Real API calls (SoilGrids, Open-Meteo) with a regional-average fallback if either is down or rate-limited |
| Canopy photo score | A green-pixel-ratio heuristic — a placeholder for a proper vision model, not one itself |
| Training data | Depends on what got loaded in — real government yield data if a dataset was supplied, agronomically-structured synthetic data otherwise. Check `backend/model_artifacts/training_data_used.csv` |
| SMS delivery (Twilio) | Code is written but not wired in by default — needs your own Twilio credentials |

## Project layout

```
upajmitra/
├── backend/                     FastAPI + CatBoost + SHAP + NSGA-II (pymoo)
│   ├── app/
│   │   ├── main.py              all API routes
│   │   ├── model.py             load model, predict, SHAP explain
│   │   ├── optimizer.py         NSGA-II multi-objective optimizer
│   │   ├── farmer_explain.py    turns SHAP numbers into plain-language reasons/advice
│   │   ├── soil.py / weather.py auto-fill with live API + regional fallback
│   │   ├── locations.py         district picker so farmers don't type lat/lon
│   │   ├── vision.py            canopy greenness heuristic (green-pixel ratio)
│   │   ├── vision_multimodal.py optional real vision-model version (needs your own API key)
│   │   ├── notify.py            Twilio SMS, written but not wired in by default
│   │   ├── storage.py           SQLite save/load for farm profiles
│   │   └── train_model.py       synthetic data generator + training script
│   └── model_artifacts/         the trained model, already sitting here
└── frontend/                     React (Vite) + Recharts
    └── src/
        ├── App.jsx               4-step wizard tying it all together
        ├── i18n.js                English/Hindi strings
        └── components/
            ├── FarmProfileForm.jsx
            ├── CanopyPhotoUpload.jsx
            ├── ProfileManager.jsx
            ├── PredictionPanel.jsx    metrics + plain-language explanation + SHAP chart
            ├── WhatIfSimulator.jsx    live sliders
            └── OptimizePanel.jsx      Recommended Plan card + Pareto chart
```

## Running it locally

**Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Swagger docs live at `http://localhost:8000/docs`. The model is already trained, so this works right away. To retrain: `python app/train_model.py` (add `--data path/to/csv.csv` to train on a real dataset instead of the synthetic one).

**Frontend**
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`. It proxies `/api/*` to `localhost:8000`, so as long as the backend's running, the whole flow — profile → predict → explain → what-if → optimize — works end to end.

## API reference

| Method | Path | What it does |
|---|---|---|
| GET | `/api/meta` | crop/soil/region dropdown options |
| GET | `/api/locations` | districts by region, for the location picker |
| GET | `/api/soil` | soil pH / organic carbon by lat-lon, live or regional fallback |
| GET | `/api/weather` | temperature / rainfall by lat-lon, live or regional fallback |
| POST | `/api/canopy-analysis` | upload a photo, get a canopy health score |
| POST | `/api/predict` | farm profile → yield, revenue, cost, profit |
| POST | `/api/explain` | farm profile → SHAP contributions + plain-language reasons |
| POST | `/api/whatif` | baseline vs. modified profile → the difference |
| POST | `/api/optimize` | farm profile → Pareto frontier + recommended plan |
| POST/GET/DELETE | `/api/profiles` | save, list, load, delete farm profiles |

Full request/response shapes are in `backend/app/schemas.py` and show up automatically at `/docs`.

## Honest limitations / what's next

- The canopy score is a color heuristic, not a trained model. `vision_multimodal.py` has a proper version that calls a vision-capable model instead — it just needs an API key and a bit more testing before it's demo-ready.
- Some soil/climate fields get backfilled with constants when training on the real Kaggle-style dataset, since that dataset doesn't include them — documented in `train_model.py`.
- SMS delivery via Twilio is written but disconnected by default; wiring it up needs your own Twilio account.
- No auth on saved profiles right now — fine for a demo, not fine for anything public-facing.

## License / credit

Built as a hackathon project. Training data is either publicly available government crop-yield data or synthetic data generated to be agronomically plausible — see the note above on which one's currently loaded.
