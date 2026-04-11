from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import aiosqlite

from backend.database import get_profile_dict

XP_AWARDS: dict[str, int] = {
    "meal_log": 10,
    "step_goal": 15,
    "sleep_goal": 15,
    "water_goal": 5,
    "checkin": 20,
    "selfie": 10,
    "data_upload": 25,
    "exercise_goal": 15,
}

LEVEL_THRESHOLDS: list[int] = [0, 100, 300, 600, 1000, 1500, 2500, 4000, 6000, 10000]
LEVEL_NAMES: list[str] = [
    "Health Rookie",
    "Data Conscious",
    "Pattern Seeker",
    "Bio Optimizer",
    "Longevity Learner",
    "Wellness Warrior",
    "Health Architect",
    "Age Defier",
    "Vitality Master",
    "EirView Legend",
]

ACHIEVEMENT_DEFS: dict[str, str] = {
    "first_blood": "Upload first blood report",
    "face_future": "First FaceAge selfie",
    "stand_tall": "Posture score >80%",
    "time_traveler": "Use Future Self chat",
    "know_thyself": "Complete PHQ-9 assessment",
    "age_bender": "Bio age improves by >1 year from first calculation",
    "data_complete": "90%+ of profile fields filled",
    "multi_source": "Ingest from 5+ different source types",
    "week_warrior": "7-day streak",
    "month_master": "30-day streak",
}


def get_level(xp: int) -> tuple[int, str]:
    """Return (level_number, level_name) for a given XP total."""

    index = 0
    for idx, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            index = idx
    return index + 1, LEVEL_NAMES[index]


async def log_action(user_id: str, action: str, db: aiosqlite.Connection) -> dict[str, Any]:
    """Log a daily action, award XP, update streak, check achievements."""

    today = date.today()
    today_str = str(today)
    xp = XP_AWARDS.get(action, 5)
    duplicate = await (
        await db.execute("SELECT 1 FROM daily_actions WHERE user_id=? AND date=? AND action=?", (user_id, today_str, action))
    ).fetchone()
    if duplicate:
        return await get_gamification(user_id, db)
    await db.execute(
        "INSERT INTO daily_actions (user_id, date, action, xp_earned) VALUES (?,?,?,?)",
        (user_id, today_str, action, xp),
    )
    streak_row = await (
        await db.execute("SELECT * FROM streaks WHERE user_id=?", (user_id,))
    ).fetchone()
    current_streak = int(streak_row["current_streak"]) if streak_row else 0
    longest_streak = int(streak_row["longest_streak"]) if streak_row else 0
    total_xp = int(streak_row["total_xp"]) if streak_row else 0
    last_streak_date = streak_row["last_streak_date"] if streak_row else None
    total_xp += xp
    yesterday = str(today - timedelta(days=1))
    if last_streak_date == yesterday:
        current_streak += 1
    elif last_streak_date != today_str:
        current_streak = 1
    longest_streak = max(longest_streak, current_streak)
    last_streak_date = today_str
    level, _ = get_level(total_xp)
    await db.execute(
        "INSERT OR REPLACE INTO streaks (user_id, current_streak, longest_streak, last_streak_date, total_xp, level) VALUES (?,?,?,?,?,?)",
        (user_id, current_streak, longest_streak, last_streak_date, total_xp, level),
    )
    await check_achievements(user_id, db)
    await db.commit()
    return await get_gamification(user_id, db)


async def get_gamification(user_id: str, db: aiosqlite.Connection) -> dict[str, Any]:
    """Return full gamification state."""

    streak = await (await db.execute("SELECT * FROM streaks WHERE user_id=?", (user_id,))).fetchone()
    total_xp = int(streak["total_xp"]) if streak else 0
    level, level_name = get_level(total_xp)
    next_threshold = next((threshold for threshold in LEVEL_THRESHOLDS if threshold > total_xp), LEVEL_THRESHOLDS[-1])
    today_actions_rows = await (
        await db.execute("SELECT action FROM daily_actions WHERE user_id=? AND date=?", (user_id, str(date.today())))
    ).fetchall()
    achievements_rows = await (
        await db.execute("SELECT badge_id, earned_at FROM achievements WHERE user_id=? ORDER BY earned_at DESC", (user_id,))
    ).fetchall()
    week_start = str(date.today() - timedelta(days=date.today().weekday()))
    challenge = await (
        await db.execute("SELECT * FROM weekly_challenges WHERE user_id=? AND week_start=? ORDER BY id DESC LIMIT 1", (user_id, week_start))
    ).fetchone()
    achievements = [
        {"badge_id": row["badge_id"], "description": ACHIEVEMENT_DEFS.get(row["badge_id"], row["badge_id"]), "earned_at": row["earned_at"]}
        for row in achievements_rows
    ]
    return {
        "current_streak": int(streak["current_streak"]) if streak else 0,
        "longest_streak": int(streak["longest_streak"]) if streak else 0,
        "total_xp": total_xp,
        "level": level,
        "level_name": level_name,
        "xp_to_next_level": max(next_threshold - total_xp, 0),
        "today_actions": [row["action"] for row in today_actions_rows],
        "achievements": achievements,
        "active_challenge": dict(challenge) if challenge else {"challenge_id": "move_5_days", "progress": 3, "target": 5, "completed": False},
    }


