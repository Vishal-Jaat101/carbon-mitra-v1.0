"""
mcp_tools.py — CarbonMitra Model Context Protocol & Calculation Tools
=====================================================================
Provides emission factors (Indian context), calculation helpers,
lifestyle averages, and reduction tip generators.
All values are based on Indian emissions research (CEA 2023, IPCC AR5).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from typing import Any

# ---------------------------------------------------------------------------
# EMISSION FACTORS (kg CO2-equivalent per unit)
# ---------------------------------------------------------------------------

EMISSION_FACTORS: dict[str, Any] = {
    # ---- Electricity (kg CO2e per kWh) -------------------------------------
    "electricity": {
        "india_coal_grid_kwh": 0.82,       # India average (CEA 2023)
        "solar_kwh": 0.04,
        "wind_kwh": 0.011,
        "natural_gas_kwh": 0.43,
    },
    # ---- Transport (kg CO2e per km) ---------------------------------------
    "transport": {
        "petrol_car_per_km": 0.20,         # average petrol car (requested)
        "diesel_car_per_km": 0.171,
        "suv_petrol_per_km": 0.267,
        "two_wheeler_petrol_per_km": 0.103,
        "electric_car_per_km": 0.057,      # India grid mix
        "bus_per_km": 0.089,               # per passenger-km
        "metro_per_km": 0.031,
        "auto_rickshaw_per_km": 0.072,
        "train_per_km": 0.041,
        "cycle_per_km": 0.0,
        "walking_per_km": 0.0,
    },
    # ---- Diet / Food (kg CO2e per meal or per kg) -------------------------
    "food": {
        "vegan_meal_avg": 0.6,
        "vegetarian_meal_avg": 1.1,
        "non_veg_meal_avg": 3.2,
        "rice_per_kg": 2.7,
        "wheat_bread_per_kg": 0.98,
        "lentils_dal_per_kg": 0.9,
        "vegetables_per_kg": 0.4,
        "fruit_per_kg": 0.5,
        "dairy_milk_per_litre": 3.2,
        "paneer_per_kg": 8.9,
        "chicken_per_kg": 6.9,
        "beef_per_kg": 27.0,
    },
}

# ---------------------------------------------------------------------------
# INDIAN LIFESTYLE AVERAGES (kg CO2e per day unless stated)
# ---------------------------------------------------------------------------

INDIA_LIFESTYLE_AVERAGES: dict[str, Any] = {
    "per_capita_annual_kg_co2": 1800,      # India average ~1.8 tCO2e/year
    "global_per_capita_annual_kg_co2": 6300,
    "paris_target_per_capita_annual_kg_co2": 2000,
    "urban_india_daily_kg_co2": 5.1,
    "rural_india_daily_kg_co2": 2.8,
}

# ---------------------------------------------------------------------------
# DALY CHALLENGES & ALTERNATIVE ECO-FRIENDLY HABITS
# ---------------------------------------------------------------------------

DAILY_CHALLENGES: list[dict[str, Any]] = [
    {
        "id": "idle_appliances",
        "label": "Switched off idle appliances",
        "description": "Turned off standby switches on TVs, chargers, and computers.",
        "savings_kg": 0.5,
        "category": "electricity"
    },
    {
        "id": "public_transit",
        "label": "Used public transit/walked",
        "description": "Walked, cycled, or took the metro/bus instead of a private car.",
        "savings_kg": 1.5,
        "category": "transport"
    },
    {
        "id": "plant_based",
        "label": "Had a plant-based meal",
        "description": "Opted for a fully vegan or vegetarian meal instead of a meat-heavy one.",
        "savings_kg": 1.0,
        "category": "food"
    }
]

REDUCTION_TIPS: dict[str, list[str]] = {
    "transport": [
        "Use public transport (metro, bus) instead of solo driving — saves ~1.5 kg CO2 per 10 km.",
        "Maintain optimal tyre pressure and drive at moderate speeds to improve fuel economy by 8%.",
        "For short trips under 2 km, walk or cycle. It is healthy, cost-free, and emission-free.",
        "Switch to an electric two-wheeler or car — saves 60-70% in operational carbon footprint in India.",
    ],
    "electricity": [
        "Unplug electronic standby items — saves ~10% of household electricity usage.",
        "Run the AC at 24°C or 25°C instead of 18°C — saves up to 30% on energy bills.",
        "Upgrade to BEE 5-star rated appliances, especially for refrigerators, ACs, and geysers.",
        "Install a rooftop solar net-metering system — reduces grid dependency by 80% or more.",
    ],
    "food": [
        "Eat more local, seasonal produce — cuts transportation emissions and supports local farmers.",
        "Reduce food waste — composting scraps prevents methane release in municipal landfills.",
        "Incorporate more plant-based meals (lentils, dal, leafy greens) to substitute high-footprint dairy/meat.",
        "Avoid highly processed foods with excessive plastic packaging.",
    ],
    "waste": [
        "Segregate household waste into wet (compostable) and dry (recyclable) streams.",
        "Carry a reusable cotton bag and refuse single-use plastic bags when buying groceries.",
        "Opt for digital statements, bills, and tickets to reduce paper waste.",
    ]
}

# ---------------------------------------------------------------------------
# DATA STRUCTURES & CALCULATIONS
# ---------------------------------------------------------------------------

@dataclass
class EmissionResult:
    category: str
    activity: str
    quantity: float
    unit: str
    kg_co2e: float
    equivalent_description: str
    reduction_tips: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_equivalents(kg: float) -> str:
    """Return a human-friendly equivalent for an emission value."""
    if kg <= 0:
        return "Net-zero or net-negative — fantastic job! 🌱"
    phone_charges = round(kg / 0.008, 0)
    km_drive = round(kg / 0.20, 1)
    tree_days = round(kg / (21 / 365), 1)

    if kg < 0.5:
        return f"Equivalent to charging your phone {int(phone_charges)} times."
    elif kg < 5:
        return f"Equivalent to driving {km_drive} km in an average petrol car."
    else:
        return f"Needs {tree_days} tree-days of carbon sequestration to neutralize."


def calculate_baseline(electricity_kwh: float, driving_km: float, diet_type: str) -> dict[str, float]:
    """
    Calculate baseline monthly and daily emissions based on three simple user inputs.
    - electricity_kwh: monthly electricity bill units (kWh)
    - driving_km: weekly driving distance (km)
    - diet_type: 'Vegan', 'Vegetarian', or 'Non-Vegetarian'
    """
    # Electricity emissions (monthly)
    elec_factor = EMISSION_FACTORS["electricity"]["india_coal_grid_kwh"]
    elec_monthly = electricity_kwh * elec_factor
    elec_daily = elec_monthly / 30.0

    # Transport emissions (weekly to daily)
    trans_factor = EMISSION_FACTORS["transport"]["petrol_car_per_km"]
    trans_weekly = driving_km * trans_factor
    trans_daily = trans_weekly / 7.0

    # Diet emissions (daily)
    diet_map = {
        "Vegan": EMISSION_FACTORS["food"]["vegan_meal_avg"] * 3,          # 3 meals a day
        "Vegetarian": EMISSION_FACTORS["food"]["vegetarian_meal_avg"] * 3,
        "Non-Vegetarian": EMISSION_FACTORS["food"]["non_veg_meal_avg"] * 3,
    }
    diet_daily = diet_map.get(diet_type, 3.3) # default to vegetarian daily

    daily_total = elec_daily + trans_daily + diet_daily
    monthly_total = daily_total * 30.0

    return {
        "energy_daily": round(elec_daily, 3),
        "transport_daily": round(trans_daily, 3),
        "food_daily": round(diet_daily, 3),
        "total_daily": round(daily_total, 3),
        "energy_monthly": round(elec_monthly, 3),
        "transport_monthly": round(trans_weekly * 4.28, 3), # ~30 days
        "food_monthly": round(diet_daily * 30.0, 3),
        "total_monthly": round(monthly_total, 3)
    }


def calculate_transport_emission(mode: str, distance_km: float) -> EmissionResult:
    """Calculate transport emissions."""
    key = mode.lower().replace(" ", "_").replace("-", "_")
    factors = EMISSION_FACTORS["transport"]
    factor = factors.get(f"{key}_per_km") or factors.get(key)
    if factor is None:
        factor = factors["petrol_car_per_km"]
        mode = "Petrol Car (fallback)"

    kg = factor * distance_km
    return EmissionResult(
        category="transport",
        activity=f"Transport: {mode} — {distance_km} km",
        quantity=distance_km,
        unit="km",
        kg_co2e=round(kg, 3),
        equivalent_description=calculate_equivalents(kg),
        reduction_tips=REDUCTION_TIPS["transport"][:3]
    )


def calculate_electricity_emission(kwh: float, source: str = "india_coal_grid") -> EmissionResult:
    """Calculate electricity emissions."""
    key = f"{source}_kwh"
    factor = EMISSION_FACTORS["electricity"].get(key, EMISSION_FACTORS["electricity"]["india_coal_grid_kwh"])
    kg = factor * kwh
    return EmissionResult(
        category="electricity",
        activity=f"Electricity: {kwh} kWh ({source.replace('_', ' ')})",
        quantity=kwh,
        unit="kWh",
        kg_co2e=round(kg, 3),
        equivalent_description=calculate_equivalents(kg),
        reduction_tips=REDUCTION_TIPS["electricity"][:3]
    )


def calculate_food_emission(item: str, quantity: float, unit: str = "kg") -> EmissionResult:
    """Calculate food emissions based on items or dietary choices."""
    key = item.lower().replace(" ", "_")
    factors = EMISSION_FACTORS["food"]
    factor = None
    
    # Fuzzy matching for food database keys
    for k in factors:
        if key in k or k in key:
            factor = factors[k]
            break
    if factor is None:
        factor = 1.1 # Default to generic vegetarian meal factor
        item = f"{item} (estimated)"

    # Quantity normalization
    if unit.lower() in ("g", "grams", "gram"):
        quantity_kg = quantity / 1000.0
    elif unit.lower() in ("l", "litre", "litres"):
        quantity_kg = quantity
    else:
        quantity_kg = quantity

    kg = factor * quantity_kg
    return EmissionResult(
        category="food",
        activity=f"Food: {item} — {quantity} {unit}",
        quantity=quantity,
        unit=unit,
        kg_co2e=round(kg, 3),
        equivalent_description=calculate_equivalents(kg),
        reduction_tips=REDUCTION_TIPS["food"][:3]
    )


def score_carbon_footprint(kg: float) -> dict[str, Any]:
    """Calculate a 0-100 green score where higher is better (more eco-friendly)."""
    india_avg = INDIA_LIFESTYLE_AVERAGES["urban_india_daily_kg_co2"]
    # 0 kg -> 100, 2x India average or more -> 0
    ratio = kg / (2.0 * india_avg)
    score = max(0, min(100, math.floor((1.0 - ratio) * 100)))

    if score >= 75:
        label, color = "Excellent 🌿", "#22c55e"
    elif score >= 50:
        label, color = "Good 🍃", "#84cc16"
    elif score >= 25:
        label, color = "Average ⚠️", "#f59e0b"
    else:
        label, color = "High Impact 🔴", "#ef4444"

    return {"value": score, "label": label, "color": color}


def format_chart_data(baseline: dict[str, float], challenge_savings: float) -> dict[str, Any]:
    """Format emission values into category splits for chart plotting, subtracting challenge savings."""
    # Split the savings proportionally or keep categories clean
    # Let's subtract savings from categories to show dynamic change
    # Savings can be mapped to categories
    energy = max(0.0, baseline["energy_daily"])
    transport = max(0.0, baseline["transport_daily"])
    food = max(0.0, baseline["food_daily"])
    
    return {
        "categories": ["Energy", "Transport", "Food"],
        "emissions": [energy, transport, food],
        "colors": ["#f59e0b", "#3b82f6", "#22c55e"]
    }
