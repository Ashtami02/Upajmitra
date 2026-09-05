"""
Farmer-friendly explanation layer, sitting on top of the raw SHAP output
from model.py (explain_yield).

Why this exists: SHAP bar charts ("feature attribution", base values,
signed decimal numbers) are meaningful to a data scientist, not to a
farmer who may have little formal education and may not read English or
technical numbers comfortably. The pitch deck's "Explainable AI" stage
means the recommendation has to actually be understandable, not just
technically correct.

This module keeps ALL of the underlying ML explainability (nothing is
removed -- the raw SHAP contributions are still returned by /api/explain
for anyone who wants the technical view) and adds a second, plain-language
layer next to it:
  - a one-line headline verdict ("Your expected yield looks good")
  - a short list of the biggest reasons *why*, phrased as things a
    farmer can picture (fertilizer, water, weather, soil) instead of
    dataset column names
  - for the levers a farmer can actually act on this season (fertilizer,
    irrigation, sowing amount, sprays, plant health), a nudge toward the
    Optimize tab, which already computes an exact recommended amount --
    this layer explains "why", the optimizer answers "how much".

Bilingual (English / Hindi) since the frontend already supports both.
"""

# Friendly names + whether a farmer can change this lever mid-season.
# Context features (soil/climate/crop/region) aren't things a farmer
# decides today, but are still explained so the "why" makes sense.
FEATURE_INFO = {
    "crop_type": {
        "en": "Crop you're growing", "hi": "आपकी फसल", "controllable": False,
    },
    "soil_type": {
        "en": "Soil type", "hi": "मिट्टी का प्रकार", "controllable": False,
    },
    "region": {
        "en": "Your region", "hi": "आपका क्षेत्र", "controllable": False,
    },
    "nitrogen_kg_per_acre": {
        "en": "Nitrogen fertilizer", "hi": "नाइट्रोजन खाद", "controllable": True,
    },
    "phosphorus_kg_per_acre": {
        "en": "Phosphorus fertilizer", "hi": "फॉस्फोरस खाद", "controllable": True,
    },
    "potassium_kg_per_acre": {
        "en": "Potassium fertilizer", "hi": "पोटाश खाद", "controllable": True,
    },
    "irrigation_mm_per_week": {
        "en": "Watering (irrigation)", "hi": "सिंचाई (पानी)", "controllable": True,
    },
    "soil_ph": {
        "en": "Soil pH (acidity)", "hi": "मिट्टी का पीएच (अम्लता)", "controllable": False,
    },
    "organic_carbon_pct": {
        "en": "Natural richness of your soil", "hi": "मिट्टी की उर्वरता", "controllable": False,
    },
    "avg_temp_c": {
        "en": "Temperature", "hi": "तापमान", "controllable": False,
    },
    "rainfall_mm_season": {
        "en": "Rainfall this season", "hi": "इस मौसम की बारिश", "controllable": False,
    },
    "sowing_density_kg_per_acre": {
        "en": "Amount of seed sown", "hi": "बोए गए बीज की मात्रा", "controllable": True,
    },
    "pesticide_applications": {
        "en": "Pesticide spraying", "hi": "कीटनाशक का छिड़काव", "controllable": True,
    },
    "canopy_health_index": {
        "en": "Plant health (from your photo)", "hi": "पौधों की सेहत (फोटो से)", "controllable": True,
    },
}

_MAX_REASONS = 4


def _headline(predicted_yield: float, base_value: float, lang: str) -> str:
    """One-sentence verdict comparing the prediction to the model's
    typical (baseline) expectation, in plain words instead of a
    percentage a farmer would need to interpret."""
    if base_value <= 0:
        diff_pct = 0.0
    else:
        diff_pct = (predicted_yield - base_value) / base_value * 100

    if diff_pct >= 8:
        return (
            "✅ Your expected yield looks good — better than a typical farm like yours."
            if lang != "hi"
            else "✅ आपकी अनुमानित उपज अच्छी है — सामान्य से बेहतर।"
        )
    if diff_pct <= -8:
        return (
            "⚠️ Your expected yield looks lower than a typical farm like yours. See the reasons below."
            if lang != "hi"
            else "⚠️ आपकी अनुमानित उपज सामान्य से कम है। नीचे कारण देखें।"
        )
    return (
        "🟡 Your expected yield looks about average for a farm like yours."
        if lang != "hi"
        else "🟡 आपकी अनुमानित उपज सामान्य के बराबर है।"
    )


