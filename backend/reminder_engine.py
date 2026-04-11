from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import aiosqlite

from backend.activity import check_inactivity, get_today_activity_overlay

DATA_REFRESH_INTERVALS: dict[str, int] = {
    "healthkit": 2,
    "apple_health": 2,
    "meal": 1,
    "water": 1,
    "posture": 7,
    "faceage": 30,
    "face_age": 30,
    "blood_report": 90,
    "cultfit": 30,
    "mental_checkin": 14,
    "manual_mobile": 7,
    "spotify": 3,
}

URGENCY_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}
SOURCE_LABELS: dict[str, str] = {
    "healthkit": "HealthKit Sync",
    "apple_health": "Apple Health Import",
    "manual_mobile": "iPhone Manual Inputs",
    "blood_report": "Blood Report",
    "cultfit": "Cult.fit Scan",
    "faceage": "Face Age Selfie",
    "face_age": "Face Age Selfie",
    "posture": "Posture Check",
    "meal": "Meal Analysis",
    "water": "Water Tracking",
    "mental_checkin": "PHQ-9 Calibration",
    "spotify": "Spotify Sync",
    "vitamin_d_retest": "Vitamin D Retest",
    "glucose_retest": "Glucose Retest",
    "general_checkup": "General Checkup",
    "blood_panel": "Blood Panel Follow-up",
}


def _parse_dt(value: str | None) -> datetime | None:
    """Parse a stored datetime/date string into a datetime."""

    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[: len(fmt)], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _source_label(source: str) -> str:
    """Return a human-friendly label for a data source or reminder source."""

    return SOURCE_LABELS.get(source, source.replace("_", " ").title())


def _format_refresh_message(label: str, interval: int, days_since: int | None, overdue: int) -> str:
    """Return a user-facing freshness message with exact timing context."""

    if label == "PHQ-9 Calibration":
        if days_since is None:
            return "PHQ-9 has not been calibrated for this profile yet. Recommended refresh: every 14 days."
        if overdue > 0:
            return f"PHQ-9 was last calibrated {days_since} days ago. Recommended refresh: every {interval} days. It is {overdue} days overdue."
        days_remaining = max(interval - days_since, 0)
        return f"PHQ-9 was last calibrated {days_since} days ago. Recommended refresh: every {interval} days. Next refresh in about {days_remaining} days."
    if days_since is None:
        return f"{label} has not been uploaded yet. Recommended refresh: every {interval} days."
    if overdue > 0:
        return f"{label} was last uploaded {days_since} days ago. Recommended refresh: every {interval} days. It is {overdue} days overdue."
    days_remaining = max(interval - days_since, 0)
    return f"{label} was last uploaded {days_since} days ago. Recommended refresh: every {interval} days. Next refresh in about {days_remaining} days."


def _build_source_freshness_row(source: str, last_synced_value: str | None, interval: int) -> dict[str, Any]:
    """Build one source freshness row with exact timestamps and due status."""

    last_synced = _parse_dt(last_synced_value)
    now = datetime.now()
    days_since = None if last_synced is None else max((now - last_synced).days, 0)
    overdue = interval if last_synced is None else max(days_since - interval, 0)
    if last_synced is None:
        status = "missing"
        urgency = "high"
        next_due_at = None
    else:
        next_due_at = last_synced + timedelta(days=interval)
        if overdue > 0:
            status = "overdue"
            urgency = "high" if overdue > interval else "medium"
        elif days_since >= max(interval - 3, 0):
            status = "due_soon"
            urgency = "medium"
        else:
            status = "fresh"
            urgency = "low"
    label = _source_label(source)
    return {
        "type": "data_freshness",
        "source": source,
        "label": label,
        "message": _format_refresh_message(label, interval, days_since, overdue),
        "urgency": urgency,
        "status": status,
        "recommended_interval_days": interval,
        "days_since_upload": days_since,
        "days_overdue": overdue,
        "days_until_due": None if days_since is None else max(interval - days_since, 0),
        "last_synced": last_synced.isoformat(sep=" ", timespec="seconds") if last_synced else None,
        "next_due_at": next_due_at.isoformat(sep=" ", timespec="seconds") if next_due_at else None,
    }


async def get_data_freshness(user_id: str, db: aiosqlite.Connection) -> list[dict[str, Any]]:
    """Return exact freshness metadata for uploaded data sources and medical retest items."""

    rows = await (await db.execute("SELECT * FROM data_sources WHERE user_id=?", (user_id,))).fetchall()
    profile = await (await db.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,))).fetchone()
    row_map = {row["source"]: dict(row) for row in rows}
    sources = ["apple_health", "blood_report", "cultfit", "face_age", "posture", "spotify", "mental_checkin", "meal", "water"]
    freshness_rows = []
    for source in sources:
        lookup_source = source
        source_row = row_map.get(source)
        if source == "apple_health" and source_row is None:
            source_row = row_map.get("healthkit")
            lookup_source = "healthkit"
        if source == "face_age" and source_row is None:
            source_row = row_map.get("faceage")
            lookup_source = "faceage"
        interval = (source_row or {}).get("refresh_interval_days") or DATA_REFRESH_INTERVALS.get(source) or DATA_REFRESH_INTERVALS.get(lookup_source, 7)
        if source == "mental_checkin":
            interval = DATA_REFRESH_INTERVALS["mental_checkin"]
        freshness_rows.append(_build_source_freshness_row(source, (source_row or {}).get("last_synced_at"), interval))

    if profile:
        medical_windows = [
            ("vitamin_d_retest", profile["last_vitd_test_date"], 90, "Vitamin D Retest"),
            ("glucose_retest", profile["last_glucose_test_date"], 90, "Glucose Retest"),
            ("blood_panel", profile["last_blood_report_date"], 90 if (profile["ldl"] or 0) > 130 else 180, "Blood Panel Follow-up"),
            ("general_checkup", profile["last_general_checkup_date"], 365, "Annual General Checkup"),
        ]
        for source, last_synced_value, interval, label in medical_windows:
            item = _build_source_freshness_row(source, last_synced_value, interval)
            item["label"] = label
            item["type"] = "medical_retest"
            item["message"] = _format_refresh_message(label, interval, item["days_since_upload"], item["days_overdue"])
            freshness_rows.append(item)

    return sorted(
        freshness_rows,
        key=lambda item: (
            0 if item["type"] == "data_freshness" else 1,
            -URGENCY_RANK.get(item["urgency"], 0),
            -(item["days_overdue"] or 0),
            item["recommended_interval_days"],
            item["label"],
        ),
    )


