"""Context-aware, time-sensitive smart reminders."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import aiosqlite

from backend.activity import assess_outdoor_conditions, check_inactivity
from backend.formulas import mental_wellness_score


async def generate_smart_reminders(
    user_id: str,
    profile: dict[str, Any],
    weather: dict[str, Any] | None,
    water_today_ml: int,
    db: aiosqlite.Connection,
) -> list[dict[str, Any]]:
    """Generate smart reminders from health, time, and context."""

    reminders: list[dict[str, Any]] = []
    now = datetime.now()
    hour = now.hour

    if hour <= 6:
        expected_ml = 0
    elif hour <= 12:
        expected_ml = int((hour - 6) / 6 * 1200)
    elif hour <= 18:
        expected_ml = int(1200 + (hour - 12) / 6 * 800)
    else:
        expected_ml = int(2000 + (hour - 18) / 6 * 500)

    if hour >= 7 and water_today_ml < expected_ml * 0.6:
        deficit = max(expected_ml - water_today_ml, 0)
        if hour >= 16 and water_today_ml < 1000:
            priority = "high"
            message = f"You've only had {water_today_ml}ml of water today. You're significantly behind — aim to drink {deficit}ml in the next 2 hours."
        elif water_today_ml < expected_ml * 0.4:
            priority = "high"
            message = f"Water intake is low: {water_today_ml}ml so far. You should be at ~{expected_ml}ml by now. Grab a glass."
        else:
            priority = "medium"
            message = f"You've had {water_today_ml}ml — target ~{expected_ml}ml by now. Drink {min(deficit, 500)}ml to catch up."
        reminders.append({"type": "water", "priority": priority, "message": message, "icon": "droplets", "action": "log_water"})

    steps = profile.get("steps_today") or 0
    step_goal = 7500
    exercise_min = profile.get("exercise_min") or 0
    if hour >= 14 and steps < step_goal * 0.4:
        pct = int(steps / step_goal * 100) if step_goal else 0
        reminders.append({
            "type": "movement",
            "priority": "high" if hour >= 18 else "medium",
            "message": f"Only {steps:,} steps ({pct}% of goal) by {hour}:00. A 20-minute walk adds ~2,000 steps and resets your focus.",
            "icon": "footprints",
            "action": "open_activity",
        })
    elif hour >= 10 and exercise_min < 15 and (profile.get("exercise_hours_week") or 4) >= 3:
        reminders.append({
            "type": "exercise",
            "priority": "medium",
            "message": "No exercise logged today yet. Even 15 minutes of movement improves HRV and mental clarity.",
            "icon": "activity",
            "action": "open_activity",
        })

    vitd = profile.get("vitamin_d")
    if vitd is not None and vitd < 20 and weather:
        is_sunny = weather.get("outdoor_ok", False) or weather.get("is_sunny", False)
        aqi = weather.get("aqi", 0)
        uv = weather.get("uv_index", 0)
        temp = weather.get("temp_c")
        if is_sunny and (aqi or 0) < 100 and (uv or 0) >= 3:
            message = f"Your Vitamin D is critically low at {vitd} ng/mL. It's sunny outside"
            if temp is not None:
                message += f" ({int(temp)}°C)"
            message += f" with UV index {uv}. Go outside for 20 minutes of sun exposure — your body needs it."
            reminders.append({"type": "vitamin_d", "priority": "high", "message": message, "icon": "sun", "action": None})
        elif vitd < 12:
            reminders.append({
                "type": "vitamin_d",
                "priority": "high",
                "message": f"Vitamin D is severely low at {vitd} ng/mL. Consider supplementation (1000-2000 IU/day). Talk to your doctor about a loading dose.",
                "icon": "pill",
                "action": None,
            })

    sleep_hours = profile.get("sleep_hours") or 0
    sleep_target = profile.get("sleep_target") or 8
    if hour >= 21 and sleep_hours < sleep_target - 1:
        reminders.append({
            "type": "sleep",
            "priority": "high",
            "message": f"You've been averaging {sleep_hours}h sleep (target: {sleep_target}h). Start your wind-down routine now — put devices away and dim lights.",
            "icon": "moon",
            "action": None,
        })
    elif hour >= 23:
        reminders.append({
            "type": "sleep",
            "priority": "high",
            "message": "It's past 11 PM. Every hour of sleep before midnight is worth more for deep sleep recovery. Get to bed.",
            "icon": "moon",
            "action": None,
        })

    hrv = profile.get("hrv_ms")
    stress = profile.get("stress_level")
    if hrv is not None and hrv < 40:
        reminders.append({
            "type": "recovery",
            "priority": "high",
            "message": f"Your HRV is low at {hrv}ms — your autonomic nervous system is under strain. Prioritize rest today: no intense workouts, focus on hydration and sleep.",
            "icon": "heart-pulse",
            "action": None,
        })
    elif stress is not None and stress >= 7:
        reminders.append({
            "type": "stress",
            "priority": "medium",
            "message": f"Your stress level is {stress}/10. Try 5 minutes of box breathing (4s in, 4s hold, 4s out, 4s hold) or a short walk.",
            "icon": "wind",
            "action": None,
        })

    screen = profile.get("screen_time_hours") or 0
    if screen >= 8 and hour >= 14:
        reminders.append({
            "type": "screen",
            "priority": "medium",
            "message": f"You're averaging {screen}h of screen time. Take a 20-20-20 break: every 20 min, look at something 20 feet away for 20 seconds. Your eyes and focus will thank you.",
            "icon": "monitor-off",
            "action": None,
        })

    last_meal = await (await db.execute("SELECT timestamp FROM meals WHERE user_id=? ORDER BY timestamp DESC LIMIT 1", (user_id,))).fetchone()
    if last_meal:
        try:
            last_meal_time = datetime.fromisoformat(str(last_meal["timestamp"]).replace(" ", "T"))
            hours_since_meal = (now - last_meal_time).total_seconds() / 3600
            if hours_since_meal > 5 and 8 <= hour <= 22:
                reminders.append({
                    "type": "nutrition",
                    "priority": "medium",
                    "message": f"It's been {int(hours_since_meal)} hours since your last logged meal. Eating regularly stabilizes blood sugar and prevents energy crashes.",
                    "icon": "utensils",
                    "action": "open_nutrition",
                })
        except (TypeError, ValueError):
            pass
    elif 12 <= hour <= 14:
        reminders.append({
            "type": "nutrition",
            "priority": "low",
            "message": "No meals logged today yet. Log your lunch to track your nutrition targets.",
            "icon": "utensils",
            "action": "open_nutrition",
        })

    last_posture = await (await db.execute("SELECT timestamp FROM posture_history WHERE user_id=? ORDER BY timestamp DESC LIMIT 1", (user_id,))).fetchone()
    posture_score = profile.get("posture_score_pct") or 0
    if posture_score < 70 and last_posture:
        try:
            last_posture_time = datetime.fromisoformat(str(last_posture["timestamp"]).replace(" ", "T"))
            if (now - last_posture_time).days >= 2:
                reminders.append({
                    "type": "posture",
                    "priority": "low",
                    "message": f"Your last posture score was {posture_score}%. A quick 30-second posture check can help you stay aware of slouching habits.",
                    "icon": "person-standing",
                    "action": "open_posture",
                })
        except (TypeError, ValueError):
            pass

    if weather and 6 <= hour <= 19:
        temp = weather.get("temp_c")
        aqi = weather.get("aqi", 0)
        if temp is not None and 15 <= temp <= 30 and (aqi or 0) < 80 and steps < step_goal * 0.7 and not any(item["type"] == "vitamin_d" for item in reminders):
            reminders.append({
                "type": "outdoor",
                "priority": "low",
                "message": f"Great weather outside ({int(temp)}°C, AQI {aqi}). Perfect conditions for a walk or outdoor workout.",
                "icon": "cloud-sun",
                "action": "open_activity",
            })

    try:
        spotify_row = await (await db.execute("SELECT avg_valence FROM spotify_history WHERE user_id=? ORDER BY timestamp DESC LIMIT 1", (user_id,))).fetchone()
        if spotify_row and (spotify_row["avg_valence"] or 1) < 0.35:
            reminders.append({
                "type": "mood",
                "priority": "medium",
                "message": "Your recent music suggests a low mood pattern. Consider putting on something upbeat, or talk through how you're feeling in the Mental Health chat.",
                "icon": "music",
                "action": "open_mental",
            })
    except Exception:
        pass

    weather_context = {**(weather or {}), **assess_outdoor_conditions(weather, hour)} if weather else {}
    try:
        wellness = mental_wellness_score(profile or {})
        nudge_profile = {
            **profile,
            "steps_today": steps,
            "exercise_min": exercise_min,
        }
        activity_nudge = check_inactivity(nudge_profile, hour, weather=weather_context, mental_score=wellness["score"])
        if activity_nudge:
            reminders.append({
                "type": activity_nudge["type"],
                "title": activity_nudge.get("title"),
                "priority": "low" if activity_nudge.get("conditions", {}).get("outdoor_ideal") else "medium" if activity_nudge.get("conditions", {}).get("outdoor_ok") else "high",
                "message": activity_nudge.get("message"),
                "icon": activity_nudge.get("type"),
                "action": "open_mental" if activity_nudge.get("type") == "fresh_air_reset" else "open_activity",
                "suggested_activity": activity_nudge.get("suggested_activity"),
                "conditions": activity_nudge.get("conditions"),
            })
    except Exception:
        pass

    priority_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(reminders, key=lambda item: priority_order.get(item["priority"], 3))