async def get_gamification_summary(user_id: str, db: aiosqlite.Connection) -> dict[str, Any]:
    """Compatibility wrapper returning the same gamification state."""

    return await get_gamification(user_id, db)


async def process_action(user_id: str, action: str, metadata: dict[str, Any] | None, db: aiosqlite.Connection) -> dict[str, Any]:
    """Compatibility wrapper used by the API layer."""

    _ = metadata
    return await log_action(user_id, action, db)


async def get_leaderboard(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    """Return all users ranked by XP descending."""

    rows = await (
        await db.execute(
            """
            SELECT u.id AS user_id, u.name, COALESCE(s.total_xp, 0) AS total_xp, COALESCE(s.level, 1) AS level,
                   COALESCE(s.current_streak, 0) AS current_streak, p.bio_age_overall, u.age
            FROM users u
            LEFT JOIN streaks s ON s.user_id = u.id
            LEFT JOIN profiles p ON p.user_id = u.id
            ORDER BY total_xp DESC, current_streak DESC, u.name ASC
            """
        )
    ).fetchall()
    leaderboard: list[dict[str, Any]] = []
    for row in rows:
        _, level_name = get_level(int(row["total_xp"]))
        delta = None
        if row["bio_age_overall"] is not None and row["age"] is not None:
            delta = round(float(row["bio_age_overall"]) - float(row["age"]), 1)
        leaderboard.append(
            {
                "user_id": row["user_id"],
                "name": row["name"],
                "total_xp": int(row["total_xp"]),
                "level": int(row["level"]),
                "level_name": level_name,
                "current_streak": int(row["current_streak"]),
                "bio_age_delta": delta,
            }
        )
    return leaderboard


async def check_achievements(user_id: str, db: aiosqlite.Connection) -> list[str]:
    """Check all achievement conditions for the user and award new ones."""

    profile = await get_profile_dict(user_id, db)
    streak = await (await db.execute("SELECT * FROM streaks WHERE user_id=?", (user_id,))).fetchone()
    earned_rows = await (await db.execute("SELECT badge_id FROM achievements WHERE user_id=?", (user_id,))).fetchall()
    earned = {row["badge_id"] for row in earned_rows}
    newly_earned: list[str] = []

    def award(badge_id: str, condition: bool) -> None:
        if condition and badge_id not in earned and badge_id not in newly_earned:
            newly_earned.append(badge_id)

    blood_fields = ["ldl", "hdl", "triglycerides", "total_cholesterol", "vitamin_d", "b12", "tsh", "ferritin"]
    award("first_blood", bool(profile and any(profile.get(field) is not None for field in blood_fields)))
    award("face_future", bool(profile and profile.get("face_age") is not None))
    award("stand_tall", bool(profile and (profile.get("posture_score_pct") or 0) > 80))
    future_log = await (
        await db.execute("SELECT 1 FROM agent_logs WHERE user_id=? AND action LIKE '%future_self%' LIMIT 1", (user_id,))
    ).fetchone()
    award("time_traveler", future_log is not None)
    award("know_thyself", bool(profile and profile.get("phq9_score") is not None))
    award(
        "age_bender",
        bool(
            profile
            and profile.get("bio_age_overall") is not None
            and profile.get("age") is not None
            and float(profile["bio_age_overall"]) <= float(profile["age"]) - 1
        ),
    )
    if profile:
        filled = sum(1 for key in profile.keys() if key != "user_id" and profile[key] is not None)
        award("data_complete", filled / max(len(profile.keys()) - 1, 1) > 0.9)
    source_count = await (
        await db.execute("SELECT COUNT(DISTINCT source) AS count FROM data_sources WHERE user_id=? AND last_synced_at IS NOT NULL", (user_id,))
    ).fetchone()
    award("multi_source", bool(source_count and source_count["count"] >= 5))
    award("week_warrior", bool(streak and streak["current_streak"] >= 7))
    award("month_master", bool(streak and streak["current_streak"] >= 30))
    for badge_id in newly_earned:
        await db.execute("INSERT OR IGNORE INTO achievements (user_id, badge_id) VALUES (?,?)", (user_id, badge_id))
    return newly_earned