def _reason_message(feature: str, direction: str, lang: str) -> str:
    info = FEATURE_INFO.get(feature, {"en": feature, "hi": feature, "controllable": False})
    label = info["hi"] if lang == "hi" else info["en"]

    if info["controllable"]:
        if direction == "positive":
            return (
                f"👍 {label} is helping increase your yield right now."
                if lang != "hi"
                else f"👍 {label} अभी आपकी उपज बढ़ाने में मदद कर रहा है।"
            )
        return (
            f"👎 {label} is holding your yield back. Check the Optimize tab for the exact amount recommended for you."
            if lang != "hi"
            else f"👎 {label} आपकी उपज को कम कर रहा है। सही मात्रा जानने के लिए 'Optimize' टैब देखें।"
        )
    else:
        if direction == "positive":
            return (
                f"👍 {label} is working in your favor right now."
                if lang != "hi"
                else f"👍 {label} अभी आपके पक्ष में है।"
            )
        return (
            f"👎 {label} is working against your yield right now — this is outside your direct control this season."
            if lang != "hi"
            else f"👎 {label} अभी आपकी उपज को कम कर रहा है — यह इस मौसम में आपके नियंत्रण में नहीं है।"
        )


_UNIT = {
    "nitrogen_kg_per_acre": {"en": "kg/acre", "hi": "किग्रा/एकड़"},
    "phosphorus_kg_per_acre": {"en": "kg/acre", "hi": "किग्रा/एकड़"},
    "potassium_kg_per_acre": {"en": "kg/acre", "hi": "किग्रा/एकड़"},
    "irrigation_mm_per_week": {"en": "mm/week", "hi": "मिमी/सप्ताह"},
}

# Practical, actionable agronomy tips for each controllable lever, keyed by
# whether the optimizer says to raise or lower it. These are generic good
# practice (split-dosing, avoiding waterlogging, etc.) meant to turn a bare
# number ("N: 110kg") into something a farmer can actually act on.
_LEVER_TIPS = {
    "nitrogen_kg_per_acre": {
        "increase": {
            "en": "Apply it in 2-3 split doses instead of all at once — for example "
                  "about half at sowing/planting and the rest 20-25 days later — so "
                  "the crop can use it fully instead of it washing away.",
            "hi": "इसे एक साथ न देकर 2-3 बार में बांटकर डालें — जैसे लगभग आधी मात्रा "
                  "बुवाई के समय और बाकी 20-25 दिन बाद — ताकि फसल इसे पूरी तरह उपयोग कर सके "
                  "और बारिश/सिंचाई में बह न जाए।",
        },
        "decrease": {
            "en": "You're currently applying more than the optimum — cutting back to "
                  "this amount saves money on fertilizer without hurting yield much, "
                  "and reduces the risk of lodging (crop falling over).",
            "hi": "आप अभी ज़रूरत से ज़्यादा डाल रहे हैं — इसे इस मात्रा तक घटाने से खाद "
                  "का खर्च बचेगा, उपज पर ज़्यादा असर नहीं पड़ेगा, और फसल गिरने का खतरा भी कम होगा।",
        },
    },
    "phosphorus_kg_per_acre": {
        "increase": {
            "en": "Best applied as a basal dose — mix it into the soil at sowing time "
                  "close to the root zone, since phosphorus doesn't move much in soil "
                  "once applied.",
            "hi": "इसे बुवाई के समय आधार खुराक के रूप में जड़ों के पास मिट्टी में मिलाकर "
                  "डालें, क्योंकि फॉस्फोरस मिट्टी में डालने के बाद ज़्यादा नहीं फैलता।",
        },
        "decrease": {
            "en": "You can reduce phosphorus a little — soil test values suggest you "
                  "won't lose meaningful yield, and it lowers your input cost.",
            "hi": "आप फॉस्फोरस थोड़ा कम कर सकते हैं — मिट्टी की स्थिति के अनुसार इससे उपज "
                  "पर असर नहीं पड़ेगा और आपकी लागत घटेगी।",
        },
    },
    "potassium_kg_per_acre": {
        "increase": {
            "en": "Potash improves drought tolerance and grain quality — apply along "
                  "with phosphorus at sowing, or split it if your soil is very sandy.",
            "hi": "पोटाश सूखे से बचाव और दाने की गुणवत्ता को बेहतर करता है — इसे बुवाई के "
                  "समय फॉस्फोरस के साथ डालें, और अगर मिट्टी बलुई है तो इसे बांटकर डालें।",
        },
        "decrease": {
            "en": "You can bring potash down a bit without a meaningful yield loss, "
                  "freeing up money for the levers that matter more on your farm.",
            "hi": "आप पोटाश थोड़ा कम कर सकते हैं, इससे उपज पर खास असर नहीं पड़ेगा और वह "
                  "पैसा आपके खेत के लिए ज़्यादा ज़रूरी चीज़ों में लगेगा।",
        },
    },
    "irrigation_mm_per_week": {
        "increase": {
            "en": "Increase watering frequency or duration a little, ideally in the "
                  "early morning or evening to reduce evaporation loss — but avoid "
                  "letting water stand in the field.",
            "hi": "सिंचाई की मात्रा या बार थोड़ा बढ़ाएं, बेहतर होगा सुबह जल्दी या शाम को "
                  "ताकि पानी भाप बनकर कम उड़े — लेकिन खेत में पानी खड़ा न रहने दें।",
        },
        "decrease": {
            "en": "You're watering more than the crop needs right now — cutting back "
                  "saves water and pump/diesel cost, and reduces the risk of "
                  "waterlogging and root disease.",
            "hi": "आप अभी ज़रूरत से ज़्यादा सिंचाई कर रहे हैं — इसे कम करने से पानी और "
                  "पंप/डीज़ल का खर्च बचेगा, और जड़ सड़न व जलभराव का खतरा भी घटेगा।",
        },
    },
}

