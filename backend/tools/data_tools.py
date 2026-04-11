from __future__ import annotations

from typing import Any

from backend.database import update_profile_fields

REFERENCE_RANGES: dict[str, dict[str, Any]] = {
    "ldl": {"normal_low": 0, "normal_high": 100, "critical": 190, "unit": "mg/dL"},
    "hdl": {"normal_low": 40, "normal_high": 60, "critical_low": 35, "unit": "mg/dL"},
    "triglycerides": {"normal_low": 0, "normal_high": 150, "critical": 500, "unit": "mg/dL"},
    "total_cholesterol": {"normal_low": 0, "normal_high": 200, "critical": 300, "unit": "mg/dL"},
    "vitamin_d": {"normal_low": 30, "normal_high": 100, "critical_low": 10, "unit": "ng/mL"},
    "b12": {"normal_low": 300, "normal_high": 900, "critical_low": 200, "unit": "pg/mL"},
    "tsh": {"normal_low": 0.4, "normal_high": 4.0, "critical": 20, "unit": "mIU/L"},
    "ferritin": {"normal_low": 30, "normal_high": 300, "critical_low": 12, "unit": "ng/mL"},
    "fasting_glucose": {"normal_low": 70, "normal_high": 100, "critical": 200, "unit": "mg/dL"},
    "hba1c": {"normal_low": 4.0, "normal_high": 5.7, "critical": 9.0, "unit": "%"},
    "hemoglobin": {"normal_low": 12, "normal_high": 17, "critical_low": 7, "unit": "g/dL"},
    "creatinine": {"normal_low": 0.6, "normal_high": 1.2, "critical": 4.0, "unit": "mg/dL"},
    "sgpt_alt": {"normal_low": 0, "normal_high": 40, "critical": 200, "unit": "U/L"},
    "sgot_ast": {"normal_low": 0, "normal_high": 40, "critical": 200, "unit": "U/L"},
    "resting_hr": {"normal_low": 50, "normal_high": 85, "critical": 120, "critical_low": 40, "unit": "bpm"},
    "blood_pressure_systolic": {"normal_low": 90, "normal_high": 120, "critical": 180, "critical_low": 80, "unit": "mmHg"},
    "blood_pressure_diastolic": {"normal_low": 60, "normal_high": 80, "critical": 120, "critical_low": 50, "unit": "mmHg"},
    "hrv_ms": {"normal_low": 30, "normal_high": 100, "critical_low": 15, "unit": "ms"},
    "bmi": {"normal_low": 18.5, "normal_high": 25, "critical": 40, "unit": "kg/m²"},
    "body_fat_pct": {"normal_low": 8, "normal_high": 20, "critical": 35, "unit": "%"},
    "vo2max": {"normal_low": 35, "normal_high": 60, "critical_low": 20, "unit": "mL/kg/min"},
}


async def parse_blood_pdf(user_id: str, db: Any, file_path: str = "", **kwargs: Any) -> dict:
    """Extract lab values from a blood report PDF."""

    _ = kwargs
    from backend.parsers import parse_blood_pdf as parser

    return await parser(file_path, user_id, db)


async def parse_cultfit_image(user_id: str, db: Any, file_path: str = "", **kwargs: Any) -> dict:
    """Extract body composition from a Cult.fit screenshot."""

    _ = kwargs
    from backend.parsers import parse_cultfit_image as parser

    return await parser(file_path, user_id, db)


async def parse_apple_health_xml(user_id: str, db: Any, file_path: str = "", **kwargs: Any) -> dict:
    """Extract health metrics from Apple Health export.xml."""

    _ = kwargs
    from backend.parsers import parse_apple_health_xml as parser

    return parser(file_path)


async def validate_ranges(user_id: str, db: Any, values: dict | None = None, **kwargs: Any) -> dict:
    """Validate health values against medical reference ranges."""

    _ = user_id, db, kwargs
    results: dict[str, Any] = {}
    for key, value in (values or {}).items():
        if value is None:
            results[key] = {"value": None, "status": "missing", "range": None, "unit": None}
            continue
        ref = REFERENCE_RANGES.get(key)
        if ref is None:
            results[key] = {"value": value, "status": "unknown", "range": None, "unit": None}
            continue
        status = "normal"
        if "critical" in ref and value >= ref["critical"]:
            status = "critical_high"
        elif "critical_low" in ref and value <= ref["critical_low"]:
            status = "critical_low"
        elif value > ref["normal_high"]:
            status = "high"
        elif value < ref["normal_low"]:
            status = "low"
        results[key] = {"value": value, "status": status, "range": f"{ref['normal_low']}-{ref['normal_high']} {ref['unit']}", "unit": ref["unit"]}
    anomaly_count = sum(1 for item in results.values() if item["status"] in {"high", "low", "critical_high", "critical_low"})
    return {"validations": results, "anomaly_count": anomaly_count}


async def update_profile(user_id: str, db: Any, updates: dict | None = None, **kwargs: Any) -> dict:
    """Update a user's health profile with new values."""

    _ = kwargs
    await update_profile_fields(user_id, updates or {}, db)
    return {"success": True, "updated_fields": list((updates or {}).keys()), "message": f"Updated {len(updates or {})} fields for user {user_id}"}
