from __future__ import annotations

import random
import string
import uuid
from typing import Any

import aiosqlite


async def create_family(name: str, creator_user_id: str, db: aiosqlite.Connection) -> dict[str, Any]:
    """Create a family group."""

    family_id = uuid.uuid4().hex[:8]
    alphabet = string.ascii_uppercase + string.digits
    join_code = ""
    while not join_code:
        candidate = "".join(random.choice(alphabet) for _ in range(6))
        exists = await (await db.execute("SELECT 1 FROM families WHERE join_code=?", (candidate,))).fetchone()
        if not exists:
            join_code = candidate
    await db.execute("INSERT INTO families (id, name, join_code, created_by) VALUES (?,?,?,?)", (family_id, name, join_code, creator_user_id))
    await db.execute(
        "INSERT INTO family_members (family_id, user_id, relationship, role, privacy_level) VALUES (?,?,?,?,?)",
        (family_id, creator_user_id, "self", "admin", "full"),
    )
    await db.execute("UPDATE users SET family_id=? WHERE id=?", (family_id, creator_user_id))
    await db.commit()
    return {"id": family_id, "name": name, "join_code": join_code, "created_by": creator_user_id}


async def join_family(join_code: str, user_id: str, relationship: str, privacy_level: str, db: aiosqlite.Connection) -> dict[str, Any]:
    """Join an existing family group."""

    family = await (await db.execute("SELECT * FROM families WHERE join_code=?", (join_code,))).fetchone()
    if not family:
        raise ValueError("Invalid join code")
    await db.execute(
        "INSERT OR REPLACE INTO family_members (family_id, user_id, relationship, role, privacy_level) VALUES (?,?,?,?,?)",
        (family["id"], user_id, relationship, "member", privacy_level),
    )
    await db.execute("UPDATE users SET family_id=? WHERE id=?", (family["id"], user_id))
    await update_family_flags(str(family["id"]), db)
    await db.commit()
    return {"id": family["id"], "name": family["name"], "join_code": family["join_code"], "created_by": family["created_by"]}


async def get_family_dashboard(family_id: str, db: aiosqlite.Connection) -> dict[str, Any]:
    """Get family dashboard with member info respecting privacy levels."""

    family = await (await db.execute("SELECT * FROM families WHERE id=?", (family_id,))).fetchone()
    members_rows = await (
        await db.execute(
            """
            SELECT fm.*, u.name, p.bio_age_overall, p.mental_wellness_score, p.phq9_score, p.stress_level, s.current_streak
            FROM family_members fm
            JOIN users u ON u.id = fm.user_id
            LEFT JOIN profiles p ON p.user_id = fm.user_id
            LEFT JOIN streaks s ON s.user_id = fm.user_id
            WHERE fm.family_id=?
            ORDER BY fm.role DESC, fm.joined_at ASC
            """,
            (family_id,),
        )
    ).fetchall()
    members: list[dict[str, Any]] = []
    for row in members_rows:
        item = {
            "user_id": row["user_id"],
            "name": row["name"],
            "relationship": row["relationship"],
            "role": row["role"],
            "privacy_level": row["privacy_level"],
            "current_streak": row["current_streak"] or 0,
        }
        privacy = row["privacy_level"]
        if privacy in {"full", "summary"}:
            item["bio_age_overall"] = row["bio_age_overall"]
            item["mental_wellness_score"] = row["mental_wellness_score"]
        if privacy == "full":
            item["phq9_score"] = row["phq9_score"]
            item["stress_level"] = row["stress_level"]
        members.append(item)
    flags_rows = await (
        await db.execute("SELECT condition, evidence, severity, detected_at FROM family_health_flags WHERE family_id=? ORDER BY detected_at DESC", (family_id,))
    ).fetchall()
    return {
        "family": {"id": family["id"], "name": family["name"], "join_code": family["join_code"]} if family else None,
        "members": members,
        "health_flags": [dict(row) for row in flags_rows],
    }


async def update_family_flags(family_id: str, db: aiosqlite.Connection) -> None:
    """Scan family member profiles and derive family health conditions."""

    members = await (
        await db.execute(
            """
            SELECT fm.user_id, p.*
            FROM family_members fm
            LEFT JOIN profiles p ON p.user_id = fm.user_id
            WHERE fm.family_id=?
            """,
            (family_id,),
        )
    ).fetchall()
    await db.execute("DELETE FROM family_health_flags WHERE family_id=?", (family_id,))
    conditions_map = {
        "diabetes": [("fasting_glucose", 100, ">"), ("hba1c", 5.7, ">")],
        "heart_disease": [("ldl", 160, ">"), ("total_cholesterol", 240, ">")],
        "hypertension": [("blood_pressure_systolic", 130, ">"), ("blood_pressure_diastolic", 85, ">")],
        "mental_health": [("phq9_score", 10, ">")],
        "thyroid": [("tsh", 4.5, ">"), ("tsh", 0.4, "<")],
    }
    family_boolean_map = {
        "diabetes": "family_diabetes",
        "heart_disease": "family_heart",
        "hypertension": "family_hypertension",
        "mental_health": "family_mental",
    }
    for member in members:
        for condition, checks in conditions_map.items():
            for metric, threshold, op in checks:
                value = member[metric]
                if value is None:
                    continue
                triggered = value > threshold if op == ">" else value < threshold
                if not triggered:
                    continue
                distance = abs(value - threshold) / threshold if threshold else 0
                severity = "borderline" if distance <= 0.1 else "moderate" if distance <= 0.3 else "severe"
                evidence = f"{metric}={value} threshold {op} {threshold}"
                await db.execute(
                    "INSERT OR REPLACE INTO family_health_flags (family_id, condition, source_user_id, evidence, severity) VALUES (?,?,?,?,?)",
                    (family_id, condition, member["user_id"], evidence, severity),
                )
                boolean_field = family_boolean_map.get(condition)
                if boolean_field:
                    await db.execute(
                        f"UPDATE profiles SET {boolean_field}=1 WHERE user_id IN (SELECT user_id FROM family_members WHERE family_id=? AND user_id!=?)",
                        (family_id, member["user_id"]),
                    )
                break
