"""
Day 4: Canopy photo analysis -- a lightweight, HONEST stand-in for the
pitch deck's "CNN model extracting canopy health & NDVI indices" (Tier 2).

Training a real CNN needs a labeled image dataset and days of compute --
not realistic in a hackathon. Instead, this computes a green-pixel-ratio
heuristic from a plain smartphone photo, which correlates loosely with
canopy vigor and is a defensible "v0" of the same idea. In your pitch,
be upfront that this is a heuristic proxy, with real CNN/NDVI as the
stated roadmap (the deck's Tier 2 already frames it that way).
"""
import io

import cv2
import numpy as np
from PIL import Image

try:
    import pillow_avif  # noqa: F401  -- registers AVIF support with Pillow on import
except ImportError:
    pillow_avif = None  # AVIF uploads will raise a clear error if this isn't installed


def analyze_canopy_greenness(image_bytes: bytes) -> dict:
    """Returns a canopy health estimate from a leaf/field photo:
      - green_pixel_ratio: fraction of pixels classified as "green vegetation"
      - canopy_health_index: 0-100 score (green_pixel_ratio scaled, clipped)
      - health_label: a human-readable bucket for the UI
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        raise ValueError(
            f"Could not read this image ({e}). If it's a .avif or .heic photo "
            "(common on modern phone camera exports), make sure "
            "pillow-avif-plugin (or pillow-heif for .heic) is installed, or "
            "re-export/upload as .jpg or .png instead."
        )
    img_array = np.array(image)
    bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    # Green vegetation in HSV: hue ~35-85 (out of 180 in OpenCV), with
    # reasonable saturation/value so we don't count dark shadows or
    # washed-out sky/soil as "green".
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)

    green_pixel_ratio = float(np.count_nonzero(mask)) / mask.size
    canopy_health_index = round(min(green_pixel_ratio * 140, 100), 1)  # scaled + capped

    if canopy_health_index >= 70:
        label = "Healthy canopy"
    elif canopy_health_index >= 40:
        label = "Moderate stress signs"
    else:
        label = "Sparse / stressed canopy"

    return {
        "green_pixel_ratio": round(green_pixel_ratio, 4),
        "canopy_health_index": canopy_health_index,
        "health_label": label,
    }
