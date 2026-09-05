"""
Day 2: Weather auto-fill via Open-Meteo Historical Weather API
(free, no API key). Docs: https://open-meteo.com/en/docs/historical-weather-api
Open-Meteo has been reliable in practice (unlike SoilGrids -- see soil.py),
but the same demo-safety principle applies: never let a live venue's flaky
wifi turn into a broken form. Falls back to regional climate normals on
any failure, and always returns a `source` field.
"""
from datetime import date, timedelta

import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Rough seasonal climate normals by region, for fallback only.
REGIONAL_CLIMATE_DEFAULTS = {
    "North":   {"avg_temp_c": 25.0, "rainfall_mm_season": 500.0},
    "South":   {"avg_temp_c": 28.0, "rainfall_mm_season": 900.0},
    "East":    {"avg_temp_c": 27.0, "rainfall_mm_season": 1300.0},
    "West":    {"avg_temp_c": 27.5, "rainfall_mm_season": 750.0},
    "Central": {"avg_temp_c": 26.5, "rainfall_mm_season": 950.0},
}
_DEFAULT_FALLBACK = {"avg_temp_c": 26.0, "rainfall_mm_season": 800.0}


def _fallback_for_region(region: str | None) -> dict:
    base = REGIONAL_CLIMATE_DEFAULTS.get(region, _DEFAULT_FALLBACK)
    return {**base, "source": "regional_estimate"}


def fetch_season_weather(lat: float, lon: float, region: str | None = None, days_back: int = 120) -> dict:
    """Returns {avg_temp_c, rainfall_mm_season, source}. Tries Open-Meteo
    with a short timeout; on any failure returns a regional fallback
    instead of raising."""
    try:
        end = date.today() - timedelta(days=2)  # archive has a short lag
        start = end - timedelta(days=days_back)
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "temperature_2m_mean,precipitation_sum",
            "timezone": "auto",
        }
        resp = requests.get(ARCHIVE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        temps = [t for t in data["daily"]["temperature_2m_mean"] if t is not None]
        rain = [r for r in data["daily"]["precipitation_sum"] if r is not None]
        if not temps or not rain:
            raise ValueError("Open-Meteo returned no usable daily data")

        return {
            "avg_temp_c": round(sum(temps) / len(temps), 1),
            "rainfall_mm_season": round(sum(rain), 1),
            "source": "open-meteo",
        }
    except Exception:
        return _fallback_for_region(region)
