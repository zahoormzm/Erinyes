from __future__ import annotations

import base64
import json
import os
import re
import socket
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.activity import assess_outdoor_conditions, check_inactivity, get_today_activity_overlay, get_workout_summary, get_workouts, get_workout_targets, log_workout
from backend.agents import coach, collector, mental_health, mirror, runner, time_machine
from backend.ai_router import ai_router
from backend.alerts import check_alerts, notify_doctor, process_alerts
from backend.database import (
    PROFILE_COLUMNS,
    create_user,
    get_all_users,
    get_db,
    get_meals,
    get_meals_for_day,
    get_posture_history,
    get_profile_dict,
    get_risk_projections,
    get_water_for_day,
    get_water_today,
    init_db,
    log_posture,
    log_meal as db_log_meal,
    log_water as db_log_water,
    save_risk_projections,
    update_profile_fields,
)
from backend.difficulty import classify_difficulty, select_max_iterations
from backend.family import create_family, get_family_dashboard, join_family
from backend.formulas import calculate_bio_age, cardiovascular_delta, mental_wellness_score, metabolic_delta, musculoskeletal_delta, neurological_delta, nutrition_targets, project_risk, simulate_habit_change
from backend.gamification import get_gamification_summary, get_leaderboard, process_action
from backend.parsers import analyze_meal_photo, parse_apple_health_file, parse_apple_health_xml
from backend.reports import build_doctor_report, render_doctor_report_text
from backend.reminder_engine import check_reminders, get_data_freshness
from backend.specialists import check_specialists
from backend.posture_runner import analyze_posture_image
from backend.smart_reminders import generate_smart_reminders
from backend.spotify import classify_music_emotion
from backend.tools.context_tools import get_weather

