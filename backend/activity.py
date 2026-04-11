from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import aiosqlite

from backend.formulas import calculate_bio_age

WORKOUT_IMPACT_MAP: dict[str, dict[str, float]] = {
    "running": {"cv": -0.3, "neuro": -0.1},
    "walking": {"cv": -0.15},
    "weight_training": {"msk": -0.3, "met": -0.1},
    "yoga": {"msk": -0.2, "neuro": -0.2},
    "hiit": {"cv": -0.4, "met": -0.15},
    "swimming": {"cv": -0.3, "msk": -0.15},
    "cycling": {"cv": -0.25, "msk": -0.1},
}

WORKOUT_MATCH_MAP: dict[str, set[str]] = {
    "walking": {"walking", "running"},
    "running": {"running"},
    "cycling": {"cycling"},
    "swimming": {"swimming"},
    "yoga": {"yoga"},
    "strength": {"strength", "weight_training"},
    "weight_training": {"strength", "weight_training"},
    "hiit": {"hiit"},
}

STEP_EQUIVALENT_PER_MIN: dict[str, int] = {
    "walking": 95,
    "running": 135,
}

MAX_STEP_EQUIVALENT_PER_WORKOUT: int = 4000
MAX_STEP_EQUIVALENT_PER_DAY: int = 6000


def assess_outdoor_conditions(weather: dict[str, Any] | None, current_hour: int | None = None) -> dict[str, Any]:
    """Return a simple weather/AQI suitability summary for movement prompts."""

    payload = weather or {}
    temp = payload.get("temp_c")
    aqi = payload.get("aqi")
    uv = payload.get("uv_index")
    description = payload.get("description") or "Conditions unavailable"
    blockers: list[str] = []
    cautions: list[str] = []

    if aqi is not None:
        if aqi > 110:
            blockers.append(f"AQI {aqi} is elevated")
        elif aqi > 80:
            cautions.append(f"AQI {aqi} is only moderate")
    if temp is not None:
        if temp >= 36:
            blockers.append(f"{temp:.0f}°C is too hot for an outdoor push")
        elif temp >= 33 or temp <= 16:
            cautions.append(f"{temp:.0f}°C makes outdoor work less comfortable")
    if uv is not None and current_hour is not None and 10 <= current_hour <= 16:
        if uv >= 9:
            blockers.append(f"UV {uv:.0f} is high right now")
        elif uv >= 7:
            cautions.append(f"UV {uv:.0f} is strong")
    if current_hour is not None and (current_hour < 6 or current_hour >= 21):
        cautions.append("daylight is limited")

    outdoor_ok = not blockers
    outdoor_ideal = not blockers and not cautions
    note_parts = blockers or cautions or ["air and temperature look reasonable"]
    note = ", ".join(note_parts).capitalize() + "."
    label = "Good for outdoor movement" if outdoor_ideal else "Outdoor with caution" if outdoor_ok else "Prefer indoor movement"
    suggested_activity = (
        "Take a 15-minute outdoor walk"
        if outdoor_ideal
        else "Keep it short, shaded, and low-intensity outdoors"
        if outdoor_ok
        else "Choose an indoor walk, treadmill, or mobility set"
    )
    summary_bits = [description.title()]
    if temp is not None:
        summary_bits.append(f"{temp:.0f}°C")
    if aqi is not None:
        summary_bits.append(f"AQI {aqi}")
    if uv is not None:
        summary_bits.append(f"UV {uv:.0f}")

    return {
        "temp_c": temp,
        "aqi": aqi,
        "uv_index": uv,
        "description": description,
        "summary": " · ".join(summary_bits),
        "outdoor_ok": outdoor_ok,
        "outdoor_ideal": outdoor_ideal,
        "label": label,
        "note": note,
        "suggested_activity": suggested_activity,
        "blockers": blockers,
        "cautions": cautions,
    }


