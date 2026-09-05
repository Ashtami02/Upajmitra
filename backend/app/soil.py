"""
Day 2: Soil auto-fill.

IMPORTANT UPDATE: ISRIC's SoilGrids REST API has an announced, ongoing
outage as of this writing ("we are currently experiencing issues with the
REST API for SoilGrids, and have decided to temporarily pause the
service" -- docs.isric.org/globaldata/soilgrids). Even when it's up, it's
explicitly beta with no uptime guarantee and a hard 5-calls/minute fair-use
limit. Relying on it as a hard dependency is a bad idea for a live demo.

So this module tries SoilGrids FIRST (in case it's back up by your demo),
with a short timeout, and on ANY failure (timeout, outage, rate limit)
falls back to a static table of typical Indian soil values by region --
sourced from published regional soil survey ranges. The response always
includes a `source` field ("soilgrids" or "regional_estimate") so the
frontend can be honest with the farmer about which one they got, and the
endpoint never hard-fails the whole form.
"""
import requests

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

# Typical topsoil pH / organic carbon % by region, drawn from published
# Indian soil survey ranges (broad regional generalizations -- real
# per-farm values vary a lot by district and land use; this is a
# reasonable fallback default, not a substitute for an actual soil test).
REGIONAL_SOIL_DEFAULTS = {
    "North":   {"soil_ph": 7.4, "organic_carbon_pct": 0.55},  # alluvial, alkaline-leaning
    "South":   {"soil_ph": 6.3, "organic_carbon_pct": 0.65},  # red/laterite, more acidic
    "East":    {"soil_ph": 6.0, "organic_carbon_pct": 0.90},  # alluvial/deltaic, higher OC
    "West":    {"soil_ph": 7.8, "organic_carbon_pct": 0.45},  # black cotton soil, alkaline
    "Central": {"soil_ph": 7.0, "organic_carbon_pct": 0.60},  # mixed black/red soil
}
_DEFAULT_FALLBACK = {"soil_ph": 6.8, "organic_carbon_pct": 0.65}


def _fallback_for_region(region: str | None) -> dict:
    base = REGIONAL_SOIL_DEFAULTS.get(region, _DEFAULT_FALLBACK)
    return {**base, "source": "regional_estimate"}


def fetch_soil_properties(lat: float, lon: float, region: str | None = None) -> dict:
    """Returns {soil_ph, organic_carbon_pct, source}. Tries SoilGrids with
    a short timeout (their fair-use policy is only 5 calls/min anyway, so
    there's no benefit to a long wait); on any failure, returns the
    regional fallback instead of raising -- callers should treat this as
    "always succeeds" rather than something to catch.
    """
    try:
        params = {
            "lon": lon,
            "lat": lat,
            "property": ["phh2o", "soc"],
            "depth": "0-5cm",
            "value": "mean",
        }
        resp = requests.get(SOILGRIDS_URL, params=params, timeout=6)
        resp.raise_for_status()
        data = resp.json()

        layers = {
            layer["name"]: layer["depths"][0]["values"]["mean"]
            for layer in data["properties"]["layers"]
        }
        # SoilGrids "mapped" units -> conventional units (rest.isric.org/soilgrids/v2.0/docs):
        #   phh2o = pH * 10 -> /10;  soc = g/kg * 10 -> /10, then roughly /10 again for %
        soil_ph = layers["phh2o"] / 10.0
        soc_g_per_kg = layers["soc"] / 10.0
        return {
            "soil_ph": round(soil_ph, 2),
            "organic_carbon_pct": round(soc_g_per_kg / 10.0, 2),
            "source": "soilgrids",
        }
    except Exception:
        # Network failure, timeout, outage, malformed response -- all treated
        # the same way: fall back rather than break the farmer's form.
        return _fallback_for_region(region)

