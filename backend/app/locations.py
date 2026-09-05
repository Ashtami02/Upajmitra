"""
Day 2 follow-up: farmer-friendly location picker.

Raw latitude/longitude entry is meaningless to most farmers, and typing
it by hand is error-prone (that's most likely why "the lat/lon system
isn't working properly" -- a mistyped or swapped coordinate silently
sends the soil/weather lookup to the wrong place on Earth with no
warning). We keep lat/lon internally (soil.py and weather.py still need
real coordinates to call SoilGrids/Open-Meteo), but the farmer never has
to see or type a number.

Two ways a farmer can set their location, both resolving to a lat/lon
behind the scenes:
  1. "Use my location" -- browser GPS (handled entirely on the frontend
     via navigator.geolocation; nothing to do here).
  2. Pick their district from a simple list -- this module provides that
     list, grouped under the same 5 regions (North/South/East/West/
     Central) already used elsewhere in the app, so picking a district
     also correctly fills in the Region dropdown.

This is a representative set of major agricultural districts per region,
not an exhaustive gazetteer -- good enough to get a farmer a reasonably
close coordinate for the soil/weather auto-fill, which itself always has
a regional fallback if the live services are unavailable.
"""

INDIA_LOCATIONS = {
    "North": [
        {"state": "Punjab", "district": "Ludhiana", "lat": 30.9010, "lon": 75.8573},
        {"state": "Haryana", "district": "Karnal", "lat": 29.6857, "lon": 76.9905},
        {"state": "Uttar Pradesh", "district": "Lucknow", "lat": 26.8467, "lon": 80.9462},
        {"state": "Uttar Pradesh", "district": "Meerut", "lat": 28.9845, "lon": 77.7064},
        {"state": "Rajasthan", "district": "Jaipur", "lat": 26.9124, "lon": 75.7873},
        {"state": "Delhi", "district": "Delhi", "lat": 28.6139, "lon": 77.2090},
        {"state": "Himachal Pradesh", "district": "Shimla", "lat": 31.1048, "lon": 77.1734},
    ],
    "South": [
        {"state": "Karnataka", "district": "Bengaluru Rural", "lat": 13.2846, "lon": 77.5758},
        {"state": "Tamil Nadu", "district": "Coimbatore", "lat": 11.0168, "lon": 76.9558},
        {"state": "Tamil Nadu", "district": "Thanjavur", "lat": 10.7870, "lon": 79.1378},
        {"state": "Andhra Pradesh", "district": "Guntur", "lat": 16.3067, "lon": 80.4365},
        {"state": "Telangana", "district": "Warangal", "lat": 17.9689, "lon": 79.5941},
        {"state": "Kerala", "district": "Palakkad", "lat": 10.7867, "lon": 76.6548},
    ],
    "East": [
        {"state": "West Bengal", "district": "Bardhaman", "lat": 23.2324, "lon": 87.8615},
        {"state": "Bihar", "district": "Patna", "lat": 25.5941, "lon": 85.1376},
        {"state": "Odisha", "district": "Cuttack", "lat": 20.4625, "lon": 85.8830},
        {"state": "Jharkhand", "district": "Ranchi", "lat": 23.3441, "lon": 85.3096},
        {"state": "Assam", "district": "Nagaon", "lat": 26.3479, "lon": 92.6840},
    ],
    "West": [
        {"state": "Maharashtra", "district": "Nashik", "lat": 19.9975, "lon": 73.7898},
        {"state": "Maharashtra", "district": "Pune", "lat": 18.5204, "lon": 73.8567},
        {"state": "Gujarat", "district": "Ahmedabad", "lat": 23.0225, "lon": 72.5714},
        {"state": "Gujarat", "district": "Rajkot", "lat": 22.3039, "lon": 70.8022},
        {"state": "Goa", "district": "North Goa", "lat": 15.4909, "lon": 73.8278},
    ],
    "Central": [
        {"state": "Madhya Pradesh", "district": "Indore", "lat": 22.7196, "lon": 75.8577},
        {"state": "Madhya Pradesh", "district": "Bhopal", "lat": 23.2599, "lon": 77.4126},
        {"state": "Chhattisgarh", "district": "Raipur", "lat": 21.2514, "lon": 81.6296},
    ],
}


def get_locations() -> dict:
    return INDIA_LOCATIONS