def _target_sessions_from_frequency(frequency: str) -> int:
    """Convert target frequency text like '5x/week' into a session count."""

    normalized = str(frequency or "").strip().lower()
    if normalized == "daily":
        return 7
    if normalized.endswith("x/week"):
        try:
            return max(1, int(normalized.split("x/week")[0]))
        except ValueError:
            return 1
    return 1


def _matching_workout_types(target_type: str) -> set[str]:
    """Return workout types that count toward a target session type."""

    normalized = str(target_type or "").strip().lower().replace(" ", "_")
    return WORKOUT_MATCH_MAP.get(normalized, {normalized})


def _step_equivalent_for_workout(workout: dict[str, Any]) -> int:
    """Return estimated steps contributed by one workout when step data is manual only."""

    workout_type = str(workout.get("type") or "").strip().lower().replace(" ", "_")
    duration = int(workout.get("duration_min") or 0)
    per_minute = STEP_EQUIVALENT_PER_MIN.get(workout_type, 0)
    return min(max(duration, 0) * per_minute, MAX_STEP_EQUIVALENT_PER_WORKOUT)


async def log_workout(user_id: str, workout_data: dict[str, Any], db: aiosqlite.Connection) -> dict[str, Any]:
    """Log a workout with computed bio-age impacts."""

    workout_type = str(workout_data.get("type", "walking")).lower().replace(" ", "_")
    impacts = dict(WORKOUT_IMPACT_MAP.get(workout_type, {"cv": -0.1}))
    duration = int(workout_data.get("duration_min") or 30)
    scale = min(duration / 30.0, 2.0)
    scaled = {key: round(value * scale, 3) for key, value in impacts.items()}
    cursor = await db.execute(
        """
        INSERT INTO workouts (user_id, type, duration_min, calories, source, date, cv_impact, msk_impact, met_impact, neuro_impact)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            user_id,
            workout_type,
            duration,
            workout_data.get("calories"),
            workout_data.get("source", "manual"),
            workout_data.get("date", str(date.today())),
            scaled.get("cv"),
            scaled.get("msk"),
            scaled.get("met"),
            scaled.get("neuro"),
        ),
    )
    await db.commit()
    return {
        "id": cursor.lastrowid,
        "user_id": user_id,
        "type": workout_type,
        "duration_min": duration,
        "calories": workout_data.get("calories"),
        "source": workout_data.get("source", "manual"),
        "date": workout_data.get("date", str(date.today())),
        "impact": scaled,
    }


async def get_workouts(user_id: str, db: aiosqlite.Connection, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch recent workouts for a user."""

    rows = await (
        await db.execute("SELECT * FROM workouts WHERE user_id=? ORDER BY date DESC, timestamp DESC LIMIT ?", (user_id, limit))
    ).fetchall()
    return [dict(row) for row in rows]


async def get_workout_summary(user_id: str, db: aiosqlite.Connection, days: int = 7) -> dict[str, Any]:
    """Summarize workouts over the last N days."""

    since = str(date.today() - timedelta(days=days - 1))
    rows = await (
        await db.execute("SELECT * FROM workouts WHERE user_id=? AND date>=? ORDER BY date ASC", (user_id, since))
    ).fetchall()
    total_minutes = sum(int(row["duration_min"] or 0) for row in rows)
    total_calories = round(sum(float(row["calories"] or 0) for row in rows), 1)
    workout_types: dict[str, int] = {}
    impact_totals = {"cv": 0.0, "msk": 0.0, "met": 0.0, "neuro": 0.0}
    chart_days = []
    for offset in range(days):
        current = date.today() - timedelta(days=days - offset - 1)
        day_rows = [row for row in rows if row["date"] == str(current)]
        chart_days.append({"day": current.strftime("%a"), "minutes": sum(int(row["duration_min"] or 0) for row in day_rows)})
    for row in rows:
        workout_types[row["type"]] = workout_types.get(row["type"], 0) + 1
        for key in impact_totals:
            impact_totals[key] += float(row[f"{key}_impact"] or 0)
    return {
        "total_sessions": len(rows),
        "total_minutes": total_minutes,
        "total_calories": total_calories,
        "workout_types": workout_types,
        "impact_totals": {key: round(value, 2) for key, value in impact_totals.items()},
        "avg_sessions_per_week": round(len(rows) * 7 / max(days, 1), 1),
        "chart": chart_days,
    }


async def get_today_activity_overlay(user_id: str, db: aiosqlite.Connection) -> dict[str, Any]:
    """Return today's logged-activity overlay for dashboards and activity UI."""

    today = str(date.today())
    rows = await (
        await db.execute("SELECT * FROM workouts WHERE user_id=? AND date=? ORDER BY timestamp DESC", (user_id, today))
    ).fetchall()
    workouts = [dict(row) for row in rows]
    manual_rows = [item for item in workouts if str(item.get("source") or "manual").lower() != "healthkit_mobile"]
    estimated_steps = min(sum(_step_equivalent_for_workout(item) for item in manual_rows), MAX_STEP_EQUIVALENT_PER_DAY)
    total_minutes = sum(int(item.get("duration_min") or 0) for item in workouts)
    total_calories = round(sum(float(item.get("calories") or 0) for item in workouts), 1)
    return {
        "estimated_steps_from_logged_activity": estimated_steps,
        "logged_workout_minutes_today": total_minutes,
        "logged_workout_calories_today": total_calories,
        "logged_cardio_sessions_today": sum(1 for item in workouts if str(item.get("type") or "").lower() in {"walking", "running"}),
        "steps_estimated": bool(estimated_steps),
    }


def workout_targets(profile: dict[str, Any]) -> dict[str, Any]:
    """Generate profile-aware weekly workout recommendations."""

    from backend.formulas import workout_targets as formula_workout_targets

    return formula_workout_targets(profile)


async def get_workout_targets(user_id: str, db: aiosqlite.Connection) -> dict[str, Any]:
    """Fetch the user's profile and return workout targets."""

    row = await (
        await db.execute(
            """
            SELECT p.*, u.age, u.sex, u.height_cm
            FROM profiles p JOIN users u ON u.id=p.user_id
            WHERE p.user_id=?
            """,
            (user_id,),
        )
    ).fetchone()
    targets = workout_targets(dict(row) if row else {})
    since = str(date.today() - timedelta(days=6))
    workout_rows = await (
        await db.execute("SELECT * FROM workouts WHERE user_id=? AND date>=? ORDER BY date DESC, timestamp DESC", (user_id, since))
    ).fetchall()
    workouts = [dict(item) for item in workout_rows]
    enriched_sessions: list[dict[str, Any]] = []
    for session in targets.get("recommended_sessions", []):
        matches = _matching_workout_types(session.get("type", ""))
        completed_workouts = [item for item in workouts if str(item.get("type", "")).lower() in matches]
        target_sessions = _target_sessions_from_frequency(session.get("frequency", "1x/week"))
        completed_sessions = len(completed_workouts)
        completed_minutes = sum(int(item.get("duration_min") or 0) for item in completed_workouts)
        target_minutes = int(target_sessions * int(session.get("duration_min") or 0))
        completion_ratio = min(completed_sessions / max(target_sessions, 1), 1.0)
        remaining_sessions = max(target_sessions - completed_sessions, 0)
        enriched_sessions.append(
            {
                **session,
                "target_sessions": target_sessions,
                "completed_sessions": completed_sessions,
                "remaining_sessions": remaining_sessions,
                "completed_minutes": completed_minutes,
                "target_minutes": target_minutes,
                "completion_ratio": round(completion_ratio, 3),
                "status": "complete" if completed_sessions >= target_sessions else "in_progress" if completed_sessions > 0 else "not_started",
                "counts_workout_types": sorted(matches),
                "last_logged_at": completed_workouts[0]["date"] if completed_workouts else None,
            }
        )
    targets["recommended_sessions"] = enriched_sessions
    targets["tracking_window_days"] = 7
    return targets


def check_inactivity(
    profile: dict[str, Any],
    current_hour: int,
    weather: dict[str, Any] | None = None,
    mental_score: float | None = None,
) -> dict[str, Any] | None:
    """Check if user is behind on daily activity and return a context-aware nudge."""

    hours_awake = max(current_hour - 7, 1)
    steps_avg = profile.get("steps_avg_7d") or 7500
    current_steps = profile.get("steps_today") or 0
    expected_steps = (steps_avg / 16) * hours_awake
    conditions = assess_outdoor_conditions(weather, current_hour)
    if current_steps < expected_steps * 0.6:
        behind = int(expected_steps - current_steps)
        if conditions["outdoor_ideal"]:
            return {
                "type": "step_nudge",
                "title": "Good window to move",
                "message": f"You're {behind:,} steps behind your usual pace. {conditions['summary']} makes this a good moment for a short outdoor walk.",
                "steps_behind": behind,
                "suggested_activity": "Take a 15-minute outdoor walk",
                "conditions": conditions,
            }
        if conditions["outdoor_ok"]:
            return {
                "type": "step_nudge",
                "title": "Move, but keep it cautious",
                "message": f"You're {behind:,} steps behind your usual pace. {conditions['summary']} is workable, but {conditions['note'].rstrip('.').lower()}. Keep it brief and shaded, or choose an indoor block.",
                "steps_behind": behind,
                "suggested_activity": "Take a short shaded walk or do 12 minutes indoors",
                "conditions": conditions,
            }
        return {
            "type": "step_nudge",
            "title": "Catch up indoors today",
            "message": f"You're {behind:,} steps behind your usual pace, but {conditions['note'].rstrip('.').lower()}. Use an indoor walk or treadmill block instead.",
            "steps_behind": behind,
            "suggested_activity": "Do 12 minutes of indoor walking or light cardio",
            "conditions": conditions,
        }
    if (profile.get("exercise_min") or 0) < 10 and current_hour >= 18:
        return {
            "type": "exercise_nudge",
            "title": "Short movement still counts",
            "message": "You have not moved much today. A short session still counts before the day ends.",
            "steps_behind": None,
            "suggested_activity": conditions["suggested_activity"] if conditions["outdoor_ideal"] else "Try 10 minutes of indoor mobility or bodyweight exercise",
            "conditions": conditions,
        }
    if mental_score is not None and mental_score < 70:
        if conditions["outdoor_ideal"] and 8 <= current_hour <= 18:
            return {
                "type": "fresh_air_reset",
                "title": "Fresh-air reset",
                "message": f"Mental wellness is running low at {mental_score:.0f}/100. {conditions['summary']} is a decent setup for a short outdoor reset.",
                "steps_behind": None,
                "suggested_activity": "Take a phone-free 10-minute fresh-air walk",
                "conditions": conditions,
            }
        if conditions["outdoor_ok"] and 8 <= current_hour <= 18:
            return {
                "type": "fresh_air_reset",
                "title": "Reset gently, with caution",
                "message": f"Mental wellness is running low at {mental_score:.0f}/100. {conditions['summary']} is not ideal because {conditions['note'].rstrip('.').lower()}. Choose shade, keep it brief, or do the reset indoors.",
                "steps_behind": None,
                "suggested_activity": "Take a 5-minute shaded break or do a 10-minute indoor breathing reset",
                "conditions": conditions,
            }
        return {
            "type": "fresh_air_reset",
            "title": "Reset your state indoors",
            "message": f"Mental wellness is running low at {mental_score:.0f}/100, but {conditions['note'].rstrip('.').lower()}. Do a 10-minute indoor breathing and mobility reset instead.",
            "steps_behind": None,
            "suggested_activity": "Step away from screens for 10 minutes of stretching and breathing",
            "conditions": conditions,
        }
    return None
