from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from typing import Any

import aiosqlite

from backend.formulas import calculate_bio_age, mental_wellness_score
from backend.health_state import HealthProfile

DB_PATH = os.environ.get("EIRVIEW_DB_PATH", "eirview.db")

PROFILE_COLUMNS: list[str] = [
    "ldl", "hdl", "triglycerides", "total_cholesterol", "vitamin_d", "b12", "tsh", "ferritin",
    "fasting_glucose", "hba1c", "hemoglobin", "creatinine", "sgpt_alt", "sgot_ast", "weight_kg",
    "bmi", "bmr", "body_fat_pct", "visceral_fat_kg", "muscle_mass_kg", "body_water_pct", "protein_kg",
    "bone_mass_kg", "body_age_device", "resting_hr", "hrv_ms", "steps_today", "steps_avg_7d",
    "active_energy_kcal", "exercise_min", "sleep_hours", "sleep_deep_pct", "sleep_rem_pct", "vo2max",
    "respiratory_rate", "walking_asymmetry_pct", "flights_climbed", "blood_oxygen_pct",
    "blood_pressure_systolic", "blood_pressure_diastolic", "face_age", "posture_score_pct",
    "temperature_c", "humidity_pct", "aqi", "uv_index", "phq9_score", "phq9_last_calibrated_at", "stress_level",
    "screen_time_hours", "academic_gpa", "study_hours_daily", "exam_stress", "academic_year",
    "family_diabetes", "family_heart", "family_hypertension", "family_mental", "exercise_hours_week",
    "sleep_target", "smoking", "diet_quality", "last_blood_report_date", "last_vitd_test_date",
    "last_glucose_test_date", "last_general_checkup_date", "doctor_name", "doctor_email", "doctor_phone",
    "emergency_contact_name", "emergency_contact_phone", "location_label", "latitude", "longitude", "bio_age_overall", "bio_age_cardiovascular",
    "bio_age_metabolic", "bio_age_musculoskeletal", "bio_age_neurological", "mental_wellness_score",
]


async def get_db() -> aiosqlite.Connection:
    """Get a database connection with row_factory set to aiosqlite.Row."""

    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def _ensure_column(db: aiosqlite.Connection, table: str, column: str, definition: str) -> None:
    """Add a column to an existing SQLite table when missing."""

    rows = await (await db.execute(f"PRAGMA table_info({table})")).fetchall()
    existing = {row["name"] for row in rows}
    if column not in existing:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