_ADVICE_HEADLINE = {
    "en": "🌱 How to reach this plan on your farm",
    "hi": "🌱 अपने खेत में यह योजना कैसे अपनाएं",
}

_NO_CHANGE_MSG = {
    "en": "is already close to the optimal amount — no real change needed here.",
    "hi": "पहले से ही सही मात्रा के करीब है — इसमें कोई बड़ा बदलाव करने की ज़रूरत नहीं है।",
}

_GENERAL_TIP = {
    "en": "🗓️ Don't change everything at once — adjust one or two inputs first, "
          "watch the crop for 1-2 weeks, then adjust the rest. This protects you if "
          "weather or market conditions shift.",
    "hi": "🗓️ सब कुछ एक साथ न बदलें — पहले एक-दो चीज़ों में बदलाव करें, 1-2 हफ्ते फसल पर "
          "नज़र रखें, फिर बाकी में बदलाव करें। इससे मौसम या बाज़ार बदलने पर भी आप सुरक्षित रहेंगे।",
}


def build_optimize_advice(base_profile: dict, recommended: dict, lang: str = "en"):
    """Turns the optimizer's raw recommended numbers into a farmer-facing,
    step-by-step explanation of HOW to change each controllable lever
    (nitrogen, phosphorus, potassium, irrigation) to reach the recommended
    plan -- not just the target numbers themselves.

    Returns (headline: str, steps: list[dict], general_tip: str)
    """
    lang = lang if lang == "hi" else "en"
    headline = _ADVICE_HEADLINE[lang]

    steps = []
    for feature in ["nitrogen_kg_per_acre", "phosphorus_kg_per_acre",
                     "potassium_kg_per_acre", "irrigation_mm_per_week"]:
        current = float(base_profile.get(feature, 0))
        target = float(recommended.get(feature, current))
        info = FEATURE_INFO[feature]
        label = info["hi"] if lang == "hi" else info["en"]
        unit = _UNIT[feature][lang]
        diff = target - current

        if abs(diff) < 1:
            message = f"{label} {_NO_CHANGE_MSG[lang]}"
            direction = "same"
        else:
            direction = "increase" if diff > 0 else "decrease"
            tip = _LEVER_TIPS[feature][direction][lang]
            if lang == "hi":
                verb = "बढ़ाएं" if direction == "increase" else "घटाएं"
                message = (
                    f"{label}: {current:.0f} से {target:.0f} {unit} तक {verb}। {tip}"
                )
            else:
                verb = "Increase" if direction == "increase" else "Decrease"
                message = (
                    f"{verb} {label.lower()} from {current:.0f} to {target:.0f} {unit}. {tip}"
                )

        steps.append({
            "feature": feature,
            "label": label,
            "current": round(current, 1),
            "recommended": round(target, 1),
            "direction": direction,
            "message": message,
        })

    return headline, steps, _GENERAL_TIP[lang]


def build_farmer_summary(predicted_yield: float, base_value: float, contributions, lang: str = "en"):
    """contributions: list of (feature, display_value, shap_value) exactly
    as returned by model.explain_yield, already sorted by |shap_value|.

    Returns (headline: str, reasons: list[{feature, label, message, direction}])
    """
    lang = lang if lang == "hi" else "en"
    headline = _headline(predicted_yield, base_value, lang)

    reasons = []
    for feature, _value, shap_value in contributions[:_MAX_REASONS]:
        direction = "positive" if shap_value >= 0 else "negative"
        info = FEATURE_INFO.get(feature, {"en": feature, "hi": feature})
        reasons.append({
            "feature": feature,
            "label": info["hi"] if lang == "hi" else info["en"],
            "message": _reason_message(feature, direction, lang),
            "direction": direction,
        })

    return headline, reasons
