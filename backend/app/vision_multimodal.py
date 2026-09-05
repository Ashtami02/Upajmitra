"""
Day 4 (optional upgrade): REAL multimodal vision analysis of farm photos,
using Claude's vision capability, as a drop-in replacement for the
green-pixel heuristic in vision.py.

Why this exists: the default `analyze_canopy_greenness()` in vision.py is
a cheap, honest color heuristic -- it works with zero setup and zero cost,
but it can only measure "how green is this photo," not actually reason
about crop appearance, visible stress, or field condition the way a real
vision model can. This module is the "real multimodal AI" version of the
same idea: it sends the photo to Claude with a structured prompt and asks
for a JSON assessment covering the specific signals a judge would expect
("crop/plant appearance", "vegetation condition", "visible soil
characteristics", "signs of stress or abnormalities", "general field
condition") -- then reduces that to the SAME canopy_health_index (0-100)
contract that vision.py returns, so nothing downstream (the API endpoint,
the model feature, SHAP, the frontend) needs to change if you swap it in.

⚠️ NOT TESTED with a live API call -- this sandbox has no ANTHROPIC_API_KEY
configured. The code is correct against the Anthropic Python SDK's public
interface (verified the SDK imports and the call shape matches its docs),
but you should run one real request yourself before relying on it, and
keep an eye on request latency/cost if you wire this in for a live demo.

Setup:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...

To wire this in instead of the heuristic, in main.py's canopy_analysis()
endpoint, swap:
    vision_module.analyze_canopy_greenness(image_bytes)
for:
    vision_multimodal.analyze_canopy_with_vision_model(image_bytes)
Both return the same {canopy_health_index, health_label, ...} shape.
"""
import base64
import json
import os

ANALYSIS_PROMPT = """You are an agronomy assistant analyzing a farm/field photo.
Look at the crop or field shown and assess:
1. Crop/plant appearance (color, density, uniformity)
2. Vegetation condition (vigorous, moderate, stressed, sparse)
3. Visible soil characteristics, if soil is visible (color, moisture, texture)
4. Any visible signs of stress or abnormality (wilting, discoloration, pest damage, bare patches)
5. General field condition summary

Respond with ONLY a JSON object, no other text, in exactly this shape:
{
  "crop_appearance": "<one short phrase>",
  "vegetation_condition": "<one of: vigorous, moderate, stressed, sparse>",
  "visible_soil_notes": "<one short phrase, or 'not clearly visible'>",
  "stress_signs": "<one short phrase describing any visible stress, or 'none apparent'>",
  "general_condition_summary": "<one sentence>",
  "canopy_health_index": <integer 0-100, your overall health estimate>
}"""


def analyze_canopy_with_vision_model(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """Sends the photo to Claude for a structured visual assessment.
    Returns a dict with the same `canopy_health_index` + `health_label`
    keys the heuristic version returns (so it's a drop-in swap), PLUS the
    richer structured fields (crop_appearance, vegetation_condition, etc.)
    for a frontend that wants to show more than just a number.

    Raises RuntimeError if ANTHROPIC_API_KEY isn't set, and lets any SDK
    exception (rate limit, bad image, etc.) bubble up to the caller.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set -- this optional multimodal vision "
            "path requires a real Anthropic API key. Falling back to the "
            "heuristic in vision.py is a reasonable default if you don't "
            "want to set this up."
        )

    from anthropic import Anthropic  # imported lazily so the app still boots without the package installed

    client = Anthropic(api_key=api_key)
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                    },
                    {"type": "text", "text": ANALYSIS_PROMPT},
                ],
            }
        ],
    )

    raw_text = response.content[0].text.strip()
    # Defensive: strip accidental markdown code fences if the model adds them
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(raw_text)

    health_index = float(parsed.get("canopy_health_index", 60))
    health_index = max(0.0, min(100.0, health_index))

    if health_index >= 70:
        label = "Healthy canopy"
    elif health_index >= 40:
        label = "Moderate stress signs"
    else:
        label = "Sparse / stressed canopy"

    return {
        "canopy_health_index": round(health_index, 1),
        "health_label": label,
        "crop_appearance": parsed.get("crop_appearance"),
        "vegetation_condition": parsed.get("vegetation_condition"),
        "visible_soil_notes": parsed.get("visible_soil_notes"),
        "stress_signs": parsed.get("stress_signs"),
        "general_condition_summary": parsed.get("general_condition_summary"),
        "source": "claude-vision",
    }
