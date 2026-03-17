"""
insurance_model.py
Premium Calculator + Weather Risk Simulation Engine
"""

import random
import math
from datetime import datetime


# ─── Occupation Risk Table ────────────────────────────────────────────────────

OCCUPATION_RISK = {
    # ── Swiggy ──────────────────────────────────────────────
    "swiggy delivery partner":     {"base": 3200, "risk": "high",   "multiplier": 1.35},
    "swiggy instamart picker":     {"base": 2600, "risk": "medium", "multiplier": 1.15},
    "swiggy fleet supervisor":     {"base": 2200, "risk": "low",    "multiplier": 1.05},
    "swiggy restaurant partner":   {"base": 2000, "risk": "low",    "multiplier": 1.02},

    # ── Zepto ───────────────────────────────────────────────
    "zepto delivery partner":      {"base": 3000, "risk": "high",   "multiplier": 1.38},
    "zepto dark store picker":     {"base": 2500, "risk": "medium", "multiplier": 1.12},
    "zepto dark store packer":     {"base": 2300, "risk": "medium", "multiplier": 1.10},
    "zepto store manager":         {"base": 2100, "risk": "low",    "multiplier": 1.03},

    # ── Amazon ──────────────────────────────────────────────
    "amazon delivery associate":   {"base": 3400, "risk": "high",   "multiplier": 1.40},
    "amazon warehouse associate":  {"base": 2800, "risk": "medium", "multiplier": 1.20},
    "amazon sortation associate":  {"base": 2700, "risk": "medium", "multiplier": 1.18},
    "amazon flex delivery":        {"base": 3100, "risk": "high",   "multiplier": 1.32},
    "amazon last mile supervisor": {"base": 2400, "risk": "low",    "multiplier": 1.08},
    "amazon returns associate":    {"base": 2500, "risk": "medium", "multiplier": 1.12},
}

# ─── Region Base Conditions ───────────────────────────────────────────────────

REGION_CONDITIONS = {
    "North Zone":   {"base_risk": 1.00, "seasonal_variance": 0.08},
    "South Zone":   {"base_risk": 1.15, "seasonal_variance": 0.12},
    "East Zone":    {"base_risk": 1.20, "seasonal_variance": 0.10},
    "West Zone":    {"base_risk": 1.25, "seasonal_variance": 0.15},
    "Central Zone": {"base_risk": 1.05, "seasonal_variance": 0.06},
}


# ─── Weather Simulation ───────────────────────────────────────────────────────

def simulate_weather(region: str) -> dict:
    """
    Simulate real-time weather conditions for a region.
    Returns weather data and a risk multiplier.
    """
    cond = REGION_CONDITIONS.get(region, {"base_risk": 1.10, "seasonal_variance": 0.10})

    month = datetime.now().month
    # Monsoon spike (June–Sept in India)
    seasonal_factor = 1.0
    if 6 <= month <= 9:
        seasonal_factor = 1.15 if region in ("South Zone", "East Zone") else 1.08

    # Simulate weather values with some randomness
    base = cond["base_risk"] * seasonal_factor
    variance = cond["seasonal_variance"]

    temperature   = round(random.uniform(22, 42), 1)
    humidity      = round(random.uniform(30, 95), 1)
    wind_speed    = round(random.uniform(5, 45), 1)
    rainfall      = round(random.uniform(0, 80), 1)

    # Derive condition label
    if humidity > 85 and rainfall > 50:
        condition = "Heavy Rain"
        extra = 0.20
    elif wind_speed > 35:
        condition = "Storm Warning"
        extra = 0.25
    elif temperature > 38:
        condition = "Extreme Heat"
        extra = 0.18
    elif humidity > 75:
        condition = "Humid"
        extra = 0.10
    else:
        condition = "Clear"
        extra = 0.00

    risk_multiplier = round(base + random.uniform(-variance, variance) + extra, 3)
    risk_multiplier = max(0.90, min(risk_multiplier, 2.00))   # clamp

    return {
        "region":          region,
        "temperature":     temperature,
        "humidity":        humidity,
        "wind_speed":      wind_speed,
        "rainfall":        rainfall,
        "condition":       condition,
        "risk_multiplier": risk_multiplier,
    }


# ─── Age Factor ───────────────────────────────────────────────────────────────

def age_factor(age: int) -> float:
    """
    Younger and older workers carry higher risk.
    Sweet-spot: 30–40 years old.
    """
    if age < 25:
        return 1.20
    elif age < 30:
        return 1.10
    elif age <= 40:
        return 1.00
    elif age <= 50:
        return 1.12
    else:
        return 1.28


# ─── Core Premium Calculator ──────────────────────────────────────────────────

def calculate_premium(
    occupation: str,
    age: int,
    region: str,
    simulate_weather_flag: bool = True,
) -> dict:
    """
    Calculate insurance premium for a worker.

    Returns a detailed breakdown dict.
    """
    occ_key = occupation.lower().strip()
    occ_data = OCCUPATION_RISK.get(
        occ_key,
        {"base": 3000, "risk": "medium", "multiplier": 1.15}
    )

    base_premium    = occ_data["base"]
    occ_multiplier  = occ_data["multiplier"]
    risk_level      = occ_data["risk"]
    af              = age_factor(age)

    # Weather
    weather = simulate_weather(region) if simulate_weather_flag else {
        "region": region, "condition": "Unknown",
        "risk_multiplier": REGION_CONDITIONS.get(region, {}).get("base_risk", 1.10),
        "temperature": None, "humidity": None, "wind_speed": None, "rainfall": None,
    }
    wf = weather["risk_multiplier"]

    # Final premium
    final_premium = math.ceil(base_premium * occ_multiplier * af * wf)

    return {
        "base_premium":       base_premium,
        "final_premium":      final_premium,
        "risk_level":         risk_level,
        "occupation":         occupation,
        "age":                age,
        "region":             region,
        "occupation_factor":  occ_multiplier,
        "age_factor":         af,
        "weather_factor":     wf,
        "weather":            weather,
        "breakdown": {
            "step1_base":         base_premium,
            "step2_after_occ":    round(base_premium * occ_multiplier, 2),
            "step3_after_age":    round(base_premium * occ_multiplier * af, 2),
            "step4_final":        final_premium,
        }
    }


# ─── Batch Recalculation ──────────────────────────────────────────────────────

def recalculate_all_premiums(workers: list) -> list:
    """
    Given a list of worker dicts from DB, recalculate premiums with fresh weather.
    Returns list of (id, new_final_premium, weather_factor).
    """
    results = []
    for w in workers:
        res = calculate_premium(w["occupation"], w["age"], w["region"])
        results.append({
            "id":             w["id"],
            "final_premium":  res["final_premium"],
            "weather_factor": res["weather_factor"],
            "risk_level":     res["risk_level"],
        })
    return results


# ─── Quick test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = calculate_premium("Construction Worker", 35, "West Zone")
    print("=== Premium Calculation ===")
    for k, v in result.items():
        if k != "weather":
            print(f"  {k}: {v}")
    print("\n=== Weather Simulation ===")
    for k, v in result["weather"].items():
        print(f"  {k}: {v}")
