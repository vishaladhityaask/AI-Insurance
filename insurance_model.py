"""
insurance_model.py
------------------
Core logic for premium calculation and weather risk simulation.
Phase 1 - Hackathon Prototype
"""

import random


def calculate_premium(daily_income: int) -> int:
    """
    Calculate weekly insurance premium based on average daily income.

    Tier logic:
      - Income < 800   → ₹20/week  (low earners, budget-friendly)
      - Income 800–1200 → ₹30/week  (mid earners)
      - Income > 1200  → ₹50/week  (high earners, higher coverage)

    Args:
        daily_income (int): Worker's average daily income in INR.

    Returns:
        int: Weekly premium amount in INR.
    """
    if daily_income < 800:
        return 20
    elif daily_income <= 1200:
        return 30
    else:
        return 50


def simulate_weather_risk(city: str) -> dict:
    """
    Simulate current weather risk for a given city.
    In Phase 1 this is random; Phase 2 will use a real weather API.

    Args:
        city (str): Name of the worker's city.

    Returns:
        dict: {
            'weather'    : str  – 'Rainy' | 'Cloudy' | 'Clear',
            'risk_level' : str  – 'High'  | 'Medium' | 'Low',
            'icon'       : str  – emoji icon for display,
            'color'      : str  – Bootstrap colour class,
            'message'    : str  – Human-readable tip for the worker,
        }
    """
    # Weighted random so rain appears ~30 % of the time for demo drama
    weather_choices = ["Rainy", "Rainy", "Cloudy", "Cloudy", "Cloudy", "Clear", "Clear"]
    weather = random.choice(weather_choices)

    profiles = {
        "Rainy": {
            "risk_level": "High",
            "icon": "🌧️",
            "color": "danger",
            "message": (
                f"Heavy rain alert in {city}! Your income protection is active. "
                "Stay safe and consider pausing deliveries."
            ),
        },
        "Cloudy": {
            "risk_level": "Medium",
            "icon": "⛅",
            "color": "warning",
            "message": (
                f"Overcast skies in {city}. Moderate disruption possible. "
                "Keep your insurance policy in mind."
            ),
        },
        "Clear": {
            "risk_level": "Low",
            "icon": "☀️",
            "color": "success",
            "message": (
                f"Clear skies in {city}. Great day for deliveries! "
                "Your coverage is still active in the background."
            ),
        },
    }

    result = {"weather": weather}
    result.update(profiles[weather])
    return result


def get_coverage_details(premium: int) -> dict:
    """
    Return coverage details corresponding to the premium tier.

    Args:
        premium (int): Weekly premium (20, 30, or 50).

    Returns:
        dict: Coverage amount and description.
    """
    tiers = {
        20: {
            "weekly_coverage": 400,
            "description": "Basic Plan – up to ₹400/week income protection",
        },
        30: {
            "weekly_coverage": 700,
            "description": "Standard Plan – up to ₹700/week income protection",
        },
        50: {
            "weekly_coverage": 1200,
            "description": "Premium Plan – up to ₹1200/week income protection",
        },
    }
    return tiers.get(premium, {"weekly_coverage": 0, "description": "Unknown Plan"})