load_dotenv()
MOBILE_ENCRYPTION_KEY = b"healthhack2026secretkey123456789"

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("EIRVIEW_CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Initialize persistent resources on startup."""

    await init_db()
    yield


app = FastAPI(title="EirView API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
os.makedirs("uploads/meals", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


def _serialize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return JSON-safe row dicts."""

    return [{key: value for key, value in row.items()} for row in rows]


def _detect_local_ips() -> list[str]:
    """Return likely LAN IPs for mobile-device testing."""

    ips: set[str] = set()
    try:
        hostname = socket.gethostname()
        for item in socket.gethostbyname_ex(hostname)[2]:
            if item and not item.startswith("127."):
                ips.add(item)
    except Exception:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        candidate = probe.getsockname()[0]
        if candidate and not candidate.startswith("127."):
            ips.add(candidate)
        probe.close()
    except Exception:
        pass
    return sorted(ips)


async def _touch_data_source(db: Any, user_id: str, source: str, refresh_interval_days: int) -> None:
    """Upsert exact sync timing for a user data source."""

    await db.execute(
        """
        INSERT OR REPLACE INTO data_sources (user_id, source, last_synced_at, refresh_interval_days)
        VALUES (
            ?, ?, CURRENT_TIMESTAMP,
            COALESCE(
                (SELECT refresh_interval_days FROM data_sources WHERE user_id=? AND source=?),
                ?
            )
        )
        """,
        (user_id, source, user_id, source, refresh_interval_days),
    )


def _trim_chat_history(history: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    """Keep only the most recent chat turns and cap message length."""

    trimmed: list[dict[str, Any]] = []
    for item in history[-limit:]:
        trimmed.append({"role": item.get("role", "user"), "content": str(item.get("content", ""))[-1200:]})
    return trimmed


COACH_ALLOWED_KEYWORDS = {
    "health", "bio age", "biological age", "wellness", "habit", "habits", "nutrition", "food", "meal", "eat", "diet",
    "calories", "protein", "carbs", "fat", "fiber", "water", "hydration", "exercise", "workout", "training", "walk",
    "walking", "run", "running", "steps", "sleep", "stress", "recovery", "remainder", "reminder", "doctor", "specialist",
    "bp", "blood pressure", "hrv", "resting hr", "heart rate", "spo2", "oxygen", "vo2", "cholesterol", "ldl", "hdl",
    "glucose", "hba1c", "vitamin", "b12", "vitamin d", "tsh", "ferritin", "creatinine", "posture", "weight", "bmi",
    "mood", "mental", "burnout", "routine", "focus on", "what should i do", "what next", "plan", "goal", "goals",
    "improve", "reduce", "increase", "lower", "raise"
}

MENTAL_ALLOWED_KEYWORDS = {
    "stress", "stressed", "anxiety", "anxious", "panic", "panic attack", "burnout", "burned out", "mood", "sad",
    "depressed", "low", "overwhelmed", "overwhelm", "lonely", "focus", "motivation", "mental", "emotion", "emotional",
    "worry", "worried", "sleep", "rest", "tired", "fatigue", "coping", "cope", "journal", "mindfulness", "therapy",
    "counselor", "counselling", "feel", "feeling", "feelings", "self care", "wellbeing", "wellness", "exam stress",
    "study", "burn out", "routine", "spiraling", "spiral"
}

MENTAL_CRISIS_KEYWORDS = {
    "suicide", "kill myself", "self harm", "hurt myself", "end my life", "want to die", "don't want to live",
    "harm myself"
}

FUTURE_ALLOWED_KEYWORDS = {
    "future", "years", "year", "later", "trajectory", "progress", "bio age", "biological age", "risk", "habit",
    "habits", "sleep", "nutrition", "exercise", "workout", "training", "food", "diet", "meal", "cholesterol",
    "ldl", "hdl", "glucose", "hba1c", "blood pressure", "weight", "bmi", "health", "wellness", "if i keep",
    "what happens", "what will", "where will", "long term", "long-term", "path", "future self", "improve", "decline"
}


def _normalize_message(message: str) -> str:
    """Return a normalized lowercased message for keyword checks."""

    return " ".join(str(message or "").lower().split())


def _has_scope_keyword(message: str, keywords: set[str]) -> bool:
    """Return True when a normalized message contains any keyword."""

    normalized = _normalize_message(message)
    if not normalized:
        return False
    return any(keyword in normalized for keyword in keywords)


# Blocklist approach: only reject messages that are CLEARLY unrelated to health.
# The AI agents already have scope instructions in their system prompts and will
# redirect borderline questions themselves. This avoids false-blocking legitimate
# health queries that happen to not match a keyword whitelist.
_CLEARLY_OFFTOPIC = {
    "write me code", "write code", "python script", "javascript code", "html code",
    "help me with my homework", "solve this equation", "translate this",
    "tell me a joke", "write a poem", "write a story", "write an essay",
    "who won the", "what is the capital of", "how to cook",
    "what is the weather in", "book a flight", "order food",
}


def _is_clearly_offtopic(message: str) -> bool:
    """Return True only when the message is unambiguously not about health/wellness."""

    normalized = _normalize_message(message)
    if not normalized or len(normalized) < 3:
        return False
    return any(phrase in normalized for phrase in _CLEARLY_OFFTOPIC)


def _is_coach_question_in_scope(message: str) -> bool:
    """Return True unless the message is clearly not about health."""

    return not _is_clearly_offtopic(message)


def _is_mental_question_in_scope(message: str) -> bool:
    """Return True unless the message is clearly not about wellness."""

    return not _is_clearly_offtopic(message)


def _is_future_question_in_scope(message: str) -> bool:
    """Return True unless the message is clearly not about health trajectory."""

    return not _is_clearly_offtopic(message)


def _is_mental_crisis_message(message: str) -> bool:
    """Return True when the message suggests immediate mental-health danger."""

    return _has_scope_keyword(message, MENTAL_CRISIS_KEYWORDS)


def _merge_chat_context(message: str, context: str) -> str:
    """Prepend structured page context to the user message when provided."""

    context_text = str(context or "").strip()[-2500:]
    if not context_text:
        return message
    return f"Current EirView context:\n{context_text}\n\nUser question:\n{message}"


def _future_system_prompt(name: str, age: int, overall_bio_age: float) -> str:
    """Build a constrained future-self system prompt."""

    return (
        f"You are {name} at age {age + 15}, speaking to your younger self. Their bio age is {overall_bio_age}. "
        "Only answer about health trajectory, habits, risk, progress, and long-term consequences of current choices. "
        "If the user asks unrelated questions, briefly refuse and redirect to health progress and future outcomes. "
        "Ground your answer in the user's available health context and be concrete, calm, and motivating."
    )


def _mental_out_of_scope_message() -> str:
    """Return a short redirect for unrelated mental-chat questions."""

    return (
        "I’m the EirView mental wellness guide. I can help with stress, burnout, mood, routines, sleep-linked wellbeing, "
        "and supportive reflection grounded in your health context."
    )


def _coach_out_of_scope_message() -> str:
    """Return a short redirect for unrelated coach questions."""

    return (
        "I’m the EirView health coach. I can help with your metrics, habits, nutrition, sleep, activity, recovery, "
        "reminders, and next-step planning."
    )


def _future_out_of_scope_message() -> str:
    """Return a short redirect for unrelated future-self questions."""

    return (
        "I’m your EirView future-self guide. I can help you think through where your current health habits and metrics "
        "are likely to lead over time."
    )


def _mental_crisis_message() -> str:
    """Return a short immediate-support response for crisis language."""

    return (
        "I’m really sorry you’re dealing with this. I’m not a crisis service, so please contact local emergency help or a "
        "trusted person right now and do not stay alone with these thoughts. If you can, go to the nearest emergency service "
        "or ask someone nearby to stay with you while you get immediate help."
    )


async def _stream_static_sse(message: str) -> Any:
    """Yield a short static SSE response."""

    yield f"data: {json.dumps({'type': 'text', 'content': message})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


def _enrich_specialist_recommendations(profile: dict[str, Any], specialists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach doctor-report evidence for each specialist recommendation."""

    enriched: list[dict[str, Any]] = []
    for item in specialists:
        report = build_doctor_report(profile, alerts=[], specialists=[item])
        enriched.append({**item, "doctor_report": report, "doctor_report_text": render_doctor_report_text(report)})
    return enriched


def _now_iso() -> str:
    """Return an ISO-8601 timestamp in local time."""

    return datetime.now().astimezone().isoformat(timespec="seconds")


def _meal_image_url(photo_path: str | None) -> str | None:
    """Convert a stored meal photo path into a public URL."""

    if not photo_path:
        return None
    normalized = str(photo_path).replace("\\", "/").lstrip("./")
    if normalized.startswith("uploads/"):
        return f"/{normalized}"
    if normalized.startswith("/uploads/"):
        return normalized
    return f"/uploads/meals/{os.path.basename(normalized)}"


def _serialize_meals_with_images(meals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach image URLs to meal rows for frontend rendering."""

    serialized: list[dict[str, Any]] = []
    for meal in meals:
        item = dict(meal)
        item["image_url"] = _meal_image_url(item.get("photo_path"))
        serialized.append(item)
    return serialized


def _agent_label(agent_name: str | None) -> str:
    """Map internal agent ids to user-facing labels."""

    labels = {
        "coach": "Coach",
        "mental_health": "Mental Health",
        "time_machine": "Future Self",
        "collector": "Collector",
        "mirror": "Mirror",
    }
    return labels.get(str(agent_name or "").strip(), str(agent_name or "Unknown"))


def _age_delta_status(value: float, chrono: float) -> str:
    """Return a semantic age-gap status."""

    gap = value - chrono
    if gap <= 0:
        return "good"
    if gap <= 3:
        return "warning"
    return "critical"


def _formula_breakdown_payload(metric: str, profile: dict[str, Any], chrono_age: float) -> dict[str, Any] | None:
    """Build the formula tooltip payload for one supported metric."""

    bio = calculate_bio_age(profile)
    wellness = mental_wellness_score(profile)
    subsystem_map = {
        "bio_age_cardiovascular": ("Cardiovascular Biological Age", cardiovascular_delta(profile), bio.get("cardiovascular")),
        "bio_age_metabolic": ("Metabolic Biological Age", metabolic_delta(profile), bio.get("metabolic")),
        "bio_age_musculoskeletal": ("Musculoskeletal Biological Age", musculoskeletal_delta(profile), bio.get("musculoskeletal")),
        "bio_age_neurological": ("Neurological Biological Age", neurological_delta(profile), bio.get("neurological")),
    }
    if metric == "bio_age_overall":
        cv = cardiovascular_delta(profile)
        met = metabolic_delta(profile)
        msk = musculoskeletal_delta(profile)
        neuro = neurological_delta(profile)
        cv_total = float(cv.get("total") or 0)
        met_total = float(met.get("total") or 0)
        msk_total = float(msk.get("total") or 0)
        neuro_total = float(neuro.get("total") or 0)
        return {
            "metric": "Biological Age (Overall)",
            "value": bio.get("overall"),
            "formula": (
                f"Chrono Age ({chrono_age}) + 0.30×CV({cv_total:.2f}) + "
                f"0.25×Met({met_total:.2f}) + 0.20×MSK({msk_total:.2f}) + "
                f"0.25×Neuro({neuro_total:.2f})"
            ),
            "inputs": {
                "chronological_age": chrono_age,
                "cv_delta": cv,
                "met_delta": met,
                "msk_delta": msk,
                "neuro_delta": neuro,
            },
            "weights": {"cv": 0.30, "met": 0.25, "msk": 0.20, "neuro": 0.25},
            "sources": ["Framingham Heart Study", "Levine Phenotypic Age", "D'Agostino 2008"],
        }
    if metric in subsystem_map:
        title, breakdown, value = subsystem_map[metric]
        return {
            "metric": title,
            "value": value,
            "formula": f"Chrono Age ({chrono_age}) + subsystem delta ({breakdown.get('total')})",
            "inputs": {"subsystem": breakdown},
            "sources": ["EirView subsystem scoring rules"],
        }
    if metric == "mental_wellness_score":
        return {
            "metric": "Mental Wellness Score",
            "value": wellness.get("score"),
            "formula": "100 - PHQ9 - Sleep - Stress - Screen - Academic - Exercise - Posture - Vitamin D - HRV penalties",
            "inputs": {
                "wellness": {
                    "components": [
                        {"input": item.get("name"), "value": f"-{item.get('penalty')}", "delta": -float(item.get("penalty") or 0), "reasoning": "Penalty applied"}
                        for item in wellness.get("breakdown_list", [])
                    ]
                }
            },
            "sources": ["EirView weighted wellness penalty model"],
        }
    normalized = metric.replace("_penalty", "").replace("_", " ").title()
    for item in wellness.get("breakdown_list", []):
        if item.get("name") == normalized:
            return {
                "metric": normalized,
                "value": item.get("penalty"),
                "formula": f"{normalized} penalty contribution",
                "inputs": {"wellness": {"components": [{"input": normalized, "value": item.get("penalty"), "delta": -float(item.get('penalty') or 0), "reasoning": "Penalty applied"}]}},
                "sources": ["EirView weighted wellness penalty model"],
            }
    return None


def _fallback_meal_estimate(description: str) -> dict[str, Any]:
    """Return a deterministic quantity-aware fallback meal estimate."""

    lines = [line.strip() for line in description.splitlines() if line.strip()]
    items = []
    total = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "sat_fat_g": 0.0, "fiber_g": 0.0}
    for line in lines or [description]:
        portion_g = 200 if "cup" in line.lower() or "bowl" in line.lower() else 120 if any(token in line.lower() for token in ("roti", "chapati", "bread")) else 150
        item = {
            "item": line,
            "portion_g": portion_g,
            "calories": round(portion_g * 1.6, 1),
            "protein_g": round(portion_g * 0.06, 1),
            "carbs_g": round(portion_g * 0.2, 1),
            "fat_g": round(portion_g * 0.04, 1),
            "sat_fat_g": round(portion_g * 0.01, 1),
            "fiber_g": round(portion_g * 0.02, 1),
        }
        items.append(item)
        for key in total:
            total[key] += item[key]
    return {
        "description": description,
        "items": items,
        "total": {key: round(value, 1) for key, value in total.items()},
        "flags": [],
        "grounding": "Quantity-aware fallback estimate",
    }


def _estimate_meal_from_text(description: str) -> dict[str, Any]:
    """Estimate meal nutrition from free text with quantity-aware instructions."""

    prompt = (
        "Analyze this meal description and return strict JSON with keys description, items, total, flags. "
        "For EACH item, estimate the quantity in grams based on the description. If the user says '1 cup rice', convert to approximately 200g. "
        "If they say '2 rotis', estimate 60g each. ALWAYS output portion_g for each item. Multiply per-100g values by the actual quantity to get real nutritional values. "
        "Never return per-100g values as the total. Each item must include item, portion_g, calories, protein_g, carbs_g, fat_g, sat_fat_g, fiber_g."
    )
    try:
        response = ai_router._call_claude(
            system="You are a nutrition extraction engine. Return JSON only.",
            messages=[{"role": "user", "content": f"{prompt}\n\nMeal description:\n{description}"}],
            tools=None,
            max_tokens=500,
        )
        text = "".join(getattr(block, "text", "") for block in getattr(response, "content", []))
        payload = json.loads(re.search(r"\{.*\}", text, re.DOTALL).group(0)) if text else None
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return _fallback_meal_estimate(description)


def _mobile_error_response(status_code: int, code: str, message: str, retryable: bool = False) -> JSONResponse:
    """Return a mobile-contract error response."""

    return JSONResponse(
        status_code=status_code,
        content={"status": "error", "code": code, "message": message, "retryable": retryable},
    )


async def _decrypt_mobile_envelope(request: Request) -> dict[str, Any]:
    """Decrypt an AES-GCM wrapped mobile request."""

    envelope = await request.json()
    if not isinstance(envelope, dict) or not envelope.get("encrypted"):
        raise ValueError("Failed to decrypt request body. Check encryption key.")
    try:
        iv = base64.b64decode(envelope["iv"])
        ciphertext = base64.b64decode(envelope["data"])
        tag = base64.b64decode(envelope["tag"])
        plaintext = AESGCM(MOBILE_ENCRYPTION_KEY).decrypt(iv, ciphertext + tag, None)
        return json.loads(plaintext.decode("utf-8"))
    except Exception as exc:
        raise ValueError("Failed to decrypt request body. Check encryption key.") from exc


def _mobile_healthkit_summary(profile: dict[str, Any]) -> dict[str, Any]:
    """Return HealthKit-style summary fields from the canonical profile."""

    return {
        "resting_hr_bpm": profile.get("resting_hr"),
        "hrv_sdnn_ms": profile.get("hrv_ms"),
        "steps_avg_7d": profile.get("steps_avg_7d"),
        "sleep_hours": profile.get("sleep_hours"),
        "active_energy_kcal": profile.get("active_energy_kcal"),
        "exercise_min_today": profile.get("exercise_min"),
        "vo2max_ml_kg_min": profile.get("vo2max"),
        "respiratory_rate_bpm": profile.get("respiratory_rate"),
        "walking_asymmetry_pct": profile.get("walking_asymmetry_pct"),
        "flights_climbed_today": profile.get("flights_climbed"),
        "body_mass_kg": profile.get("weight_kg"),
        "height_cm": profile.get("height_cm"),
        "blood_oxygen_pct": profile.get("blood_oxygen_pct"),
    }


def _mobile_manual_inputs(profile: dict[str, Any]) -> dict[str, Any]:
    """Return the mobile manual-input grouping from the canonical profile."""

    return {
        "blood": {
            "ldl": profile.get("ldl"),
            "hdl": profile.get("hdl"),
            "triglycerides": profile.get("triglycerides"),
            "total_cholesterol": profile.get("total_cholesterol"),
            "vitamin_d": profile.get("vitamin_d"),
            "b12": profile.get("b12"),
            "tsh": profile.get("tsh"),
            "ferritin": profile.get("ferritin"),
            "fasting_glucose": profile.get("fasting_glucose"),
            "hba1c": profile.get("hba1c"),
            "hemoglobin": profile.get("hemoglobin"),
            "creatinine": profile.get("creatinine"),
            "sgpt_alt": profile.get("sgpt_alt"),
            "sgot_ast": profile.get("sgot_ast"),
        },
        "body": {
            "weight_kg": profile.get("weight_kg"),
            "bmi": profile.get("bmi"),
            "bmr": profile.get("bmr"),
            "body_fat_pct": profile.get("body_fat_pct"),
            "visceral_fat_kg": profile.get("visceral_fat_kg"),
            "muscle_mass_kg": profile.get("muscle_mass_kg"),
            "body_water_pct": profile.get("body_water_pct"),
            "protein_kg": profile.get("protein_kg"),
            "bone_mass_kg": profile.get("bone_mass_kg"),
            "body_age_device": profile.get("body_age_device"),
        },
        "lifestyle": {
            "exercise_hours_week": profile.get("exercise_hours_week"),
            "sleep_target": profile.get("sleep_target"),
            "smoking": profile.get("smoking"),
            "diet_quality": profile.get("diet_quality"),
            "stress_level": profile.get("stress_level"),
            "screen_time_hours": profile.get("screen_time_hours"),
        },
        "family_history": {
            "diabetes": bool(profile.get("family_diabetes")),
            "heart_disease": bool(profile.get("family_heart")),
            "hypertension": bool(profile.get("family_hypertension")),
            "mental_health": bool(profile.get("family_mental")),
        },
    }


def _mobile_source_status(profile: dict[str, Any]) -> dict[str, Any]:
    """Return lightweight mobile source-status metadata."""

    return {
        "healthkit": {"present": any(profile.get(key) is not None for key in ("resting_hr", "steps_avg_7d", "sleep_hours")), "last_sync": profile.get("updated_at")},
        "blood_report": {"present": any(profile.get(key) is not None for key in ("ldl", "hdl", "vitamin_d", "hba1c")), "last_sync": profile.get("last_blood_report_date")},
        "cultfit": {"present": any(profile.get(key) is not None for key in ("body_fat_pct", "muscle_mass_kg", "visceral_fat_kg")), "last_sync": profile.get("updated_at")},
        "face_age": {"present": profile.get("face_age") is not None, "last_sync": profile.get("updated_at") if profile.get("face_age") is not None else None},
        "posture": {"present": profile.get("posture_score_pct") is not None, "last_sync": profile.get("updated_at") if profile.get("posture_score_pct") is not None else None},
    }


def _mobile_missing_fields(profile: dict[str, Any]) -> list[str]:
    """Return the key missing fields expected by the mobile app."""

    fields = ["vo2max", "blood_pressure_systolic", "blood_pressure_diastolic", "fasting_glucose"]
    return [field for field in fields if profile.get(field) is None]


def _mobile_profile_version(profile: dict[str, Any]) -> str:
    """Generate a profile version string from the latest update timestamp."""

    timestamp = str(profile.get("updated_at") or _now_iso())
    digits = "".join(char for char in timestamp if char.isdigit())
    return f"v{digits[:14] or '0'}"


def _top_wellness_labels(wellness: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return top concern and top strength labels from the wellness breakdown."""

    breakdown = wellness.get("breakdown", {})
    if not breakdown:
        return None, None
    concern = max(breakdown.items(), key=lambda item: item[1])[0]
    strength = min(breakdown.items(), key=lambda item: item[1])[0]
    return concern, strength


def _mobile_metric_status(label: str, value: Any, unit: str, status: str) -> dict[str, Any]:
    """Build one mobile metric status row."""

    return {"label": label, "value": value, "unit": unit, "status": status}


def _safe_float(value: Any) -> float | None:
    """Convert a value to float when possible."""

    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_dashboard_narrative(profile: dict[str, Any], bio_age: dict[str, Any], risk_rows: list[dict[str, Any]], wellness: dict[str, Any]) -> str:
    """Build a profile-specific Insights narrative."""

    chrono = _safe_float(profile.get("age")) or 0
    overall = _safe_float(bio_age.get("overall")) or chrono
    gap = round(overall - chrono, 1)
    ten_year = next((row for row in risk_rows if int(row.get("year", 0)) == 10), risk_rows[-1] if risk_rows else {})
    risk_candidates = [
        ("diabetes risk", _safe_float(ten_year.get("diabetes_risk"))),
        ("heart risk", _safe_float(ten_year.get("cvd_risk"))),
        ("metabolic risk", _safe_float(ten_year.get("metabolic_risk"))),
        ("cognitive risk", _safe_float(ten_year.get("mental_decline_risk"))),
    ]
    top_risk_label, top_risk_value = max(risk_candidates, key=lambda item: item[1] if item[1] is not None else -1)
    top_change = (bio_age.get("contributing_factors") or [{}])[0]
    top_change_text = top_change.get("change")
    top_change_gain = top_change.get("estimated_bio_age_reduction")

    if gap <= -0.5:
        age_open = f"Your biological age is {overall:.1f}, about {abs(gap):.1f} years younger than your chronological age of {chrono:.0f}."
    elif gap >= 0.5:
        age_open = f"Your biological age is {overall:.1f}, about {gap:.1f} years older than your chronological age of {chrono:.0f}."
    else:
        age_open = f"Your biological age is {overall:.1f}, almost aligned with your chronological age of {chrono:.0f}."

    subsystem_ages = {
        "cardiovascular": _safe_float(bio_age.get("cardiovascular")),
        "metabolic": _safe_float(bio_age.get("metabolic")),
        "musculoskeletal": _safe_float(bio_age.get("musculoskeletal")),
        "neurological": _safe_float(bio_age.get("neurological")),
    }
    weakest_system = max(subsystem_ages.items(), key=lambda item: item[1] if item[1] is not None else -999)[0]
    strongest_system = min(subsystem_ages.items(), key=lambda item: item[1] if item[1] is not None else 999)[0]

    risk_text = ""
    if top_risk_value is not None:
        risk_text = f" On your current trajectory, your highest modeled 10-year issue is {top_risk_label} at about {top_risk_value * 100:.1f}%."

    leverage_text = ""
    if top_change_text:
        leverage_text = (
            f" The biggest lever right now is {top_change_text.lower()},"
            f" worth about {float(top_change_gain):.1f} years of biological-age improvement."
            if top_change_gain is not None
            else f" The biggest lever right now is {top_change_text.lower()}."
        )

    wellness_score = _safe_float(wellness.get("score"))
    wellness_text = f" Your current mental wellness score is {wellness_score:.1f}/100." if wellness_score is not None else ""

    return (
        f"{age_open} Your strongest subsystem is {strongest_system}, while {weakest_system} is currently the main drag."
        f"{risk_text}{leverage_text}{wellness_text}"
    )


def _build_simulation_narrative(profile: dict[str, Any], changes: dict[str, Any], simulation: dict[str, Any]) -> str:
    """Build a deterministic scenario summary from the simulated deltas."""

    current = simulation.get("current", {})
    projected = simulation.get("projected", {})
    improvement = _safe_float(simulation.get("improvement")) or 0.0
    overall_current = _safe_float(current.get("overall")) or 0.0
    overall_projected = _safe_float(projected.get("overall")) or overall_current
    duration_label = str(((simulation.get("duration") or {}).get("label")) or "3 months")
    changed_inputs: list[str] = []
    if "sleep" in changes:
        changed_inputs.append(f"sleep from {(_safe_float(profile.get('sleep_hours')) or 0):.1f}h to {(_safe_float(changes.get('sleep')) or 0):.1f}h")
    if "exercise" in changes:
        projected_minutes = int(float(changes.get("exercise") or 0) * 60 / 7)
        current_minutes = int(_safe_float(profile.get("exercise_min")) or 0)
        changed_inputs.append(f"exercise from {(_safe_float(profile.get('exercise_hours_week')) or 0):.1f} to {(_safe_float(changes.get('exercise')) or 0):.1f} hours/week")
        changed_inputs.append(f"daily exercise minutes from {current_minutes} to {projected_minutes}")
    if "diet" in changes:
        diet_labels = {1: "poor", 2: "average", 3: "good", 4: "excellent"}
        changed_inputs.append(
            f"diet quality from {str(profile.get('diet_quality') or 'average').lower()} to {diet_labels.get(int(changes.get('diet', 2)), 'average')}"
        )
    if "stress" in changes:
        changed_inputs.append(f"stress from {(_safe_float(profile.get('stress_level')) or 0):.0f}/10 to {(_safe_float(changes.get('stress')) or 0):.0f}/10")
    if "screen_time" in changes:
        changed_inputs.append(
            f"screen time from {(_safe_float(profile.get('screen_time_hours')) or 0):.0f}h to {(_safe_float(changes.get('screen_time')) or 0):.0f}h"
        )
    if "exam_stress" in changes:
        changed_inputs.append(
            f"academic stress from {(_safe_float(profile.get('exam_stress')) or 0):.0f}/10 to {(_safe_float(changes.get('exam_stress')) or 0):.0f}/10"
        )

    subsystem_deltas = [
        ("cardiovascular", (_safe_float(projected.get("cardiovascular")) or 0.0) - (_safe_float(current.get("cardiovascular")) or 0.0)),
        ("metabolic", (_safe_float(projected.get("metabolic")) or 0.0) - (_safe_float(current.get("metabolic")) or 0.0)),
        ("musculoskeletal", (_safe_float(projected.get("musculoskeletal")) or 0.0) - (_safe_float(current.get("musculoskeletal")) or 0.0)),
        ("neurological", (_safe_float(projected.get("neurological")) or 0.0) - (_safe_float(current.get("neurological")) or 0.0)),
    ]
    top_subsystem, top_subsystem_delta = max(subsystem_deltas, key=lambda item: abs(item[1]))

    current_ten_year = next((row for row in simulation.get("new_risk_projections", []) if int(row.get("year", 0)) == 10), None)
    baseline_ten_year = project_risk(profile, years=15)
    baseline_ten_year = next((row for row in baseline_ten_year if int(row.get("year", 0)) == 10), None)
    risk_shift_text = ""
    if current_ten_year and baseline_ten_year:
        risk_deltas = [
            ("diabetes risk", ((_safe_float(current_ten_year.get("diabetes_risk")) or 0.0) - (_safe_float(baseline_ten_year.get("diabetes_risk")) or 0.0)) * 100),
            ("heart risk", ((_safe_float(current_ten_year.get("cvd_risk")) or 0.0) - (_safe_float(baseline_ten_year.get("cvd_risk")) or 0.0)) * 100),
            ("metabolic risk", ((_safe_float(current_ten_year.get("metabolic_risk")) or 0.0) - (_safe_float(baseline_ten_year.get("metabolic_risk")) or 0.0)) * 100),
            ("cognitive risk", ((_safe_float(current_ten_year.get("mental_decline_risk")) or 0.0) - (_safe_float(baseline_ten_year.get("mental_decline_risk")) or 0.0)) * 100),
        ]
        top_risk, top_risk_delta = max(risk_deltas, key=lambda item: abs(item[1]))
        if abs(top_risk_delta) >= 0.05:
            direction = "higher" if top_risk_delta > 0 else "lower"
            risk_shift_text = f" The clearest 10-year change is {top_risk}, moving {abs(top_risk_delta):.1f} points {direction}."

    change_text = (
        f"If you maintained this pattern for {duration_label.lower()}, you would be testing {', '.join(changed_inputs)}."
        if changed_inputs
        else f"If you maintained this pattern for {duration_label.lower()}, you would be testing a hypothetical lifestyle change."
    )
    direction_text = (
        f" That improves projected biological age from {overall_current:.1f} to {overall_projected:.1f}, making you {improvement:.1f} years biologically younger."
        if improvement > 0
        else f" That worsens projected biological age from {overall_current:.1f} to {overall_projected:.1f}, making you {abs(improvement):.1f} years biologically older."
        if improvement < 0
        else f" That leaves projected biological age flat at {overall_projected:.1f}."
    )
    subsystem_text = (
        f" The biggest subsystem movement is {top_subsystem}, shifting by {abs(top_subsystem_delta):.1f} years "
        f"{'worse' if top_subsystem_delta > 0 else 'better' if top_subsystem_delta < 0 else 'with no material change'}."
    )
    return f"{change_text}{direction_text}{subsystem_text}{risk_shift_text}"


def _build_cross_domain_insight(profile: dict[str, Any], bio_age: dict[str, Any]) -> str:
    """Build a specific cross-domain insight from available profile signals."""

    sleep_hours = _safe_float(profile.get("sleep_hours"))
    steps_avg = _safe_float(profile.get("steps_avg_7d"))
    hrv = _safe_float(profile.get("hrv_ms"))
    ldl = _safe_float(profile.get("ldl"))
    exam_stress = _safe_float(profile.get("exam_stress"))

    if sleep_hours is not None and sleep_hours < 6 and steps_avg is not None and steps_avg < 8000:
        return (
            f"You are averaging {sleep_hours:.1f} hours of sleep and {steps_avg:.0f} daily steps. "
            "That combination is likely pushing both neurological recovery and metabolic risk in the wrong direction."
        )
    if ldl is not None and ldl > 130 and sleep_hours is not None and sleep_hours < 7:
        return (
            f"Your LDL at {ldl:.0f} mg/dL plus short sleep around {sleep_hours:.1f} hours suggests cardiovascular recovery is under more strain than your age alone would imply."
        )
    if hrv is not None and hrv < 30 and exam_stress is not None and exam_stress > 7:
        return (
            f"Your HRV is {hrv:.1f} ms while academic stress is {exam_stress:.0f}/10. "
            "That pattern suggests recovery load is high and stress management may now matter as much as exercise volume."
        )
    top_change = (bio_age.get("contributing_factors") or [{}])[0].get("change")
    if top_change:
        return f"Your current data suggests the clearest next-step leverage comes from {top_change.lower()}."
    return "Your available data is stable overall, but the next useful improvement will become clearer as you log more sleep, activity, and lab data."


def _today_nutrition_progress(meals: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate today's consumed meal totals for dashboard nutrition bars."""

    today = date.today().isoformat()
    totals = {
        "current_calories": 0.0,
        "current_protein_g": 0.0,
        "current_carbs_g": 0.0,
        "current_fat_g": 0.0,
        "current_sat_fat_g": 0.0,
        "current_fiber_g": 0.0,
    }
    for meal in meals:
        timestamp = str(meal.get("timestamp") or meal.get("date") or "")
        if not timestamp.startswith(today):
            continue
        totals["current_calories"] += float(meal.get("calories") or meal.get("nutrition", {}).get("calories") or 0)
        totals["current_protein_g"] += float(meal.get("protein_g") or meal.get("nutrition", {}).get("protein_g") or 0)
        totals["current_carbs_g"] += float(meal.get("carbs_g") or meal.get("nutrition", {}).get("carbs_g") or 0)
        totals["current_fat_g"] += float(meal.get("fat_g") or meal.get("nutrition", {}).get("fat_g") or 0)
        totals["current_sat_fat_g"] += float(meal.get("saturated_fat_g") or meal.get("sat_fat_g") or meal.get("nutrition", {}).get("sat_fat_g") or 0)
        totals["current_fiber_g"] += float(meal.get("fiber_g") or meal.get("nutrition", {}).get("fiber_g") or 0)
    return {key: round(value, 1) for key, value in totals.items()}


def _nutrition_progress_for_day(meals: list[dict[str, Any]], day: str) -> dict[str, float]:
    """Aggregate consumed meal totals for a specific calendar day."""

    totals = {
        "current_calories": 0.0,
        "current_protein_g": 0.0,
        "current_carbs_g": 0.0,
        "current_fat_g": 0.0,
        "current_sat_fat_g": 0.0,
        "current_fiber_g": 0.0,
    }
    for meal in meals:
        timestamp = str(meal.get("timestamp") or meal.get("date") or "")
        if not timestamp.startswith(day):
            continue
        totals["current_calories"] += float(meal.get("calories") or meal.get("nutrition", {}).get("calories") or 0)
        totals["current_protein_g"] += float(meal.get("protein_g") or meal.get("nutrition", {}).get("protein_g") or 0)
        totals["current_carbs_g"] += float(meal.get("carbs_g") or meal.get("nutrition", {}).get("carbs_g") or 0)
        totals["current_fat_g"] += float(meal.get("fat_g") or meal.get("nutrition", {}).get("fat_g") or 0)
        totals["current_sat_fat_g"] += float(meal.get("saturated_fat_g") or meal.get("sat_fat_g") or meal.get("nutrition", {}).get("sat_fat_g") or 0)
        totals["current_fiber_g"] += float(meal.get("fiber_g") or meal.get("nutrition", {}).get("fiber_g") or 0)
    return {key: round(value, 1) for key, value in totals.items()}


def _mobile_dashboard_payload(profile: dict[str, Any], risk_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build the mobile dashboard response shape from the canonical profile."""

    bio_age = calculate_bio_age(profile)
    wellness = mental_wellness_score(profile)
    top_concern, top_strength = _top_wellness_labels(wellness)
    rows = risk_rows or []
    ten_year = next((row for row in rows if int(row.get("year", 0)) == 10), rows[-1] if rows else {})
    recommendations = [item.get("change") for item in bio_age.get("contributing_factors", [])[:3] if item.get("change")]
    metrics = [
        _mobile_metric_status("Resting HR", profile.get("resting_hr"), "bpm", "good" if (profile.get("resting_hr") or 999) < 70 else "warning"),
        _mobile_metric_status("HRV", profile.get("hrv_ms"), "ms", "good" if (profile.get("hrv_ms") or 0) >= 40 else "warning"),
        _mobile_metric_status("Steps (7d avg)", profile.get("steps_avg_7d"), "steps", "good" if (profile.get("steps_avg_7d") or 0) >= 7500 else "warning"),
        _mobile_metric_status("Sleep", profile.get("sleep_hours"), "hours", "good" if (profile.get("sleep_hours") or 0) >= 7 else "warning"),
        _mobile_metric_status("LDL", profile.get("ldl"), "mg/dL", "elevated" if (profile.get("ldl") or 0) >= 120 else "good"),
        _mobile_metric_status("Vitamin D", profile.get("vitamin_d"), "ng/mL", "deficient" if (profile.get("vitamin_d") or 999) < 20 else "good"),
    ]
    return {
        "chronological_age": profile.get("age"),
        "biological_age": bio_age["overall"],
        "subsystem_ages": {
            "cardiovascular": bio_age["cardiovascular"],
            "metabolic": bio_age["metabolic"],
            "musculoskeletal": bio_age["musculoskeletal"],
            "neurological": bio_age["neurological"],
        },
        "risk_summary": {
            "diabetes_10yr": ten_year.get("diabetes_risk"),
            "cvd_10yr": ten_year.get("cvd_risk"),
            "metabolic_10yr": ten_year.get("metabolic_risk"),
        },
        "wellness_summary": {
            "mental_wellness_score": wellness.get("score"),
            "top_concern": top_concern,
            "top_strength": top_strength,
        },
        "key_metrics": metrics,
        "recommendation_summary": recommendations,
        "updated_at": profile.get("updated_at"),
    }


def _mobile_profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    """Build the mobile profile summary shape."""

    source_status = _mobile_source_status(profile)
    present = [name for name, meta in source_status.items() if meta["present"]]
    missing = [name for name, meta in source_status.items() if not meta["present"]]
    completeness_denominator = 4
    completeness = round(len(present) / completeness_denominator * 100)
    return {
        "sources_present": present,
        "sources_missing": missing,
        "data_completeness_pct": completeness,
    }


def _mobile_profile_updates_from_sync(payload: dict[str, Any]) -> dict[str, Any]:
    """Flatten mobile sync payload into canonical profile fields."""

    updates: dict[str, Any] = {}
    healthkit = payload.get("healthkit") or {}
    sleep = healthkit.get("sleep_last_night") or {}
    updates.update(
        {
            "resting_hr": healthkit.get("resting_hr_bpm"),
            "hrv_ms": healthkit.get("hrv_sdnn_ms"),
            "steps_today": healthkit.get("steps_today"),
            "steps_avg_7d": healthkit.get("steps_avg_7d"),
            "active_energy_kcal": healthkit.get("active_energy_kcal"),
            "exercise_min": healthkit.get("exercise_min_today"),
            "vo2max": healthkit.get("vo2max_ml_kg_min"),
            "respiratory_rate": healthkit.get("respiratory_rate_bpm"),
            "walking_asymmetry_pct": healthkit.get("walking_asymmetry_pct"),
            "flights_climbed": healthkit.get("flights_climbed_today"),
            "weight_kg": healthkit.get("body_mass_kg"),
            "blood_pressure_systolic": healthkit.get("blood_pressure_systolic"),
            "blood_pressure_diastolic": healthkit.get("blood_pressure_diastolic"),
            "blood_oxygen_pct": healthkit.get("blood_oxygen_pct"),
            "sleep_hours": sleep.get("total_hours"),
            "sleep_deep_pct": sleep.get("deep_pct"),
            "sleep_rem_pct": sleep.get("rem_pct"),
        }
    )
    manual = payload.get("manual_inputs") or {}
    updates.update(manual.get("blood") or {})
    updates.update(manual.get("body") or {})
    updates.update(manual.get("lifestyle") or {})
    family_history = manual.get("family_history") or {}
    updates.update(
        {
            "family_diabetes": family_history.get("diabetes"),
            "family_heart": family_history.get("heart_disease"),
            "family_hypertension": family_history.get("hypertension"),
            "family_mental": family_history.get("mental_health"),
        }
    )
    return {key: value for key, value in updates.items() if value is not None}


@app.get("/api/users")
async def list_users() -> list[dict[str, Any]]:
    """List all users."""

    return await get_all_users()


@app.post("/api/users")
async def create_user_endpoint(request: Request) -> dict[str, Any]:
    """Create a new user."""

    data = await request.json()
    try:
        return await create_user(data["id"], data["name"], data.get("age"), data.get("sex"), data.get("height_cm"))
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing field: {exc}") from exc


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str) -> dict[str, Any]:
    """Delete a user and all user-scoped data."""

    tables = [
        "profiles",
        "meals",
        "workouts",
        "water_log",
        "posture_history",
        "daily_actions",
        "streaks",
        "achievements",
        "agent_logs",
        "risk_projections",
        "data_sources",
        "reflections",
        "spotify_history",
        "spotify_tokens",
        "spotify_track_history",
        "weekly_challenges",
        "alerts",
        "specialist_referrals",
    ]
    db = await get_db()
    try:
        for table in tables:
            await db.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        await db.execute("DELETE FROM family_health_flags WHERE source_user_id=?", (user_id,))
        await db.execute("DELETE FROM family_members WHERE user_id=?", (user_id,))
        await db.execute("UPDATE users SET family_id=NULL WHERE id=?", (user_id,))
        await db.execute("DELETE FROM users WHERE id=?", (user_id,))
        await db.commit()
        return {"deleted": user_id}
    finally:
        await db.close()


@app.get("/api/mobile/health")
async def mobile_health() -> dict[str, Any]:
    """Lightweight health check for the iOS app."""

    return {"status": "ok", "server": "eirview", "version": app.version, "timestamp": _now_iso()}


@app.get("/api/server-info")
async def server_info() -> dict[str, Any]:
    """Return local machine connection details for mobile setup."""

    hostname = socket.gethostname()
    local_ips = _detect_local_ips()
    return {
        "hostname": hostname,
        "localhost_url": "http://127.0.0.1:8000",
        "local_ips": local_ips,
        "mobile_base_urls": [f"http://{ip}:8000" for ip in local_ips],
    }


@app.get("/api/mobile/profile/{user_id}")
async def mobile_profile(user_id: str) -> Any:
    """Return profile data in the iOS app contract shape."""

    db = await get_db()
    try:
        profile = await get_profile_dict(user_id, db)
        if profile is None:
            return _mobile_error_response(404, "UNKNOWN_USER", "User ID not found. Create user first.", False)
        return {
            "user_id": user_id,
            "profile_version": _mobile_profile_version(profile),
            "manual_inputs": _mobile_manual_inputs(profile),
            "healthkit_summary": _mobile_healthkit_summary(profile),
            "source_status": _mobile_source_status(profile),
            "updated_at": profile.get("updated_at"),
        }
    finally:
        await db.close()


@app.get("/api/mobile/dashboard/{user_id}")
async def mobile_dashboard(user_id: str) -> Any:
    """Return dashboard data in the iOS app contract shape."""

    db = await get_db()
    try:
        profile = await get_profile_dict(user_id, db)
        if profile is None:
            return _mobile_error_response(404, "UNKNOWN_USER", "User ID not found. Create user first.", False)
        risk_rows = await get_risk_projections(user_id)
        if not risk_rows:
            from backend.formulas import project_risk

            risk_rows = project_risk(profile)
            await save_risk_projections(user_id, risk_rows)
        return _mobile_dashboard_payload(profile, risk_rows)
    finally:
        await db.close()


@app.post("/api/mobile/sync")
async def mobile_sync(request: Request) -> Any:
    """Merge encrypted iOS snapshot data into the canonical user profile."""

    try:
        payload = await _decrypt_mobile_envelope(request)
    except ValueError:
        return _mobile_error_response(400, "INVALID_ENCRYPTION", "Failed to decrypt request body. Check encryption key.", False)

    user_id = payload.get("user_id")
    if not user_id:
        return _mobile_error_response(422, "INVALID_PAYLOAD", "Request body does not match expected schema.", False)

    db = await get_db()
    try:
        user = await (await db.execute("SELECT * FROM users WHERE id=?", (user_id,))).fetchone()
        if user is None:
            return _mobile_error_response(404, "UNKNOWN_USER", "User ID not found. Create user first.", False)

        updates = _mobile_profile_updates_from_sync(payload)
        healthkit = payload.get("healthkit") or {}
        if healthkit.get("height_cm") is not None:
            await db.execute("UPDATE users SET height_cm=? WHERE id=?", (healthkit.get("height_cm"), user_id))

        profile = await update_profile_fields(user_id, updates, db)

        workouts = healthkit.get("workouts_7d") or []
        if workouts:
            await db.execute("DELETE FROM workouts WHERE user_id=? AND source='healthkit_mobile'", (user_id,))
            for workout in workouts:
                await log_workout(
                    user_id,
                    {
                        "type": workout.get("type", "walking"),
                        "duration_min": workout.get("duration_min"),
                        "calories": workout.get("calories"),
                        "date": workout.get("date"),
                        "source": "healthkit_mobile",
                    },
                    db,
                )

        if healthkit:
            await db.execute(
                "INSERT OR REPLACE INTO data_sources (user_id, source, last_synced_at, refresh_interval_days) VALUES (?,?,CURRENT_TIMESTAMP,1)",
                (user_id, "healthkit"),
            )
        if payload.get("manual_inputs"):
            await db.execute(
                "INSERT OR REPLACE INTO data_sources (user_id, source, last_synced_at, refresh_interval_days) VALUES (?,?,CURRENT_TIMESTAMP,7)",
                (user_id, "manual_mobile"),
            )
        await db.commit()

        risk_rows = await get_risk_projections(user_id)
        if not risk_rows:
            from backend.formulas import project_risk

            risk_rows = project_risk(profile)
            await save_risk_projections(user_id, risk_rows)

        return {
            "status": "ok",
            "profile_version": _mobile_profile_version(profile),
            "dashboard": _mobile_dashboard_payload(profile, risk_rows),
            "profile_summary": _mobile_profile_summary(profile),
            "missing_fields": _mobile_missing_fields(profile),
            "last_processed_at": _now_iso(),
        }
    finally:
        await db.close()


@app.post("/api/mobile/simulate")
async def mobile_simulate(request: Request) -> Any:
    """Run encrypted mobile what-if simulation without persisting overrides."""

    try:
        payload = await _decrypt_mobile_envelope(request)
    except ValueError:
        return _mobile_error_response(400, "INVALID_ENCRYPTION", "Failed to decrypt request body. Check encryption key.", False)

    user_id = payload.get("user_id")
    overrides = payload.get("overrides")
    if not user_id or not isinstance(overrides, dict):
        return _mobile_error_response(422, "INVALID_PAYLOAD", "Request body does not match expected schema.", False)

    db = await get_db()
    try:
        profile = await get_profile_dict(user_id, db)
        if profile is None:
            return _mobile_error_response(404, "UNKNOWN_USER", "User ID not found. Create user first.", False)

        base_bio = calculate_bio_age(profile)
        base_wellness = mental_wellness_score(profile)
        simulated_profile = {
            **profile,
            "sleep_hours": overrides.get("sleep_hours", profile.get("sleep_hours")),
            "exercise_min": overrides.get("exercise_min_daily", profile.get("exercise_min")),
            "steps_avg_7d": overrides.get("steps_avg_7d", profile.get("steps_avg_7d")),
            "stress_level": overrides.get("stress_level", profile.get("stress_level")),
            "screen_time_hours": overrides.get("screen_time_hours", profile.get("screen_time_hours")),
        }
        simulated_bio = calculate_bio_age(simulated_profile)
        simulated_wellness = mental_wellness_score(simulated_profile)
        from backend.formulas import project_risk

        simulated_risk_rows = project_risk(simulated_profile)
        ten_year = next((row for row in simulated_risk_rows if int(row.get("year", 0)) == 10), simulated_risk_rows[-1] if simulated_risk_rows else {})
        top_concern, top_strength = _top_wellness_labels(simulated_wellness)
        return {
            "biological_age": simulated_bio["overall"],
            "subsystem_ages": {
                "cardiovascular": simulated_bio["cardiovascular"],
                "metabolic": simulated_bio["metabolic"],
                "musculoskeletal": simulated_bio["musculoskeletal"],
                "neurological": simulated_bio["neurological"],
            },
            "risk_summary": {
                "diabetes_10yr": ten_year.get("diabetes_risk"),
                "cvd_10yr": ten_year.get("cvd_risk"),
                "metabolic_10yr": ten_year.get("metabolic_risk"),
            },
            "wellness_summary": {
                "mental_wellness_score": simulated_wellness.get("score"),
                "top_concern": top_concern,
                "top_strength": top_strength,
            },
            "delta_summary": {
                "biological_age_delta": round(simulated_bio["overall"] - base_bio["overall"], 2),
                "cardiovascular_delta": round(simulated_bio["cardiovascular"] - base_bio["cardiovascular"], 2),
                "metabolic_delta": round(simulated_bio["metabolic"] - base_bio["metabolic"], 2),
                "musculoskeletal_delta": round(simulated_bio["musculoskeletal"] - base_bio["musculoskeletal"], 2),
                "neurological_delta": round(simulated_bio["neurological"] - base_bio["neurological"], 2),
                "mental_wellness_delta": round(simulated_wellness.get("score", 0) - base_wellness.get("score", 0), 2),
            },
        }
    finally:
        await db.close()


@app.get("/api/profile/{user_id}")
async def get_profile_endpoint(user_id: str) -> dict[str, Any]:
    """Get the full health profile for a user."""

    db = await get_db()
    try:
        profile = await get_profile_dict(user_id, db)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return profile
    finally:
        await db.close()


@app.get("/api/formula-breakdown/{user_id}/{metric}")
async def get_formula_breakdown(user_id: str, metric: str) -> dict[str, Any]:
    """Return a step-by-step formula breakdown for a supported metric."""

    db = await get_db()
    try:
        profile = await get_profile_dict(user_id, db)
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        chrono_age = float(profile.get("age") or 19)
        payload = _formula_breakdown_payload(metric, profile, chrono_age)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"No breakdown available for {metric}")
        return payload
    finally:
        await db.close()


@app.put("/api/profile/{user_id}")
async def update_profile_endpoint(user_id: str, request: Request) -> dict[str, Any]:
    """Update specific profile fields for a user."""

    data = await request.json()
    db = await get_db()
    try:
        profile = await update_profile_fields(user_id, data, db)
        alerts = await process_alerts(user_id, profile, db)
        return {"success": True, "updated_fields": list(data.keys()), "profile": profile, "alerts": alerts}
    finally:
        await db.close()


@app.get("/api/reflections/{user_id}")
async def get_reflections(user_id: str) -> dict[str, Any]:
    """Return active reflections for a user."""

    db = await get_db()
    try:
        rows = await (
            await db.execute(
                "SELECT * FROM reflections WHERE user_id=? AND is_active=1 ORDER BY created_at DESC",
                (user_id,),
            )
        ).fetchall()
        return {"reflections": [dict(row) for row in rows]}
    finally:
        await db.close()


@app.delete("/api/reflections/{user_id}")
async def clear_reflections(user_id: str) -> dict[str, Any]:
    """Soft-delete all active reflections for a user."""

    db = await get_db()
    try:
        await db.execute("UPDATE reflections SET is_active=0 WHERE user_id=?", (user_id,))
        await db.commit()
        return {"cleared": user_id}
    finally:
        await db.close()


@app.get("/api/dashboard/{user_id}")
async def get_dashboard(user_id: str) -> dict[str, Any]:
    """Get complete dashboard data for a user."""

    db = await get_db()
    try:
        profile = await get_profile_dict(user_id, db)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        current_time = datetime.now()
        bio_age = calculate_bio_age(profile)
        weather = await get_weather(user_id, db)
        weather_context = assess_outdoor_conditions(weather, current_time.hour)
        alerts = await check_alerts(user_id, db)
        specialists = _enrich_specialist_recommendations(profile, check_specialists(profile))
        gamification = await get_gamification_summary(user_id, db)
        nutrition = nutrition_targets(profile)
        workout_summary = await get_workout_summary(user_id, db)
        workout_target_data = await get_workout_targets(user_id, db)
        activity_overlay = await get_today_activity_overlay(user_id, db)
        meals = _serialize_meals_with_images(await get_meals(user_id))
        nutrition.update(_today_nutrition_progress(meals))
        water_today_ml = await get_water_today(user_id, db)
        wellness = mental_wellness_score(profile)
        reminder_list = await generate_smart_reminders(user_id, profile, {**weather, **weather_context}, water_today_ml, db)
        risk_rows = await get_risk_projections(user_id)
        if not risk_rows:
            from backend.formulas import project_risk

            risk_rows = project_risk(profile)
            await save_risk_projections(user_id, risk_rows)
        base_steps = int(profile.get("steps_today") or 0)
        estimated_steps = int(activity_overlay.get("estimated_steps_from_logged_activity") or 0)
        metrics = {
            "resting_hr": profile.get("resting_hr"),
            "hrv": profile.get("hrv_ms"),
            "steps": base_steps + estimated_steps,
            "steps_base": base_steps,
            "steps_from_logged_activity": estimated_steps,
            "steps_are_estimated": bool(activity_overlay.get("steps_estimated")),
            "sleep": profile.get("sleep_hours"),
            "vo2max": profile.get("vo2max"),
            "spo2": profile.get("blood_oxygen_pct"),
            "exercise_min": max(int(profile.get("exercise_min") or 0), int(activity_overlay.get("logged_workout_minutes_today") or 0)),
            "flights": profile.get("flights_climbed"),
            "logged_workout_calories": activity_overlay.get("logged_workout_calories_today"),
        }
        nudge_profile = {
            **profile,
            "steps_today": metrics["steps"],
            "exercise_min": metrics["exercise_min"],
        }
        nudge = check_inactivity(nudge_profile, current_time.hour, weather=weather, mental_score=wellness["score"])
        cross_domain = _build_cross_domain_insight(profile, bio_age)
        narrative = _build_dashboard_narrative(profile, bio_age, risk_rows, wellness)
        return {
            "profile": profile,
            "bio_age_overall": bio_age["overall"],
            "bio_age": bio_age,
            "bio_age_deltas": bio_age["deltas"],
            "face_age": profile.get("face_age"),
            "metrics": metrics,
            "step_goal": max(profile.get("steps_avg_7d") or 7500, 7500),
            "reminders": reminder_list,
            "alerts": alerts,
            "specialists": specialists,
            "gamification": gamification,
            "nutrition_targets": nutrition,
            "water_today_ml": water_today_ml,
            "workout_summary": workout_summary,
            "workout_targets": workout_target_data,
            "recent_meals": meals,
            "wellness_score": wellness["score"],
            "wellness_breakdown": wellness["breakdown_list"],
            "risk_projections": risk_rows,
            "cross_domain_insight": cross_domain,
            "narrative": narrative,
            "activity_nudge": nudge,
            "weather": {**weather, **weather_context},
        }
    finally:
        await db.close()


@app.get("/api/nutrition-day/{user_id}")
async def get_nutrition_day(user_id: str, day: str | None = None) -> dict[str, Any]:
    """Return nutrition totals, meals, and water for a specific day."""

    selected_day = (day or date.today().isoformat()).strip()
    try:
        datetime.strptime(selected_day, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="day must be in YYYY-MM-DD format") from exc

    db = await get_db()
    try:
        profile = await get_profile_dict(user_id, db)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        meals = _serialize_meals_with_images(await get_meals_for_day(user_id, selected_day, db))
        water_total_ml = await get_water_for_day(user_id, selected_day, db)
        targets = nutrition_targets(profile)
        targets.update(_nutrition_progress_for_day(meals, selected_day))
        return {
            "day": selected_day,
            "is_today": selected_day == date.today().isoformat(),
            "nutrition_targets": targets,
            "water_total_ml": water_total_ml,
            "meals": meals,
        }
    finally:
        await db.close()


@app.post("/api/nutrition-day/{user_id}/reset-today")
async def reset_today_nutrition(user_id: str) -> dict[str, Any]:
    """Delete today's meals and water entries for a user."""

    db = await get_db()
    try:
        profile = await get_profile_dict(user_id, db)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")

        meal_count_row = await (
            await db.execute(
                "SELECT COUNT(*) AS count FROM meals WHERE user_id=? AND DATE(timestamp, 'localtime')=DATE('now', 'localtime')",
                (user_id,),
            )
        ).fetchone()
        water_count_row = await (
            await db.execute(
                "SELECT COUNT(*) AS count FROM water_log WHERE user_id=? AND DATE(timestamp, 'localtime')=DATE('now', 'localtime')",
                (user_id,),
            )
        ).fetchone()
        meals_deleted = int((meal_count_row["count"] if meal_count_row else 0) or 0)
        water_entries_deleted = int((water_count_row["count"] if water_count_row else 0) or 0)

        await db.execute(
            "DELETE FROM meals WHERE user_id=? AND DATE(timestamp, 'localtime')=DATE('now', 'localtime')",
            (user_id,),
        )
        await db.execute(
            "DELETE FROM water_log WHERE user_id=? AND DATE(timestamp, 'localtime')=DATE('now', 'localtime')",
            (user_id,),
        )

        latest_meal_row = await (await db.execute("SELECT MAX(timestamp) AS latest FROM meals WHERE user_id=?", (user_id,))).fetchone()
        latest_water_row = await (await db.execute("SELECT MAX(timestamp) AS latest FROM water_log WHERE user_id=?", (user_id,))).fetchone()

        latest_meal = latest_meal_row["latest"] if latest_meal_row else None
        latest_water = latest_water_row["latest"] if latest_water_row else None

        if latest_meal:
            await db.execute(
                """
                INSERT OR REPLACE INTO data_sources (user_id, source, last_synced_at, refresh_interval_days)
                VALUES (?,?,?,COALESCE((SELECT refresh_interval_days FROM data_sources WHERE user_id=? AND source=?),1))
                """,
                (user_id, "meal", latest_meal, user_id, "meal"),
            )
        else:
            await db.execute("DELETE FROM data_sources WHERE user_id=? AND source='meal'", (user_id,))

        if latest_water:
            await db.execute(
                """
                INSERT OR REPLACE INTO data_sources (user_id, source, last_synced_at, refresh_interval_days)
                VALUES (?,?,?,COALESCE((SELECT refresh_interval_days FROM data_sources WHERE user_id=? AND source=?),1))
                """,
                (user_id, "water", latest_water, user_id, "water"),
            )
        else:
            await db.execute("DELETE FROM data_sources WHERE user_id=? AND source='water'", (user_id,))

        await db.commit()

        meals = _serialize_meals_with_images(await get_meals_for_day(user_id, date.today().isoformat(), db))
        water_total_ml = await get_water_for_day(user_id, date.today().isoformat(), db)
        targets = nutrition_targets(profile)
        targets.update(_nutrition_progress_for_day(meals, date.today().isoformat()))

        return {
            "success": True,
            "day": date.today().isoformat(),
            "meals_deleted": meals_deleted,
            "water_entries_deleted": water_entries_deleted,
            "nutrition_targets": targets,
            "water_total_ml": water_total_ml,
            "meals": meals,
        }
    finally:
        await db.close()


@app.post("/api/ingest")
async def ingest_data(file: UploadFile = File(...), data_type: str = Form(...), user_id: str = Form(...)) -> dict[str, Any]:
    """Upload blood PDF, Cult.fit image, or Apple Health XML and update the profile."""

    db = await get_db()
    tmp_path = ""
    try:
        suffix = os.path.splitext(file.filename or "")[1] or ".tmp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        if data_type == "blood_pdf":
            from backend.parsers import parse_blood_pdf

            extracted = await parse_blood_pdf(tmp_path, user_id, db)
            await _touch_data_source(db, user_id, "blood_report", 90)
        elif data_type == "cultfit_image":
            from backend.parsers import parse_cultfit_image

            extracted = await parse_cultfit_image(tmp_path, user_id, db)
            await _touch_data_source(db, user_id, "cultfit", 30)
        elif data_type == "apple_health_xml":
            extracted = parse_apple_health_file(tmp_path)
            await _touch_data_source(db, user_id, "apple_health", 2)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported data_type: {data_type}")
        workouts = extracted.pop("workouts_7d", []) if isinstance(extracted, dict) else []
        profile_updates = extracted.get("profile_updates", extracted) if isinstance(extracted, dict) else {}
        profile = await update_profile_fields(user_id, profile_updates if isinstance(profile_updates, dict) else {}, db)
        for workout in workouts:
            await log_workout(user_id, workout, db)
        alerts = await process_alerts(user_id, profile, db)
        specialists = _enrich_specialist_recommendations(profile, check_specialists(profile))
        mirror_result = await runner.run_agent(mirror, user_id, {}, db)
        await process_action(user_id, "data_upload", None, db)
        return {
            "success": True,
            "data_type": data_type,
            "extracted": extracted,
            "profile_updates_applied": profile_updates,
            "profile": profile,
            "alerts": alerts,
            "specialists": specialists,
            "mirror": mirror_result["result"],
            "workouts_logged": len(workouts),
        }
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        await db.close()


@app.post("/api/face-age")
async def face_age_endpoint(file: UploadFile = File(...), user_id: str = Form(...)) -> dict[str, Any]:
    """Accept a selfie image, run face age prediction, and persist it."""

    image_bytes = await file.read()
    try:
        from backend.faceage import predict_face_age

        face_age = predict_face_age(image_bytes)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Face age model is unavailable: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Face age prediction failed: {exc}") from exc
    db = await get_db()
    try:
        profile = await update_profile_fields(user_id, {"face_age": face_age}, db)
        await process_action(user_id, "selfie", None, db)
        return {"face_age": face_age, "profile": profile}
    finally:
        await db.close()


@app.post("/api/healthkit")
async def receive_healthkit(request: Request) -> dict[str, Any]:
    """Receive HealthKit-style JSON and update the profile."""

    data = await request.json()
    user_id = data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")
    health_data = data.get("data", {})
    db = await get_db()
    try:
        profile = await update_profile_fields(user_id, health_data, db)
        await _touch_data_source(db, user_id, "healthkit", 2)
        await db.commit()
        return {"success": True, "updated_fields": list(health_data.keys()), "profile": profile}
    finally:
        await db.close()


@app.post("/api/apple-health")
async def upload_apple_health(file: UploadFile = File(...), user_id: str = Form(...)) -> dict[str, Any]:
    """Upload Apple Health export.xml, parse it, update profile, and store workouts."""

    db = await get_db()
    tmp_path = ""
    try:
        suffix = os.path.splitext(file.filename or "")[1] or ".xml"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        health_data = parse_apple_health_file(tmp_path)
        workouts = health_data.pop("workouts_7d", [])
        detected_metrics = {key: value for key, value in health_data.items() if value is not None}
        profile_updates_applied = {key: value for key, value in detected_metrics.items() if key in PROFILE_COLUMNS}
        ignored_metrics = {key: value for key, value in detected_metrics.items() if key not in PROFILE_COLUMNS}
        profile = await update_profile_fields(user_id, profile_updates_applied, db)
        await _touch_data_source(db, user_id, "apple_health", 2)
        for workout in workouts:
            await log_workout(user_id, workout, db)
        await db.commit()
        return {
            "success": True,
            "metrics_updated": list(profile_updates_applied.keys()),
            "metrics_detected": list(detected_metrics.keys()),
            "profile_updates_applied": profile_updates_applied,
            "ignored_metrics": ignored_metrics,
            "workouts_found": len(workouts),
            "data": detected_metrics,
            "profile": profile,
        }
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        await db.close()


@app.post("/api/meal")
async def log_meal_endpoint(request: Request, file: UploadFile | None = File(None)) -> dict[str, Any]:
    """Log a meal via photo upload or text description."""

    db = await get_db()
    try:
        if file is not None:
            form = await request.form()
            user_id = str(form.get("user_id", "zahoor"))
            suffix = os.path.splitext(file.filename or "")[1].lower()
            if suffix not in {".jpg", ".jpeg", ".png"}:
                raise HTTPException(status_code=400, detail="Meal photo must be .jpg, .jpeg, or .png")
            file_bytes = await file.read()
            if len(file_bytes) > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Meal photo must be 10MB or smaller")
            filename = f"{uuid.uuid4().hex}{suffix}"
            photo_path = os.path.join("uploads", "meals", filename)
            with open(photo_path, "wb") as handle:
                handle.write(file_bytes)
            result = await analyze_meal_photo(file_bytes, user_id, db)
            result["photo_path"] = photo_path
            result["image_url"] = _meal_image_url(photo_path)
            await db_log_meal(user_id, result, db)
            await process_action(user_id, "meal_log", None, db)
            return result
        data = await request.json()
        user_id = data.get("user_id")
        description = data.get("description")
        if not user_id or not description:
            raise HTTPException(status_code=400, detail="Provide user_id and description")
        result = _estimate_meal_from_text(description)
        result["description"] = description
        await db_log_meal(user_id, result, db)
        await process_action(user_id, "meal_log", None, db)
        return result
    finally:
        await db.close()


@app.post("/api/water")
async def log_water_endpoint(request: Request) -> dict[str, Any]:
    """Log water intake for a user."""

    data = await request.json()
    user_id = data.get("user_id")
    amount_ml = int(data.get("amount_ml", 250))
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")
    await db_log_water(user_id, amount_ml)
    db = await get_db()
    try:
        today_total = await get_water_today(user_id)
        await process_action(user_id, "water_goal" if today_total >= 2000 else "meal_log", None, db)
        return {"success": True, "amount_ml": amount_ml, "today_total_ml": today_total, "target_ml": 2500, "pct_complete": round(today_total / 2500 * 100, 1)}
    finally:
        await db.close()


@app.post("/api/simulate")
async def simulate_endpoint(request: Request) -> dict[str, Any]:
    """Simulate the effect of a habit change on bio age and risk projections."""

    data = await request.json()
    user_id = data.get("user_id")
    changes = data.get("changes", {})
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")
    db = await get_db()
    try:
        profile = await get_profile_dict(user_id, db)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        simulation = simulate_habit_change(profile, changes)
        narrative = _build_simulation_narrative(profile, changes, simulation)
        return {"simulation": simulation, "narrative": narrative, "traces": []}
    finally:
        await db.close()


@app.post("/api/chat/future")
async def chat_future(request: Request) -> StreamingResponse:
    """Future-self SSE chat endpoint."""

    data = await request.json()
    user_id = data.get("user_id", "zahoor")
    message = str(data.get("message", ""))[-1200:]
    if not _is_future_question_in_scope(message):
        return StreamingResponse(_stream_static_sse(_future_out_of_scope_message()), media_type="text/event-stream")
    contextualized_message = _merge_chat_context(message, data.get("context", ""))
    db = await get_db()
    difficulty = classify_difficulty(message)
    return StreamingResponse(
        runner.stream_agent(
            time_machine,
            user_id,
            {"message": contextualized_message, "cache_key": message, "history": _trim_chat_history(data.get("history", [])), "difficulty": difficulty},
            db,
            close_db=True,
        ),
        media_type="text/event-stream",
    )


@app.post("/api/chat/mental")
async def chat_mental(request: Request) -> StreamingResponse:
    """Mental-health SSE chat endpoint."""

    data = await request.json()
    message = str(data.get("message", ""))[-1200:]
    if message == "__INIT__":
        message = (
            "Open the conversation warmly. Greet the user by name. Reference 1-2 specific things from their current data "
            "(for example sleep, vitamin D, wellness score, Spotify mood, or stress). Ask how they're feeling today. "
            "Keep it to 2-3 sentences. Do NOT give advice yet — just open the door."
        )
    if _is_mental_crisis_message(message):
        return StreamingResponse(_stream_static_sse(_mental_crisis_message()), media_type="text/event-stream")
    if not _is_mental_question_in_scope(message):
        return StreamingResponse(_stream_static_sse(_mental_out_of_scope_message()), media_type="text/event-stream")
    db = await get_db()
    difficulty = classify_difficulty(message)
    return StreamingResponse(
        runner.stream_agent(
            mental_health,
            data.get("user_id", "zahoor"),
            {"message": message, "history": _trim_chat_history(data.get("history", [])), "difficulty": difficulty},
            db,
            close_db=True,
        ),
        media_type="text/event-stream",
    )


@app.post("/api/chat/coach")
async def chat_coach(request: Request) -> StreamingResponse:
    """Coach SSE chat endpoint."""

    data = await request.json()
    message = str(data.get("message", ""))[-1200:]
    contextualized_message = _merge_chat_context(message, data.get("context", ""))
    if not _is_coach_question_in_scope(message):
        return StreamingResponse(
            _stream_static_sse(_coach_out_of_scope_message()),
            media_type="text/event-stream",
        )
    db = await get_db()
    difficulty = classify_difficulty(message)
    return StreamingResponse(
        runner.stream_agent(
            coach,
            data.get("user_id", "zahoor"),
            {"message": contextualized_message, "cache_key": message, "history": _trim_chat_history(data.get("history", [])), "difficulty": difficulty},
            db,
            close_db=True,
        ),
        media_type="text/event-stream",
    )

@app.get("/api/gamification/{user_id}")
async def gamification_summary(user_id: str) -> dict[str, Any]:
    """Get gamification summary."""

    db = await get_db()
    try:
        return await get_gamification_summary(user_id, db)
    finally:
        await db.close()


@app.post("/api/gamification/{user_id}/action")
async def gamification_action(user_id: str, request: Request) -> dict[str, Any]:
    """Log a gamification action."""

    data = await request.json()
    db = await get_db()
    try:
        return await process_action(user_id, data.get("action", ""), data.get("metadata"), db)
    finally:
        await db.close()


@app.get("/api/gamification/leaderboard")
async def gamification_leaderboard() -> list[dict[str, Any]]:
    """Get leaderboard data."""

    db = await get_db()
    try:
        return await get_leaderboard(db)
    finally:
        await db.close()


@app.post("/api/family")
async def create_family_endpoint(request: Request) -> dict[str, Any]:
    """Create a new family group."""

    data = await request.json()
    db = await get_db()
    try:
        return await create_family(data.get("name", "My Family"), data["created_by"], db)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing field: {exc}") from exc
    finally:
        await db.close()


@app.post("/api/family/join")
async def join_family_endpoint(request: Request) -> dict[str, Any]:
    """Join an existing family group."""

    data = await request.json()
    db = await get_db()
    try:
        return await join_family(data["join_code"], data["user_id"], data["relationship"], data.get("privacy_level", "summary"), db)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing field: {exc}") from exc
    finally:
        await db.close()


@app.get("/api/family/{family_id}")
async def get_family_endpoint(family_id: str) -> dict[str, Any]:
    """Get the family dashboard."""

    db = await get_db()
    try:
        return await get_family_dashboard(family_id, db)
    finally:
        await db.close()


@app.get("/api/reminders/{user_id}")
async def get_reminders_endpoint(user_id: str) -> list[dict[str, Any]]:
    """Get reminder data."""

    db = await get_db()
    try:
        return await check_reminders(user_id, db)
    finally:
        await db.close()


@app.post("/api/reminders/smart/{user_id}")
async def smart_reminders(user_id: str) -> list[dict[str, Any]]:
    """Generate smart contextual reminders for a user."""

    db = await get_db()
    try:
        profile = await get_profile_dict(user_id, db)
        if profile is None:
            raise HTTPException(status_code=404, detail="User not found")
        weather = await get_weather(user_id, db)
        water_ml = await get_water_today(user_id, db)
        return await generate_smart_reminders(user_id, profile, weather, water_ml, db)
    finally:
        await db.close()


@app.get("/api/data-freshness/{user_id}")
async def get_data_freshness_endpoint(user_id: str) -> list[dict[str, Any]]:
    """Return exact upload history and recommended refresh timing."""

    db = await get_db()
    try:
        return await get_data_freshness(user_id, db)
    finally:
        await db.close()


@app.get("/api/alerts/{user_id}")
async def get_alerts_endpoint(user_id: str) -> list[dict[str, Any]]:
    """Get health alerts."""

    db = await get_db()
    try:
        return await check_alerts(user_id, db)
    finally:
        await db.close()


@app.post("/api/alerts/{user_id}/notify-doctor")
async def notify_doctor_endpoint(user_id: str, request: Request) -> dict[str, Any]:
    """Send alert summary to the user's doctor."""

    data = await request.json()
    db = await get_db()
    try:
        alert_id = data.get("alert_id")
        alert_ids = [alert_id] if alert_id is not None else data.get("alert_ids", [])
        return await notify_doctor(user_id, data.get("doctor_email"), alert_ids, db)
    finally:
        await db.close()


@app.get("/api/specialists/{user_id}")
async def get_specialists_endpoint(user_id: str) -> list[dict[str, Any]]:
    """Get specialist recommendations."""

    db = await get_db()
    try:
        profile = await get_profile_dict(user_id, db)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return _enrich_specialist_recommendations(profile, check_specialists(profile))
    finally:
        await db.close()


@app.get("/api/workouts/{user_id}")
async def get_workouts_endpoint(user_id: str) -> list[dict[str, Any]]:
    """Get recent workouts."""

    db = await get_db()
    try:
        return await get_workouts(user_id, db)
    finally:
        await db.close()


@app.post("/api/workouts/{user_id}")
async def log_workout_endpoint(user_id: str, request: Request) -> dict[str, Any]:
    """Log a new workout."""

    data = await request.json()
    db = await get_db()
    try:
        result = await log_workout(user_id, data, db)
        if (data.get("duration_min") or 0) >= 30:
            await process_action(user_id, "exercise_goal", None, db)
        return result
    finally:
        await db.close()


@app.get("/api/workouts/{user_id}/summary")
async def workout_summary_endpoint(user_id: str) -> dict[str, Any]:
    """Get workout summary."""

    db = await get_db()
    try:
        return await get_workout_summary(user_id, db)
    finally:
        await db.close()


@app.get("/api/workouts/{user_id}/targets")
async def workout_targets_endpoint(user_id: str) -> dict[str, Any]:
    """Get profile-aware workout targets."""

    db = await get_db()
    try:
        return await get_workout_targets(user_id, db)
    finally:
        await db.close()


@app.get("/api/spotify/callback")
async def spotify_callback(code: str, state: str = "") -> dict[str, Any]:
    """Handle Spotify OAuth callback and sync data."""

    from backend.spotify import exchange_spotify_code, resolve_spotify_oauth_state, sync_spotify

    db = await get_db()
    try:
        try:
            user_id = resolve_spotify_oauth_state(state)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        access_token = exchange_spotify_code(code)
        result = await sync_spotify(user_id, access_token, db)
        return {"success": True, "user_id": user_id, "spotify_data": result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Spotify connection failed: {exc}") from exc
    finally:
        await db.close()


@app.get("/api/spotify/mood/{user_id}")
async def spotify_mood(user_id: str) -> dict[str, Any]:
    """Return the latest Spotify mood payload, or available=false when missing."""

    db = await get_db()
    try:
        row = await (
            await db.execute(
                """
                SELECT timestamp, avg_valence, avg_energy, avg_danceability, track_count, baseline_valence, flagged, flag_reason
                FROM spotify_history
                WHERE user_id=?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (user_id,),
            )
        ).fetchone()
        if row is None:
            return {"available": False}
        payload = dict(row)
        history_rows = await (
            await db.execute(
                """
                SELECT timestamp, avg_valence, avg_energy, avg_danceability
                FROM spotify_history
                WHERE user_id=?
                ORDER BY timestamp DESC
                LIMIT 7
                """,
                (user_id,),
            )
        ).fetchall()
        payload["available"] = True
        payload["emotion_class"] = classify_music_emotion(payload.get("avg_valence") or 0, payload.get("avg_energy") or 0, payload.get("avg_danceability") or 0.5)
        payload["history"] = [
            {
                **dict(item),
                "emotion_class": classify_music_emotion(item["avg_valence"] or 0, item["avg_energy"] or 0, item["avg_danceability"] or 0.5),
            }
            for item in history_rows
        ]
        return payload
    finally:
        await db.close()


@app.get("/api/spotify/status/{user_id}")
async def spotify_status(user_id: str) -> dict[str, Any]:
    """Return Spotify connection status for a user."""

    db = await get_db()
    try:
        token_row = await (
            await db.execute("SELECT updated_at FROM spotify_tokens WHERE user_id=?", (user_id,))
        ).fetchone()
        history_row = await (
            await db.execute(
                """
                SELECT timestamp, avg_valence, avg_energy, avg_danceability, track_count
                FROM spotify_history
                WHERE user_id=?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (user_id,),
            )
        ).fetchone()
        sync_history_rows = await (
            await db.execute(
                """
                SELECT timestamp, avg_valence, avg_energy, avg_danceability, track_count, flagged
                FROM spotify_history
                WHERE user_id=?
                ORDER BY timestamp DESC
                LIMIT 7
                """,
                (user_id,),
            )
        ).fetchall()
        recent_track_rows = await (
            await db.execute(
                """
                SELECT played_at, track_id, track_name, artist_names, album_name, album_image_url, preview_url, spotify_url, sync_timestamp
                FROM spotify_track_history
                WHERE user_id=?
                ORDER BY datetime(played_at) DESC
                LIMIT 12
                """,
                (user_id,),
            )
        ).fetchall()
        return {
            "connected": token_row is not None,
            "connected_at": token_row["updated_at"] if token_row else None,
            "latest_sync": dict(history_row) if history_row else None,
            "sync_history": [dict(row) for row in sync_history_rows],
            "recent_tracks": [dict(row) for row in recent_track_rows],
        }
    finally:
        await db.close()


@app.get("/api/research-features/{user_id}")
async def research_features(user_id: str) -> dict[str, Any]:
    """Return live evidence for the implemented research-paper features."""

    db = await get_db()
    try:
        react_rows = await (
            await db.execute(
                """
                SELECT timestamp, agent_name, difficulty, react_trace, response
                FROM agent_logs
                WHERE user_id=? AND action='completed' AND react_trace IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 8
                """,
                (user_id,),
            )
        ).fetchall()
        react_runs = []
        for row in react_rows:
            try:
                trace = json.loads(row["react_trace"] or "[]")
            except Exception:
                trace = []
            react_runs.append(
                {
                    "timestamp": row["timestamp"],
                    "agent_name": row["agent_name"],
                    "agent_label": _agent_label(row["agent_name"]),
                    "difficulty": row["difficulty"] or "unknown",
                    "step_count": len(trace),
                    "trace_preview": trace[:4],
                    "answer_preview": str(row["response"] or "")[:220],
                }
            )

        difficulty_rows = await (
            await db.execute(
                """
                SELECT timestamp, agent_name, difficulty
                FROM agent_logs
                WHERE user_id=? AND action='completed' AND difficulty IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 12
                """,
                (user_id,),
            )
        ).fetchall()
        difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}
        for row in difficulty_rows:
            level = str(row["difficulty"] or "").lower()
            if level in difficulty_counts:
                difficulty_counts[level] += 1

        cache_rows = await (
            await db.execute(
                """
                SELECT timestamp, agent_name, difficulty, response
                FROM agent_logs
                WHERE user_id=? AND action='cache_hit'
                ORDER BY timestamp DESC
                LIMIT 8
                """,
                (user_id,),
            )
        ).fetchall()

        reflection_rows = await (
            await db.execute(
                """
                SELECT created_at, agent_type, reflection, query_summary, is_active
                FROM reflections
                WHERE user_id=?
                ORDER BY created_at DESC
                LIMIT 8
                """,
                (user_id,),
            )
        ).fetchall()
        reflection_total_row = await (
            await db.execute(
                "SELECT COUNT(*) AS total, SUM(CASE WHEN is_active=1 THEN 1 ELSE 0 END) AS active FROM reflections WHERE user_id=?",
                (user_id,),
            )
        ).fetchone()

        spotify_latest = await (
            await db.execute(
                """
                SELECT timestamp, avg_valence, avg_energy, avg_danceability, track_count, flagged, flag_reason
                FROM spotify_history
                WHERE user_id=?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (user_id,),
            )
        ).fetchone()
        spotify_sync_rows = await (
            await db.execute(
                """
                SELECT timestamp, avg_valence, avg_energy, avg_danceability, track_count, flagged
                FROM spotify_history
                WHERE user_id=?
                ORDER BY timestamp DESC
                LIMIT 6
                """,
                (user_id,),
            )
        ).fetchall()
        spotify_track_rows = await (
            await db.execute(
                """
                SELECT played_at, track_name, artist_names, album_name, album_image_url, spotify_url
                FROM spotify_track_history
                WHERE user_id=?
                ORDER BY datetime(played_at) DESC
                LIMIT 8
                """,
                (user_id,),
            )
        ).fetchall()

        latest_spotify_payload = dict(spotify_latest) if spotify_latest else None
        if latest_spotify_payload:
            latest_spotify_payload["emotion_class"] = classify_music_emotion(
                latest_spotify_payload.get("avg_valence") or 0,
                latest_spotify_payload.get("avg_energy") or 0,
                latest_spotify_payload.get("avg_danceability") or 0.5,
            )

        return {
            "generated_at": _now_iso(),
            "features": {
                "react": {
                    "name": "ReAct",
                    "paper_label": "Reason + Act traces",
                    "enabled": True,
                    "how_used": "Chats stream hidden thought/action/observation steps while tools run behind the scenes.",
                    "where_used": ["Coach", "Mental Health", "Future Self"],
                    "last_used_at": react_runs[0]["timestamp"] if react_runs else None,
                    "total_recent_runs": len(react_runs),
                    "recent_runs": react_runs,
                },
                "daao": {
                    "name": "DAAO",
                    "paper_label": "Difficulty-aware adaptive orchestration",
                    "enabled": True,
                    "how_used": "Each incoming chat is classified as easy, medium, or hard, then the runner adjusts iteration budget accordingly.",
                    "where_used": ["Coach", "Mental Health", "Future Self"],
                    "last_used_at": difficulty_rows[0]["timestamp"] if difficulty_rows else None,
                    "difficulty_counts": difficulty_counts,
                    "recent_classifications": [
                        {
                            "timestamp": row["timestamp"],
                            "agent_name": row["agent_name"],
                            "agent_label": _agent_label(row["agent_name"]),
                            "difficulty": row["difficulty"],
                            "max_iterations": select_max_iterations(str(row["difficulty"] or "medium")),
                        }
                        for row in difficulty_rows
                    ],
                },
                "semantic_cache": {
                    "name": "Semantic Cache",
                    "paper_label": "Health-state-aware cache reuse",
                    "enabled": True,
                    "how_used": "If a new question is semantically close to a recent one and the user's health fingerprint matches, the cached answer is reused.",
                    "where_used": ["Coach", "Future Self", "Eligible lower-risk chats"],
                    "last_used_at": cache_rows[0]["timestamp"] if cache_rows else None,
                    "cache_hits": len(cache_rows),
                    "recent_hits": [
                        {
                            "timestamp": row["timestamp"],
                            "agent_name": row["agent_name"],
                            "agent_label": _agent_label(row["agent_name"]),
                            "difficulty": row["difficulty"] or "unknown",
                            "response_preview": str(row["response"] or "")[:220],
                        }
                        for row in cache_rows
                    ],
                },
                "reflexion": {
                    "name": "Reflexion",
                    "paper_label": "Post-run self-reflection memory",
                    "enabled": True,
                    "how_used": "After medium/hard runs, the system stores short lessons about what context it used or missed, then injects those into later prompts.",
                    "where_used": ["Coach", "Mental Health", "Future Self"],
                    "last_used_at": reflection_rows[0]["created_at"] if reflection_rows else None,
                    "active_reflections": int((reflection_total_row["active"] or 0) if reflection_total_row else 0),
                    "total_reflections": int((reflection_total_row["total"] or 0) if reflection_total_row else 0),
                    "recent_reflections": [
                        {
                            "created_at": row["created_at"],
                            "agent_type": row["agent_type"],
                            "agent_label": _agent_label(row["agent_type"]),
                            "reflection": row["reflection"],
                            "query_summary": row["query_summary"],
                            "is_active": bool(row["is_active"]),
                        }
                        for row in reflection_rows
                    ],
                },
                "music_emotion": {
                    "name": "Music Emotion Classification",
                    "paper_label": "Spotify valence/energy emotion inference",
                    "enabled": True,
                    "how_used": "Spotify listening history is converted into mood labels and fed into the mental-health layer and dashboard widgets.",
                    "where_used": ["Dashboard Spotify widget", "Mental-health context", "Settings Spotify proof"],
                    "last_used_at": latest_spotify_payload.get("timestamp") if latest_spotify_payload else None,
                    "latest_sync": latest_spotify_payload,
                    "recent_syncs": [
                        {
                            **dict(row),
                            "emotion_class": classify_music_emotion(
                                row["avg_valence"] or 0,
                                row["avg_energy"] or 0,
                                row["avg_danceability"] or 0.5,
                            ),
                        }
                        for row in spotify_sync_rows
                    ],
                    "recent_tracks": [dict(row) for row in spotify_track_rows],
                },
            },
        }
    finally:
        await db.close()


@app.get("/api/spotify/sync/{user_id}")
async def spotify_sync(user_id: str) -> dict[str, Any]:
    """Trigger Spotify sync or return auth URL."""

    from backend.spotify import SpotifySyncError, generate_spotify_oauth_state, sp_oauth, spotify_oauth_available, sync_spotify

    db = await get_db()
    try:
        row = await (await db.execute("SELECT access_token FROM spotify_tokens WHERE user_id=?", (user_id,))).fetchone()
        if row is None:
            if not spotify_oauth_available():
                return {
                    "success": False,
                    "needs_auth": False,
                    "available": False,
                    "message": "Spotify OAuth is not configured on this server yet.",
                }
            return {"needs_auth": True, "auth_url": sp_oauth.get_authorize_url(state=generate_spotify_oauth_state(user_id))}
        try:
            return {"success": True, "data": await sync_spotify(user_id, row["access_token"], db)}
        except SpotifySyncError as exc:
            if exc.needs_auth:
                await db.execute("DELETE FROM spotify_tokens WHERE user_id=?", (user_id,))
                await db.commit()
                if spotify_oauth_available():
                    return {
                        "success": False,
                        "needs_auth": True,
                        "auth_url": sp_oauth.get_authorize_url(state=generate_spotify_oauth_state(user_id)),
                        "message": str(exc),
                    }
            return {
                "success": False,
                "needs_auth": False,
                "available": spotify_oauth_available(),
                "message": str(exc),
            }
    finally:
        await db.close()


@app.post("/api/posture")
async def receive_posture(request: Request) -> dict[str, Any]:
    """Receive posture score updates from the standalone posture runner."""

    data = await request.json()
    user_id = data.get("user_id", "zahoor")
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO posture_history (user_id, score_pct, avg_angle, is_slouching) VALUES (?,?,?,?)",
            (user_id, data.get("score_pct", 100), data.get("avg_angle", 180), data.get("is_slouching", False)),
        )
        profile = await update_profile_fields(user_id, {"posture_score_pct": data.get("score_pct", 100)}, db)
        recent = await (
            await db.execute("SELECT score_pct FROM posture_history WHERE user_id=? ORDER BY timestamp DESC LIMIT 5", (user_id,))
        ).fetchall()
        average_recent = sum(float(row["score_pct"]) for row in recent) / max(len(recent), 1)
        return {"success": True, "score_pct": data.get("score_pct", 100), "avg_recent_5": round(average_recent, 1), "nudge": average_recent < 50, "profile": profile}
    finally:
        await db.close()


@app.post("/api/posture/analyze")
async def analyze_posture_endpoint(user_id: str = Form(...), file: UploadFile = File(...)) -> dict[str, Any]:
    """Analyze a webcam frame for posture, persist it, and return recent trend data."""

    try:
        image_bytes = await file.read()
        reading = analyze_posture_image(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    saved = await log_posture(user_id, reading)
    history = await get_posture_history(user_id, limit=12)
    history = list(reversed(history))
    average_score = round(sum(float(row.get("score_pct") or 0) for row in history) / max(len(history), 1), 1)
    latest = history[-1] if history else saved
    return {
        "success": True,
        "analysis": saved,
        "summary": {
            "latest_score_pct": latest.get("score_pct"),
            "latest_angle": latest.get("avg_angle"),
            "is_slouching": latest.get("is_slouching"),
            "average_score_pct": average_score,
            "samples": len(history),
        },
        "history": history,
    }


@app.get("/api/posture/{user_id}")
async def get_posture_endpoint(user_id: str) -> dict[str, Any]:
    """Return recent posture history and summary for a user."""

    history = await get_posture_history(user_id, limit=20)
    ordered = list(reversed(history))
    if not ordered:
        return {
            "summary": {"latest_score_pct": None, "latest_angle": None, "is_slouching": None, "average_score_pct": None, "samples": 0},
            "history": [],
        }
    average_score = round(sum(float(row.get("score_pct") or 0) for row in ordered) / len(ordered), 1)
    latest = ordered[-1]
    return {
        "summary": {
            "latest_score_pct": latest.get("score_pct"),
            "latest_angle": latest.get("avg_angle"),
            "is_slouching": latest.get("is_slouching"),
            "average_score_pct": average_score,
            "samples": len(ordered),
        },
        "history": ordered,
    }