async def get_reminders(user_id: str, db: aiosqlite.Connection) -> list[dict[str, Any]]:
    """Generate all reminders for a user."""

    reminders: list[dict[str, Any]] = []
    profile = await (await db.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,))).fetchone()
    profile_dict = dict(profile) if profile else None
    source_rows = await (await db.execute("SELECT * FROM data_sources WHERE user_id=?", (user_id,))).fetchall()
    normal_blood = True
    if profile:
        normal_blood = all(
            [
                (profile["ldl"] is None or profile["ldl"] <= 100),
                (profile["vitamin_d"] is None or profile["vitamin_d"] >= 20),
                (profile["fasting_glucose"] is None or profile["fasting_glucose"] <= 100),
                (profile["hba1c"] is None or profile["hba1c"] <= 5.7),
            ]
        )
    for row in source_rows:
        source = row["source"]
        interval = row["refresh_interval_days"] or DATA_REFRESH_INTERVALS.get(source, 7)
        if source == "mental_checkin":
            interval = DATA_REFRESH_INTERVALS["mental_checkin"]
        if source == "blood_report":
            interval = 180 if normal_blood else 90
        freshness = _build_source_freshness_row(source, row["last_synced_at"], interval)
        overdue = freshness["days_overdue"]
        if overdue <= 0:
            continue
        reminders.append(freshness)
    def medical(source: str, message: str, days_overdue: int) -> None:
        urgency = "high" if days_overdue > 30 else "medium"
        label = _source_label(source)
        reminders.append(
            {
                "type": "medical_checkup",
                "source": source,
                "label": label,
                "message": message,
                "urgency": urgency,
                "days_overdue": days_overdue,
                "last_synced": None,
            }
        )
    if profile:
        vitd_test = _parse_dt(profile["last_vitd_test_date"])
        if (profile["vitamin_d"] or 100) < 20 and vitd_test and (date.today() - vitd_test.date()).days > 90:
            medical("vitamin_d_retest", "Vitamin D is low and retesting is overdue.", (date.today() - vitd_test.date()).days - 90)
        glucose_test = _parse_dt(profile["last_glucose_test_date"])
        if (profile["fasting_glucose"] or 0) > 100 and glucose_test and (date.today() - glucose_test.date()).days > 90:
            medical("glucose_retest", "Elevated fasting glucose should be rechecked.", (date.today() - glucose_test.date()).days - 90)
        general_checkup = _parse_dt(profile["last_general_checkup_date"])
        if general_checkup is None or (date.today() - general_checkup.date()).days > 365:
            medical("general_checkup", "Annual general checkup is due.", 0 if general_checkup is None else (date.today() - general_checkup.date()).days - 365)
        blood_test = _parse_dt(profile["last_blood_report_date"])
        blood_interval = 90 if (profile["ldl"] or 0) > 130 else 180
        if blood_test and (date.today() - blood_test.date()).days > blood_interval:
            medical("blood_panel", "Blood lipid panel follow-up is due.", (date.today() - blood_test.date()).days - blood_interval)
    if profile_dict:
        from backend.tools.context_tools import get_weather

        now = datetime.now()
        mental_score = profile_dict.get("mental_wellness_score")
        weather = await get_weather(user_id, db)
        activity_overlay = await get_today_activity_overlay(user_id, db)
        nudge_profile = {
            **profile_dict,
            "steps_today": int(profile_dict.get("steps_today") or 0) + int(activity_overlay.get("estimated_steps_from_logged_activity") or 0),
            "exercise_min": max(int(profile_dict.get("exercise_min") or 0), int(activity_overlay.get("logged_workout_minutes_today") or 0)),
        }
        nudge = check_inactivity(nudge_profile, now.hour, weather=weather, mental_score=mental_score)
        if nudge:
            conditions = nudge.get("conditions") or {}
            reminders.append(
                {
                    "type": "contextual_activity",
                    "source": nudge.get("type", "daily_movement"),
                    "label": nudge.get("title", "Daily activity"),
                    "message": nudge.get("message"),
                    "urgency": "medium" if nudge.get("steps_behind") else "low",
                    "days_overdue": 0,
                    "last_synced": None,
                    "suggested_activity": nudge.get("suggested_activity"),
                    "conditions_summary": conditions.get("summary"),
                    "conditions_note": conditions.get("note"),
                }
            )
    return sorted(reminders, key=lambda item: (URGENCY_RANK.get(item["urgency"], 0), item["days_overdue"]), reverse=True)


async def check_reminders(user_id: str, db: aiosqlite.Connection) -> list[dict[str, Any]]:
    """Compatibility alias for reminder generation."""

    return await get_reminders(user_id, db)