async def init_db() -> None:
    """Create database schema and seed demo data."""

    db = await get_db()
    try:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER,
                sex TEXT,
                height_cm REAL,
                family_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY REFERENCES users(id),
                ldl REAL, hdl REAL, triglycerides REAL, total_cholesterol REAL,
                vitamin_d REAL, b12 REAL, tsh REAL, ferritin REAL,
                fasting_glucose REAL, hba1c REAL, hemoglobin REAL,
                creatinine REAL, sgpt_alt REAL, sgot_ast REAL,
                weight_kg REAL, bmi REAL, bmr REAL,
                body_fat_pct REAL, visceral_fat_kg REAL,
                muscle_mass_kg REAL, body_water_pct REAL,
                protein_kg REAL, bone_mass_kg REAL, body_age_device INTEGER,
                resting_hr REAL, hrv_ms REAL,
                steps_today INTEGER, steps_avg_7d INTEGER,
                active_energy_kcal REAL, exercise_min INTEGER,
                sleep_hours REAL, sleep_deep_pct REAL, sleep_rem_pct REAL,
                vo2max REAL, respiratory_rate REAL,
                walking_asymmetry_pct REAL, flights_climbed INTEGER,
                blood_oxygen_pct REAL,
                blood_pressure_systolic REAL, blood_pressure_diastolic REAL,
                face_age REAL,
                posture_score_pct REAL,
                temperature_c REAL, humidity_pct REAL,
                aqi INTEGER, uv_index REAL,
                phq9_score INTEGER, phq9_last_calibrated_at TEXT, stress_level INTEGER,
                screen_time_hours REAL,
                academic_gpa REAL, study_hours_daily REAL,
                exam_stress INTEGER, academic_year TEXT,
                family_diabetes BOOLEAN DEFAULT 0, family_heart BOOLEAN DEFAULT 0,
                family_hypertension BOOLEAN DEFAULT 0, family_mental BOOLEAN DEFAULT 0,
                exercise_hours_week REAL, sleep_target REAL,
                smoking TEXT DEFAULT 'never',
                diet_quality TEXT DEFAULT 'average',
                last_blood_report_date DATE,
                last_vitd_test_date DATE,
                last_glucose_test_date DATE,
                last_general_checkup_date DATE,
                doctor_name TEXT, doctor_email TEXT, doctor_phone TEXT,
                emergency_contact_name TEXT, emergency_contact_phone TEXT,
                location_label TEXT, latitude REAL, longitude REAL,
                bio_age_overall REAL,
                bio_age_cardiovascular REAL, bio_age_metabolic REAL,
                bio_age_musculoskeletal REAL, bio_age_neurological REAL,
                mental_wellness_score REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT REFERENCES users(id),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                agent_name TEXT NOT NULL,
                action TEXT,
                tool_name TEXT,
                tool_input TEXT,
                tool_output TEXT,
                prompt TEXT,
                response TEXT,
                tokens_in INTEGER,
                tokens_out INTEGER,
                latency_ms INTEGER,
                model TEXT DEFAULT 'claude-sonnet-4-6'
            );
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                reflection TEXT NOT NULL,
                query_summary TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                is_active INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT REFERENCES users(id),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                photo_path TEXT,
                calories REAL, protein_g REAL, carbs_g REAL, fat_g REAL,
                saturated_fat_g REAL, fiber_g REAL,
                vitamin_d_ug REAL, b12_ug REAL,
                health_score REAL,
                ai_notes TEXT
            );
            CREATE TABLE IF NOT EXISTS water_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT REFERENCES users(id),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                amount_ml INTEGER
            );
            CREATE TABLE IF NOT EXISTS posture_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT REFERENCES users(id),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                score_pct REAL,
                avg_angle REAL,
                is_slouching BOOLEAN
            );
            CREATE TABLE IF NOT EXISTS risk_projections (
                user_id TEXT REFERENCES users(id),
                year INTEGER,
                diabetes_risk REAL,
                cvd_risk REAL,
                metabolic_risk REAL,
                mental_decline_risk REAL,
                PRIMARY KEY (user_id, year)
            );
            CREATE TABLE IF NOT EXISTS spotify_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT REFERENCES users(id),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                avg_valence REAL,
                avg_energy REAL,
                avg_danceability REAL,
                track_count INTEGER,
                baseline_valence REAL,
                flagged BOOLEAN DEFAULT 0,
                flag_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS spotify_track_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT REFERENCES users(id),
                played_at TEXT,
                track_id TEXT,
                track_name TEXT,
                artist_names TEXT,
                album_name TEXT,
                album_image_url TEXT,
                preview_url TEXT,
                spotify_url TEXT,
                sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, played_at, track_id)
            );
            CREATE TABLE IF NOT EXISTS streaks (
                user_id TEXT PRIMARY KEY REFERENCES users(id),
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_streak_date DATE,
                total_xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS daily_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT REFERENCES users(id),
                date DATE NOT NULL,
                action TEXT NOT NULL,
                xp_earned INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, date, action)
            );
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT REFERENCES users(id),
                badge_id TEXT NOT NULL,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, badge_id)
            );
            CREATE TABLE IF NOT EXISTS weekly_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT REFERENCES users(id),
                week_start DATE NOT NULL,
                challenge_id TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                target INTEGER NOT NULL,
                completed BOOLEAN DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS families (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                join_code TEXT UNIQUE NOT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS family_members (
                family_id TEXT REFERENCES families(id),
                user_id TEXT REFERENCES users(id),
                relationship TEXT NOT NULL,
                role TEXT DEFAULT 'member',
                privacy_level TEXT DEFAULT 'summary',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (family_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS family_health_flags (
                family_id TEXT REFERENCES families(id),
                condition TEXT NOT NULL,
                source_user_id TEXT,
                evidence TEXT,
                severity TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (family_id, condition, source_user_id)
            );
            CREATE TABLE IF NOT EXISTS usda_foods (
                fdc_id INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                calories_per_100g REAL,
                protein_per_100g REAL,
                fat_per_100g REAL,
                carbs_per_100g REAL,
                sat_fat_per_100g REAL,
                fiber_per_100g REAL,
                vitamin_d_ug_per_100g REAL,
                b12_ug_per_100g REAL,
                iron_mg_per_100g REAL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS specialist_referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT REFERENCES users(id),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                specialist_type TEXT NOT NULL,
                trigger_metric TEXT NOT NULL,
                trigger_value REAL,
                trigger_threshold REAL,
                reason TEXT,
                recommended_hospitals TEXT,
                acknowledged BOOLEAN DEFAULT 0,
                appointment_scheduled BOOLEAN DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS data_sources (
                user_id TEXT REFERENCES users(id),
                source TEXT NOT NULL,
                last_synced_at TIMESTAMP,
                refresh_interval_days INTEGER,
                reminder_sent_at TIMESTAMP,
                PRIMARY KEY (user_id, source)
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT REFERENCES users(id),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                threshold REAL NOT NULL,
                severity TEXT NOT NULL,
                user_notified BOOLEAN DEFAULT 1,
                doctor_notified BOOLEAN DEFAULT 0,
                doctor_email_sent_at TIMESTAMP,
                user_approved_doctor_alert BOOLEAN
            );
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT REFERENCES users(id),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type TEXT NOT NULL,
                duration_min INTEGER,
                calories REAL,
                source TEXT DEFAULT 'manual',
                date DATE NOT NULL,
                cv_impact REAL,
                msk_impact REAL,
                met_impact REAL,
                neuro_impact REAL
            );
            CREATE TABLE IF NOT EXISTS spotify_tokens (
                user_id TEXT PRIMARY KEY REFERENCES users(id),
                access_token TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        await _ensure_column(db, "profiles", "location_label", "TEXT")
        await _ensure_column(db, "profiles", "latitude", "REAL")
        await _ensure_column(db, "profiles", "longitude", "REAL")
        await _ensure_column(db, "profiles", "phq9_last_calibrated_at", "TEXT")
        await _ensure_column(db, "agent_logs", "react_trace", "TEXT")
        await _ensure_column(db, "agent_logs", "difficulty", "TEXT")
        await db.execute("UPDATE data_sources SET refresh_interval_days=14 WHERE source='mental_checkin'")
        await db.commit()
        await seed_data()
    finally:
        await db.close()


def _row_to_dict(row: aiosqlite.Row | None) -> dict[str, Any] | None:
    """Convert a row to a plain dictionary."""

    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


async def _ensure_profile_exists(user_id: str, db: aiosqlite.Connection) -> None:
    """Ensure a profile row exists for the given user."""

    await db.execute("INSERT OR IGNORE INTO profiles (user_id) VALUES (?)", (user_id,))


async def create_user(user_id: str, name: str, age: int | None, sex: str | None, height_cm: float | None) -> dict[str, Any]:
    """Insert a new user. Return the created user dict."""

    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO users (id, name, age, sex, height_cm) VALUES (?,?,?,?,?)",
            (user_id, name, age, sex, height_cm),
        )
        await _ensure_profile_exists(user_id, db)
        await db.commit()
        return {"id": user_id, "name": name, "age": age, "sex": sex, "height_cm": height_cm}
    finally:
        await db.close()


async def get_user(user_id: str) -> dict[str, Any] | None:
    """Fetch a user by ID. Return None if not found."""

    db = await get_db()
    try:
        row = await (await db.execute("SELECT * FROM users WHERE id=?", (user_id,))).fetchone()
        return _row_to_dict(row)
    finally:
        await db.close()


async def get_all_users() -> list[dict[str, Any]]:
    """Fetch all users."""

    db = await get_db()
    try:
        rows = await (await db.execute("SELECT * FROM users ORDER BY created_at ASC")).fetchall()
        return [_row_to_dict(row) or {} for row in rows]
    finally:
        await db.close()


def _prepare_profile_payload(user_id: str, data: dict[str, Any], existing: dict[str, Any] | None) -> dict[str, Any]:
    """Merge new profile data with existing data and computed fields."""

    payload = dict(existing or {})
    payload.update(data)
    payload["user_id"] = user_id
    user_meta_age = payload.get("age", payload.get("chronological_age"))
    if user_meta_age is not None:
        payload["age"] = user_meta_age
    bio = calculate_bio_age(payload)
    wellness = mental_wellness_score(payload)
    payload.update(
        {
            "bio_age_overall": bio["overall"],
            "bio_age_cardiovascular": bio["cardiovascular"],
            "bio_age_metabolic": bio["metabolic"],
            "bio_age_musculoskeletal": bio["musculoskeletal"],
            "bio_age_neurological": bio["neurological"],
            "mental_wellness_score": wellness["score"],
        }
    )
    valid_model = HealthProfile(**{key: value for key, value in payload.items() if key in HealthProfile.model_fields})
    payload.update(valid_model.model_dump())
    return payload


async def upsert_profile(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Insert or update a health profile using merge semantics."""

    db = await get_db()
    try:
        existing = await get_profile_dict(user_id, db)
        payload = _prepare_profile_payload(user_id, data, existing)
        columns = ["user_id"] + PROFILE_COLUMNS
        values = [payload.get(column) for column in columns]
        placeholders = ",".join(["?"] * len(columns))
        assignments = ",".join(columns)
        await db.execute(
            f"INSERT OR REPLACE INTO profiles ({assignments}) VALUES ({placeholders})",
            values,
        )
        await db.commit()
        return await get_profile_dict(user_id, db) or {"user_id": user_id}
    finally:
        await db.close()


async def update_profile_fields(user_id: str, data: dict[str, Any], db: aiosqlite.Connection | None = None) -> dict[str, Any]:
    """Update specific profile fields while preserving existing fields."""

    own_connection = db is None
    conn = db or await get_db()
    try:
        await _ensure_profile_exists(user_id, conn)
        existing = await get_profile_dict(user_id, conn)
        normalized_data = dict(data)
        if "phq9_score" in normalized_data:
            if normalized_data.get("phq9_score") is None:
                normalized_data["phq9_last_calibrated_at"] = None
            elif "phq9_last_calibrated_at" not in normalized_data:
                normalized_data["phq9_last_calibrated_at"] = datetime.now().isoformat(sep=" ", timespec="seconds")
        payload = _prepare_profile_payload(user_id, normalized_data, existing)
        columns = ["user_id"] + PROFILE_COLUMNS
        values = [payload.get(column) for column in columns]
        placeholders = ",".join(["?"] * len(columns))
        await conn.execute(f"INSERT OR REPLACE INTO profiles ({','.join(columns)}) VALUES ({placeholders})", values)
        await conn.execute("UPDATE profiles SET updated_at=CURRENT_TIMESTAMP WHERE user_id=?", (user_id,))
        for source, value in normalized_data.items():
            if source in {"face_age", "posture_score_pct"}:
                await conn.execute(
                    "INSERT OR REPLACE INTO data_sources (user_id, source, last_synced_at, refresh_interval_days) VALUES (?,?,CURRENT_TIMESTAMP,COALESCE((SELECT refresh_interval_days FROM data_sources WHERE user_id=? AND source=?),30))",
                    (user_id, source.replace("_pct", ""), user_id, source.replace("_pct", "")),
                )
        if "phq9_score" in normalized_data:
            if normalized_data.get("phq9_score") is None:
                await conn.execute("DELETE FROM data_sources WHERE user_id=? AND source='mental_checkin'", (user_id,))
            else:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO data_sources (user_id, source, last_synced_at, refresh_interval_days)
                    VALUES (?,?,CURRENT_TIMESTAMP,14)
                    """,
                    (user_id, "mental_checkin"),
                )
        await conn.commit()
        return await get_profile_dict(user_id, conn) or {}
    finally:
        if own_connection:
            await conn.close()


async def get_profile(user_id: str) -> dict[str, Any] | None:
    """Fetch a user's health profile as a dict with user metadata."""

    db = await get_db()
    try:
        return await get_profile_dict(user_id, db)
    finally:
        await db.close()


async def get_profile_dict(user_id: str, db: aiosqlite.Connection) -> dict[str, Any] | None:
    """Fetch a user's health profile and include user fields."""

    cursor = await db.execute(
        """
        SELECT p.*, u.id, u.name, u.age, u.sex, u.height_cm, u.family_id
        FROM users u
        LEFT JOIN profiles p ON p.user_id = u.id
        WHERE u.id = ?
        """,
        (user_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    result = _row_to_dict(row) or {}
    result["id"] = result.get("id", user_id)
    result["user_id"] = user_id
    result["age"] = result.get("age")
    return result


async def log_meal(user_id: str, meal: dict[str, Any], db: aiosqlite.Connection | None = None) -> dict[str, Any]:
    """Insert a meal entry. Return the created meal with its ID."""

    own_connection = db is None
    conn = db or await get_db()
    try:
        total = meal.get("total", meal)
        cursor = await conn.execute(
            """
            INSERT INTO meals (
                user_id, description, photo_path, calories, protein_g, carbs_g, fat_g,
                saturated_fat_g, fiber_g, vitamin_d_ug, b12_ug, health_score, ai_notes
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                user_id,
                meal.get("description"),
                meal.get("photo_path"),
                total.get("calories"),
                total.get("protein_g"),
                total.get("carbs_g"),
                total.get("fat_g"),
                total.get("sat_fat_g", total.get("saturated_fat_g")),
                total.get("fiber_g"),
                total.get("vitamin_d_ug"),
                total.get("b12_ug"),
                meal.get("health_score", meal.get("score")),
                json.dumps(meal.get("flags") or meal.get("items") or meal.get("ai_notes")),
            ),
        )
        await conn.execute(
            "INSERT OR REPLACE INTO data_sources (user_id, source, last_synced_at, refresh_interval_days) VALUES (?,?,CURRENT_TIMESTAMP,1)",
            (user_id, "meal"),
        )
        await conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, **meal}
    finally:
        if own_connection:
            await conn.close()


async def get_meals(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch recent meals for a user, ordered by timestamp DESC."""

    db = await get_db()
    try:
        rows = await (
            await db.execute("SELECT * FROM meals WHERE user_id=? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
        ).fetchall()
        return [_row_to_dict(row) or {} for row in rows]
    finally:
        await db.close()


async def get_meals_for_day(user_id: str, day: str, db: aiosqlite.Connection | None = None) -> list[dict[str, Any]]:
    """Fetch all meals for a specific local calendar day."""

    own_connection = db is None
    conn = db or await get_db()
    try:
        rows = await (
            await conn.execute(
                """
                SELECT * FROM meals
                WHERE user_id=? AND DATE(timestamp, 'localtime')=DATE(?)
                ORDER BY timestamp DESC
                """,
                (user_id, day),
            )
        ).fetchall()
        return [_row_to_dict(row) or {} for row in rows]
    finally:
        if own_connection:
            await conn.close()


async def get_recent_meals_db(user_id: str, days: int, db: aiosqlite.Connection) -> list[dict[str, Any]]:
    """Fetch meal rows from the last N days and normalize them for tool consumption."""

    since = datetime.now() - timedelta(days=days)
    rows = await (
        await db.execute("SELECT * FROM meals WHERE user_id=? AND timestamp>=? ORDER BY timestamp DESC", (user_id, since.isoformat(sep=" ")))
    ).fetchall()
    meals: list[dict[str, Any]] = []
    for row in rows:
        item = _row_to_dict(row) or {}
        meals.append(
            {
                "id": item.get("id"),
                "date": str(item.get("timestamp", ""))[:10],
                "description": item.get("description"),
                "nutrition": {
                    "calories": item.get("calories") or 0,
                    "protein_g": item.get("protein_g") or 0,
                    "carbs_g": item.get("carbs_g") or 0,
                    "fat_g": item.get("fat_g") or 0,
                    "sat_fat_g": item.get("saturated_fat_g") or 0,
                    "fiber_g": item.get("fiber_g") or 0,
                },
                "score": item.get("health_score"),
                "notes": item.get("ai_notes"),
            }
        )
    return meals


async def log_water(user_id: str, amount_ml: int) -> dict[str, Any]:
    """Insert a water log entry."""

    db = await get_db()
    try:
        cursor = await db.execute("INSERT INTO water_log (user_id, amount_ml) VALUES (?,?)", (user_id, amount_ml))
        await db.execute(
            "INSERT OR REPLACE INTO data_sources (user_id, source, last_synced_at, refresh_interval_days) VALUES (?,?,CURRENT_TIMESTAMP,1)",
            (user_id, "water"),
        )
        await db.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "amount_ml": amount_ml}
    finally:
        await db.close()


async def get_water_today(user_id: str, db: aiosqlite.Connection | None = None) -> int:
    """Sum of water intake today in ml."""

    own_connection = db is None
    conn = db or await get_db()
    try:
        row = await (
            await conn.execute(
                "SELECT COALESCE(SUM(amount_ml),0) AS total FROM water_log WHERE user_id=? AND DATE(timestamp, 'localtime')=DATE('now', 'localtime')",
                (user_id,),
            )
        ).fetchone()
        return int((row["total"] if row else 0) or 0)
    finally:
        if own_connection:
            await conn.close()


async def get_water_for_day(user_id: str, day: str, db: aiosqlite.Connection | None = None) -> int:
    """Sum of water intake for a specific local calendar day in ml."""

    own_connection = db is None
    conn = db or await get_db()
    try:
        row = await (
            await conn.execute(
                "SELECT COALESCE(SUM(amount_ml),0) AS total FROM water_log WHERE user_id=? AND DATE(timestamp, 'localtime')=DATE(?)",
                (user_id, day),
            )
        ).fetchone()
        return int((row["total"] if row else 0) or 0)
    finally:
        if own_connection:
            await conn.close()


async def log_posture(user_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    """Insert a posture reading."""

    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO posture_history (user_id, score_pct, avg_angle, is_slouching) VALUES (?,?,?,?)",
            (user_id, entry.get("score_pct"), entry.get("avg_angle"), entry.get("is_slouching", False)),
        )
        await update_profile_fields(user_id, {"posture_score_pct": entry.get("score_pct")}, db)
        await db.execute(
            "INSERT OR REPLACE INTO data_sources (user_id, source, last_synced_at, refresh_interval_days) VALUES (?,?,CURRENT_TIMESTAMP,7)",
            (user_id, "posture"),
        )
        await db.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, **entry}
    finally:
        await db.close()


async def get_posture_history(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Fetch recent posture readings."""

    db = await get_db()
    try:
        rows = await (
            await db.execute("SELECT * FROM posture_history WHERE user_id=? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
        ).fetchall()
        return [_row_to_dict(row) or {} for row in rows]
    finally:
        await db.close()


async def save_risk_projections(user_id: str, projections: list[dict[str, Any]]) -> None:
    """Save risk projection rows (replace existing for user)."""

    db = await get_db()
    try:
        await db.execute("DELETE FROM risk_projections WHERE user_id=?", (user_id,))
        for projection in projections:
            await db.execute(
                "INSERT INTO risk_projections (user_id, year, diabetes_risk, cvd_risk, metabolic_risk, mental_decline_risk) VALUES (?,?,?,?,?,?)",
                (
                    user_id,
                    projection.get("year"),
                    projection.get("diabetes_risk"),
                    projection.get("cvd_risk"),
                    projection.get("metabolic_risk"),
                    projection.get("mental_decline_risk"),
                ),
            )
        await db.commit()
    finally:
        await db.close()


async def get_risk_projections(user_id: str) -> list[dict[str, Any]]:
    """Fetch risk projections for a user."""

    db = await get_db()
    try:
        rows = await (
            await db.execute("SELECT * FROM risk_projections WHERE user_id=? ORDER BY year ASC", (user_id,))
        ).fetchall()
        return [_row_to_dict(row) or {} for row in rows]
    finally:
        await db.close()


async def log_agent_action(user_id: str, agent_name: str, action: str, **kwargs: Any) -> None:
    """Insert an agent log entry."""

    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO agent_logs
            (user_id, agent_name, action, tool_name, tool_input, tool_output, prompt, response, tokens_in, tokens_out, latency_ms, model, react_trace, difficulty)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                user_id,
                agent_name,
                action,
                kwargs.get("tool_name"),
                json.dumps(kwargs.get("tool_input")) if kwargs.get("tool_input") is not None else None,
                json.dumps(kwargs.get("tool_output")) if kwargs.get("tool_output") is not None else None,
                kwargs.get("prompt"),
                kwargs.get("response"),
                kwargs.get("tokens_in"),
                kwargs.get("tokens_out"),
                kwargs.get("latency_ms"),
                kwargs.get("model", "claude-sonnet-4-6"),
                json.dumps(kwargs.get("react_trace")) if kwargs.get("react_trace") is not None else None,
                kwargs.get("difficulty"),
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def log_spotify(user_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    """Insert a Spotify analysis entry."""

    db = await get_db()
    try:
        cursor = await db.execute(
            """
            INSERT INTO spotify_history (user_id, avg_valence, avg_energy, avg_danceability, track_count, baseline_valence, flagged, flag_reason)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                user_id,
                entry.get("avg_valence"),
                entry.get("avg_energy"),
                entry.get("avg_danceability"),
                entry.get("track_count"),
                entry.get("baseline_valence"),
                bool(entry.get("flagged", False)),
                json.dumps(entry.get("flag_reason")) if isinstance(entry.get("flag_reason"), (dict, list)) else entry.get("flag_reason"),
            ),
        )
        await db.execute(
            "INSERT OR REPLACE INTO data_sources (user_id, source, last_synced_at, refresh_interval_days) VALUES (?,?,CURRENT_TIMESTAMP,3)",
            (user_id, "spotify"),
        )
        await db.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, **entry}
    finally:
        await db.close()


async def seed_data() -> None:
    """Insert seed data for 3 users if they don't already exist."""

    db = await get_db()
    try:
        existing = await (await db.execute("SELECT COUNT(*) AS count FROM users")).fetchone()
        if existing and existing["count"] >= 3:
            return
        today = date.today()
        users = [
            {"id": "zahoor", "name": "Zahoor Mashahir", "age": 19, "sex": "male", "height_cm": 178.0},
            {"id": "riya", "name": "Riya Sharma", "age": 22, "sex": "female", "height_cm": 162.0},
            {"id": "arjun", "name": "Arjun Patel", "age": 24, "sex": "male", "height_cm": 180.0},
        ]
        profiles = {
            "zahoor": {
                "ldl": 121, "hdl": 48, "total_cholesterol": 198, "vitamin_d": 15, "b12": 310, "tsh": 2.8, "hemoglobin": 14.2,
                "fasting_glucose": 85, "hba1c": 5.1, "creatinine": 0.9, "sgpt_alt": 28, "sgot_ast": 22, "ferritin": 65,
                "weight_kg": 66.9, "bmi": 21.1, "bmr": 1575, "body_fat_pct": 18.5, "visceral_fat_kg": 1.2, "muscle_mass_kg": 29.1,
                "body_water_pct": 58.2, "protein_kg": 10.1, "bone_mass_kg": 2.8, "body_age_device": 15, "resting_hr": 67, "hrv_ms": 42,
                "steps_today": 8234, "steps_avg_7d": 7500, "active_energy_kcal": 420, "exercise_min": 35, "sleep_hours": 6.5,
                "sleep_deep_pct": 15, "sleep_rem_pct": 20, "vo2max": 42.5, "respiratory_rate": 15.2, "walking_asymmetry_pct": 3.2,
                "flights_climbed": 4, "blood_oxygen_pct": 97, "face_age": 21.3, "posture_score_pct": 72, "phq9_score": 6, "stress_level": 5,
                "screen_time_hours": 8, "academic_gpa": 3.5, "study_hours_daily": 5, "exam_stress": 6, "academic_year": "Year 2",
                "exercise_hours_week": 4, "sleep_target": 8, "smoking": "never", "diet_quality": "average", "family_diabetes": 0,
                "family_heart": 0, "family_hypertension": 0, "last_blood_report_date": str(today - timedelta(days=100)),
                "last_vitd_test_date": str(today - timedelta(days=100)), "last_glucose_test_date": str(today - timedelta(days=120)),
                "last_general_checkup_date": str(today - timedelta(days=390)),
            },
            "riya": {
                "ldl": 95, "hdl": 55, "vitamin_d": 12, "b12": 245, "fasting_glucose": 108, "hba1c": 5.8, "hemoglobin": 11.5, "tsh": 4.8,
                "weight_kg": 58, "bmi": 22.1, "body_fat_pct": 28, "muscle_mass_kg": 20.5, "body_age_device": 25, "resting_hr": 78, "hrv_ms": 28,
                "steps_today": 3200, "steps_avg_7d": 4100, "exercise_min": 8, "sleep_hours": 5.5, "sleep_deep_pct": 10, "sleep_rem_pct": 15,
                "vo2max": 32, "phq9_score": 12, "stress_level": 7, "screen_time_hours": 11, "academic_gpa": 2.4, "study_hours_daily": 9,
                "exam_stress": 9, "academic_year": "Year 3", "family_diabetes": 1, "last_blood_report_date": str(today - timedelta(days=140)),
                "last_vitd_test_date": str(today - timedelta(days=150)), "last_glucose_test_date": str(today - timedelta(days=110)),
                "last_general_checkup_date": str(today - timedelta(days=410)),
            },
            "arjun": {
                "ldl": 85, "hdl": 65, "vitamin_d": 38, "b12": 520, "fasting_glucose": 82, "hba1c": 4.9, "hemoglobin": 15.5, "weight_kg": 75,
                "bmi": 23.1, "body_fat_pct": 12, "muscle_mass_kg": 38, "body_age_device": 20, "resting_hr": 55, "hrv_ms": 65, "steps_today": 12500,
                "steps_avg_7d": 11000, "exercise_min": 65, "sleep_hours": 7.8, "sleep_deep_pct": 22, "sleep_rem_pct": 25, "vo2max": 52,
                "phq9_score": 3, "stress_level": 3, "screen_time_hours": 4, "academic_gpa": 3.9, "study_hours_daily": 4, "exam_stress": 3,
                "academic_year": "Year 1", "exercise_hours_week": 8, "diet_quality": "excellent", "last_blood_report_date": str(today - timedelta(days=45)),
                "last_vitd_test_date": str(today - timedelta(days=60)), "last_glucose_test_date": str(today - timedelta(days=80)),
                "last_general_checkup_date": str(today - timedelta(days=200)),
            },
        }
        streaks = {
            "zahoor": {"current_streak": 3, "longest_streak": 3, "total_xp": 250, "level": 2},
            "riya": {"current_streak": 0, "longest_streak": 0, "total_xp": 50, "level": 1},
            "arjun": {"current_streak": 12, "longest_streak": 12, "total_xp": 1200, "level": 5},
        }
        source_offsets = {
            "zahoor": {"healthkit": 1, "meal": 1, "water": 0, "posture": 10, "faceage": 40, "blood_report": 100, "mental_checkin": 8},
            "riya": {"healthkit": 5, "meal": 2, "water": 2, "posture": 9, "faceage": 31, "blood_report": 140, "mental_checkin": 10},
            "arjun": {"healthkit": 0, "meal": 1, "water": 0, "posture": 3, "faceage": 20, "blood_report": 45, "mental_checkin": 4},
        }
        refresh_intervals = {"healthkit": 2, "meal": 1, "water": 1, "posture": 7, "faceage": 30, "blood_report": 90, "mental_checkin": 7}
        for user in users:
            await db.execute(
                "INSERT OR IGNORE INTO users (id, name, age, sex, height_cm) VALUES (?,?,?,?,?)",
                (user["id"], user["name"], user["age"], user["sex"], user["height_cm"]),
            )
            await _ensure_profile_exists(user["id"], db)
            merged = {**profiles[user["id"]], "age": user["age"], "sex": user["sex"], "height_cm": user["height_cm"]}
            payload = _prepare_profile_payload(user["id"], merged, None)
            cols = ["user_id"] + PROFILE_COLUMNS
            await db.execute(
                f"INSERT OR REPLACE INTO profiles ({','.join(cols)}) VALUES ({','.join(['?'] * len(cols))})",
                [user["id"]] + [payload.get(col) for col in PROFILE_COLUMNS],
            )
            streak = streaks[user["id"]]
            await db.execute(
                "INSERT OR REPLACE INTO streaks (user_id, current_streak, longest_streak, last_streak_date, total_xp, level) VALUES (?,?,?,?,?,?)",
                (user["id"], streak["current_streak"], streak["longest_streak"], str(today - timedelta(days=1)), streak["total_xp"], streak["level"]),
            )
            for source, interval in refresh_intervals.items():
                offset_days = source_offsets[user["id"]][source]
                await db.execute(
                    "INSERT OR REPLACE INTO data_sources (user_id, source, last_synced_at, refresh_interval_days) VALUES (?,?,?,?)",
                    (user["id"], source, datetime.now() - timedelta(days=offset_days), interval),
                )
        await db.commit()
    finally:
        await db.close()
