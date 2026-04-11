from __future__ import annotations

import json
from typing import Any

from backend.database import get_profile_dict
from backend.spotify import classify_music_emotion


async def get_spotify_mood(user_id: str, db: Any, **kwargs: Any) -> dict:
    """Get the latest Spotify mood entry for a user."""

    _ = kwargs
    cursor = await db.execute("SELECT * FROM spotify_history WHERE user_id=? ORDER BY timestamp DESC LIMIT 1", (user_id,))
    row = await cursor.fetchone()
    if row is None:
        return {"available": False, "message": "No Spotify data synced"}
    row_dict = dict(row)
    baseline = row_dict.get("baseline_valence")
    avg_valence = row_dict.get("avg_valence", 0)
    return {
        "available": True,
        "avg_valence": avg_valence,
        "avg_energy": row_dict.get("avg_energy"),
        "avg_danceability": row_dict.get("avg_danceability"),
        "emotion_class": classify_music_emotion(avg_valence or 0, row_dict.get("avg_energy") or 0, row_dict.get("avg_danceability") or 0.5),
        "baseline_valence": baseline,
        "flagged": bool(row_dict.get("flagged")),
        "flag_reason": json.loads(row_dict["flag_reason"]) if row_dict.get("flag_reason") else None,
        "valence_shift": round(avg_valence - baseline, 3) if baseline is not None else None,
    }


async def get_cross_signals(user_id: str, db: Any, **kwargs: Any) -> dict:
    """Get cross-domain signals that can confirm a mood change."""

    _ = kwargs
    profile = await get_profile_dict(user_id, db) or {}
    signals: dict[str, Any] = {
        "sleep_declining": (profile.get("sleep_hours") or 7) < 6,
        "steps_declining": (profile.get("steps_avg_7d") or 7500) < 5000,
        "hrv_low": (profile.get("hrv_ms") or 40) < 30,
        "stress_high": (profile.get("stress_level") or 5) > 6,
        "screen_high": (profile.get("screen_time_hours") or 6) > 10,
        "vitd_deficient": (profile.get("vitamin_d") or 30) < 20,
        "academic_burnout": (profile.get("exam_stress") or 0) > 7 and (profile.get("study_hours_daily") or 0) > 8 and (profile.get("sleep_hours") or 7) < 6,
        "academic_stress_high": (profile.get("exam_stress") or 0) > 7,
    }
    signals["num_confirming"] = sum(1 for value in signals.values() if value is True)
    return signals
