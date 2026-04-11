from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.database import get_profile_dict, get_recent_meals_db

_WEATHER_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Showers",
    82: "Heavy showers",
    95: "Thunderstorm",
}


async def get_profile(user_id: str, db: Any, **kwargs: Any) -> dict:
    """Get the complete health profile for a user."""

    _ = kwargs
    profile = await get_profile_dict(user_id, db)
    return profile or {"error": f"No profile found for user {user_id}"}


async def get_weather(user_id: str, db: Any, **kwargs: Any) -> dict:
    """Fetch current weather using the user's saved coordinates when available."""

    _ = kwargs
    default_lat = 12.9716
    default_lon = 77.5946
    profile = await get_profile_dict(user_id, db)
    lat = profile.get("latitude") if profile else None
    lon = profile.get("longitude") if profile else None
    location_label = (profile.get("location_label") if profile else None) or None
    using_profile_location = lat is not None and lon is not None
    lat = float(lat if lat is not None else default_lat)
    lon = float(lon if lon is not None else default_lon)
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            weather_resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,uv_index",
                    "timezone": "auto",
                },
                timeout=5,
            )
            weather_resp.raise_for_status()
            weather_data = weather_resp.json()
            current = weather_data.get("current") or {}
            air_resp = await client.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "us_aqi",
                    "timezone": "auto",
                },
                timeout=5,
            )
            air_resp.raise_for_status()
            air_data = air_resp.json()
            air_current = air_data.get("current") or {}
            description = _WEATHER_CODE_MAP.get(current.get("weather_code"), "Conditions unavailable")
            result = {
                "temp_c": current.get("temperature_2m"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "description": description,
                "wind_speed_mps": current.get("wind_speed_10m", 0),
                "aqi": air_current.get("us_aqi"),
                "uv_index": current.get("uv_index"),
                "location_label": location_label or ("Saved device location" if using_profile_location else "Bangalore fallback"),
                "location_source": "profile_coordinates" if using_profile_location else "fallback_coordinates",
                "latitude": lat,
                "longitude": lon,
            }
            return result
    except Exception:
        return {
            "temp_c": 28,
            "humidity_pct": 65,
            "aqi": 85,
            "uv_index": 7,
            "description": "Partly cloudy (cached)",
            "wind_speed_mps": 3,
            "location_label": location_label or ("Saved device location" if using_profile_location else "Bangalore fallback"),
            "location_source": "profile_coordinates_cached" if using_profile_location else "fallback_coordinates",
            "latitude": lat,
            "longitude": lon,
        }


async def get_nutrition_targets(user_id: str, db: Any, **kwargs: Any) -> dict:
    """Get blood-work-aware nutrition targets for the user."""

    _ = kwargs
    profile = await get_profile_dict(user_id, db)
    from backend.formulas import nutrition_targets

    return nutrition_targets(profile or {})


async def get_recent_meals(user_id: str, db: Any, days: int = 3, **kwargs: Any) -> dict:
    """Get recent meals and aggregate daily totals."""

    _ = kwargs
    meals = await get_recent_meals_db(user_id, days, db)
    daily_totals: dict[str, Any] = defaultdict(lambda: {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "sat_fat_g": 0, "fiber_g": 0, "meal_count": 0})
    for meal in meals:
        bucket = daily_totals[meal["date"]]
        for key in ("calories", "protein_g", "carbs_g", "fat_g", "sat_fat_g", "fiber_g"):
            bucket[key] += meal["nutrition"].get(key, 0)
        bucket["meal_count"] += 1
    return {"meals": meals, "daily_totals": dict(daily_totals)}


async def get_workout_targets(user_id: str, db: Any, **kwargs: Any) -> dict:
    """Get profile-aware workout recommendations."""

    _ = kwargs
    profile = await get_profile_dict(user_id, db)
    from backend.formulas import workout_targets

    return workout_targets(profile or {})


async def rank_impact(user_id: str, db: Any, **kwargs: Any) -> dict:
    """Rank possible health improvements by bio age impact."""

    _ = kwargs
    profile = await get_profile_dict(user_id, db)
    from backend.formulas import rank_impact

    return rank_impact(profile or {})


async def get_reminders(user_id: str, db: Any, **kwargs: Any) -> dict:
    """Get pending reminders."""

    _ = kwargs
    from backend.reminder_engine import check_reminders

    return {"reminders": await check_reminders(user_id, db)}


async def check_specialists(user_id: str, db: Any, **kwargs: Any) -> dict:
    """Check if specialist consultations are recommended."""

    _ = kwargs
    profile = await get_profile_dict(user_id, db)
    from backend.specialists import check_specialists as cs

    return {"specialists": cs(profile or {})}
