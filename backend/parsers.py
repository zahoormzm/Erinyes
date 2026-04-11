from __future__ import annotations

import base64
import json
import os
import re
import tempfile
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from backend.database import get_profile_dict

LAB_ALIASES: dict[str, list[str]] = {
    "ldl": ["ldl", "ldl cholesterol", "low density lipoprotein"],
    "hdl": ["hdl", "hdl cholesterol", "high density lipoprotein"],
    "triglycerides": ["triglycerides", "triglyceride"],
    "total_cholesterol": ["total cholesterol", "cholesterol total"],
    "vitamin_d": ["vitamin d", "25 oh vitamin d", "25-oh vitamin d", "25 hydroxy vitamin d"],
    "b12": ["vitamin b12", "b12", "cobalamin"],
    "tsh": ["tsh", "thyroid stimulating hormone"],
    "ferritin": ["ferritin", "iron stores"],
    "fasting_glucose": ["fasting glucose", "glucose fasting", "glucose"],
    "hba1c": ["hba1c", "hb a1c", "glycated hemoglobin", "hemoglobin a1c"],
    "hemoglobin": ["hemoglobin", "haemoglobin", "hb"],
    "creatinine": ["creatinine", "serum creatinine"],
    "sgpt_alt": ["sgpt", "alt", "alanine aminotransferase", "alanine transaminase"],
    "sgot_ast": ["sgot", "ast", "aspartate aminotransferase", "aspartate transaminase"],
}

COMMON_LAB_FIELDS: list[str] = [
    "ldl",
    "hdl",
    "triglycerides",
    "total_cholesterol",
    "fasting_glucose",
    "hba1c",
    "vitamin_d",
    "b12",
    "tsh",
    "ferritin",
    "hemoglobin",
    "creatinine",
    "sgpt_alt",
    "sgot_ast",
]

LAB_VALUE_RANGES: dict[str, tuple[float, float]] = {
    "ldl": (10, 500),
    "hdl": (10, 150),
    "triglycerides": (10, 2000),
    "total_cholesterol": (50, 600),
    "vitamin_d": (1, 200),
    "b12": (50, 5000),
    "tsh": (0.01, 100),
    "ferritin": (1, 5000),
    "fasting_glucose": (20, 700),
    "hba1c": (3, 20),
    "hemoglobin": (4, 25),
    "creatinine": (0.1, 20),
    "sgpt_alt": (1, 5000),
    "sgot_ast": (1, 5000),
}

CULTFIT_FIELDS: dict[str, list[str]] = {
    "weight_kg": ["weight", "body weight", "weight kg"],
    "bmi": ["bmi", "body mass index"],
    "bmr": ["bmr", "basal metabolic rate"],
    "body_fat_pct": ["body fat %", "body fat percentage", "fat percentage"],
    "visceral_fat_kg": ["visceral fat", "visceral fat mass"],
    "muscle_mass_kg": ["skeletal muscle", "muscle mass"],
    "body_water_pct": ["body water %", "total body water %"],
    "body_water_kg": ["total body water", "body water"],
    "protein_kg": ["protein mass", "protein"],
    "bone_mass_kg": ["bone mass"],
    "body_age_device": ["body age", "metabolic age"],
    "fat_mass_kg": ["fat mass"],
}


def _extract_json_blob(text: str) -> Any | None:
    text = (text or "").strip()
    if not text:
        return None
    candidates = [text]
    object_match = re.search(r"\{.*\}", text, re.DOTALL)
    array_match = re.search(r"\[.*\]", text, re.DOTALL)
    if object_match:
        candidates.append(object_match.group())
    if array_match:
        candidates.append(array_match.group())
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _normalize_lab_name(name: str) -> str | None:
    cleaned = re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()
    if not cleaned:
        return None
    for metric, aliases in LAB_ALIASES.items():
        if cleaned == metric:
            return metric
        if any(alias in cleaned for alias in aliases):
            return metric
    return None


def _extract_numeric_value(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group()) if match else None


def _is_plausible_lab_value(metric: str | None, value: float | None) -> bool:
    """Return True when a lab value is plausible enough to auto-apply."""

    if metric is None or value is None:
        return False
    bounds = LAB_VALUE_RANGES.get(metric)
    if bounds is None:
        return True
    low, high = bounds
    return low <= value <= high


def _flatten_dict_items(payload: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """Flatten nested dict/list payloads into key/value pairs."""

    items: list[tuple[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            compound = f"{prefix} {key}".strip()
            items.extend(_flatten_dict_items(value, compound))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            items.extend(_flatten_dict_items(value, f"{prefix} {index}".strip()))
    else:
        items.append((prefix.strip(), payload))
    return items


def _cultfit_line_value(text: str, aliases: list[str], unit_pattern: str = r"(?:kg|kcal|%|yrs?|year[s]?)?") -> float | None:
    """Extract a numeric value for a Cult.fit metric from OCR-like text."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    alias_patterns = [re.escape(alias).replace(r"\ ", r"\s+") for alias in aliases]
    for line in lines:
        normalized_line = re.sub(r"\s+", " ", line.lower())
        for alias in alias_patterns:
            forward = re.search(rf"{alias}[^\d\-]*(-?\d+(?:\.\d+)?)\s*{unit_pattern}", normalized_line, re.IGNORECASE)
            if forward:
                return float(forward.group(1))
            backward = re.search(rf"(-?\d+(?:\.\d+)?)\s*{unit_pattern}[^\n]*{alias}", normalized_line, re.IGNORECASE)
            if backward:
                return float(backward.group(1))
    return None


def _normalize_cultfit_payload(payload: Any, fallback_text: str = "") -> dict[str, Any]:
    """Normalize Cult.fit body-composition output from AI JSON or OCR-like text."""

    extracted: dict[str, float | None] = {field: None for field in CULTFIT_FIELDS}
    for key, value in _flatten_dict_items(payload):
        normalized_key = re.sub(r"[^a-z0-9]+", " ", key.lower()).strip()
        numeric_value = _extract_numeric_value(value)
        if numeric_value is None:
            continue
        for field, aliases in CULTFIT_FIELDS.items():
            if any(alias in normalized_key for alias in aliases):
                extracted[field] = numeric_value
                break

    if fallback_text:
        for field, aliases in CULTFIT_FIELDS.items():
            if extracted.get(field) is None:
                extracted[field] = _cultfit_line_value(fallback_text, aliases)

    weight = extracted.get("weight_kg")
    fat_mass = extracted.get("fat_mass_kg")
    water_mass = extracted.get("body_water_kg")
    if extracted.get("body_fat_pct") is None and weight and fat_mass:
        extracted["body_fat_pct"] = round((fat_mass / weight) * 100, 1)
    if extracted.get("body_water_pct") is None and weight and water_mass:
        extracted["body_water_pct"] = round((water_mass / weight) * 100, 1)

    profile_updates = {
        "weight_kg": extracted.get("weight_kg"),
        "bmi": extracted.get("bmi"),
        "bmr": extracted.get("bmr"),
        "body_fat_pct": extracted.get("body_fat_pct"),
        "visceral_fat_kg": extracted.get("visceral_fat_kg"),
        "muscle_mass_kg": extracted.get("muscle_mass_kg"),
        "body_water_pct": extracted.get("body_water_pct"),
        "protein_kg": extracted.get("protein_kg"),
        "bone_mass_kg": extracted.get("bone_mass_kg"),
        "body_age_device": extracted.get("body_age_device"),
    }
    return {key: value for key, value in profile_updates.items() if value is not None}


def _coerce_tests(payload: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metadata: dict[str, Any] = {}
    if isinstance(payload, dict):
        metadata = {key: value for key, value in payload.items() if key != "tests"}
        if isinstance(payload.get("tests"), list):
            return [item for item in payload["tests"] if isinstance(item, dict)], metadata
        rows: list[dict[str, Any]] = []
        for key, value in payload.items():
            if key == "tests":
                continue
            if isinstance(value, dict):
                row = {"name": value.get("name") or key, **value}
            else:
                row = {"name": key, "value": value}
            rows.append(row)
        return rows, metadata
    if isinstance(payload, list):
        return [item if isinstance(item, dict) else {"name": str(item), "value": None} for item in payload], metadata
    return [], metadata


def _fallback_extract_tests_from_text(text: str) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    seen: set[tuple[str, float | None]] = set()
    for line in [segment.strip() for segment in text.splitlines() if segment.strip()]:
        metric = _normalize_lab_name(line)
        value = _extract_numeric_value(line)
        if metric is None or value is None:
            continue
        key = (metric, value)
        if key in seen:
            continue
        seen.add(key)
        unit_match = re.search(r"(mg/dL|g/dL|ng/mL|pg/mL|mIU/L|U/L|IU/L|%)", line, re.IGNORECASE)
        tests.append(
            {
                "name": metric,
                "value": value,
                "unit": unit_match.group(1) if unit_match else None,
                "reference_range": None,
                "flag": None,
                "source": "fallback_text",
            }
        )
    return tests


def _normalize_lab_payload(payload: Any, fallback_text: str = "") -> dict[str, Any]:
    tests, metadata = _coerce_tests(payload)
    if not tests and fallback_text:
        tests = _fallback_extract_tests_from_text(fallback_text)
    normalized_tests: list[dict[str, Any]] = []
    recognized_fields: dict[str, float | str | None] = {}
    unmapped_tests: list[dict[str, Any]] = []
    invalid_tests: list[dict[str, Any]] = []
    ambiguous_tests: list[dict[str, Any]] = []
    metric_candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in tests:
        name = row.get("name") or row.get("test") or row.get("analyte") or row.get("marker") or "Unknown test"
        metric = _normalize_lab_name(str(name))
        value = _extract_numeric_value(row.get("value"))
        test_entry = {
            "name": str(name),
            "metric": metric,
            "value": value,
            "unit": row.get("unit") or row.get("units"),
            "reference_range": row.get("reference_range") or row.get("reference") or row.get("range"),
            "flag": row.get("flag") or row.get("status") or row.get("interpretation"),
        }
        normalized_tests.append(test_entry)
        if metric:
            if value is None:
                continue
            if not _is_plausible_lab_value(metric, value):
                invalid_tests.append({**test_entry, "validation": "out_of_range"})
                continue
            metric_candidates[metric].append(test_entry)
        else:
            unmapped_tests.append(test_entry)
    for metric, candidates in metric_candidates.items():
        distinct_values = sorted({round(float(candidate["value"]), 4) for candidate in candidates if candidate.get("value") is not None})
        if len(distinct_values) == 1:
            recognized_fields[metric] = distinct_values[0]
            continue
        ambiguous_tests.append(
            {
                "metric": metric,
                "label": metric.replace("_", " ").title(),
                "candidates": candidates,
            }
        )
    if normalized_tests:
        recognized_fields["last_blood_report_date"] = datetime.now().date().isoformat()
    missing_common_tests = [field for field in COMMON_LAB_FIELDS if field not in recognized_fields]
    return {
        "profile_updates": recognized_fields,
        "recognized_fields": {key: value for key, value in recognized_fields.items() if key != "last_blood_report_date"},
        "lab_tests": normalized_tests,
        "unmapped_tests": unmapped_tests,
        "invalid_tests": invalid_tests,
        "ambiguous_tests": ambiguous_tests,
        "missing_common_tests": missing_common_tests,
        "source_summary": {
            "tests_found": len(normalized_tests),
            "recognized_count": len([key for key in recognized_fields if key != "last_blood_report_date"]),
            "unmapped_count": len(unmapped_tests),
            "invalid_count": len(invalid_tests),
            "ambiguous_count": len(ambiguous_tests),
            "report_date": metadata.get("report_date") or metadata.get("collected_at"),
            "lab_name": metadata.get("lab_name") or metadata.get("laboratory"),
        },
    }


async def parse_blood_pdf(file_path: str, user_id: str, db: Any) -> dict:
    """Extract a flexible lab panel from a blood report PDF and normalize known metrics."""

    _ = user_id, db
    pdf_bytes = b""
    try:
        from backend.ai_router import ai_router

        with open(file_path, "rb") as handle:
            pdf_bytes = handle.read()
        b64 = base64.b64encode(pdf_bytes).decode()
        response = ai_router._call_claude(
            system=(
                "Extract every blood/lab test present in the uploaded report. "
                "Return strict JSON only with this shape: "
                "{\"tests\": [{\"name\": str, \"value\": number|null, \"unit\": str|null, "
                "\"reference_range\": str|null, \"flag\": str|null}], "
                "\"report_date\": str|null, \"lab_name\": str|null}. "
                "Do not invent tests that are not present. If the report is partial, return only the tests shown."
            ),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
                        {"type": "text", "text": "Extract all visible lab tests. Partial panels are valid. Include unknown tests in the tests array too."},
                    ],
                }
            ],
            tools=None,
            max_tokens=ai_router.extraction_max_tokens,
        )
        text = "".join(getattr(block, "text", "") for block in getattr(response, "content", []))
        payload = _extract_json_blob(text)
        if payload is not None:
            return _normalize_lab_payload(payload, fallback_text=pdf_bytes.decode("latin-1", errors="ignore"))
    except Exception:
        pass
    if not pdf_bytes and os.path.exists(file_path):
        with open(file_path, "rb") as handle:
            pdf_bytes = handle.read()
    return _normalize_lab_payload({}, fallback_text=pdf_bytes.decode("latin-1", errors="ignore"))


async def parse_cultfit_image(file_path: str, user_id: str, db: Any) -> dict:
    """Extract body composition from a Cult.fit image using Gemini or fallback."""

    _ = user_id, db
    fallback_text = ""
    try:
        from backend.ai_router import ai_router

        with open(file_path, "rb") as handle:
            image_bytes = handle.read()
        response = await ai_router.route(
            task="collector_cultfit",
            system=(
                "You are extracting values from a Cult.fit / smart-scale body composition report image. "
                "Return strict JSON only. Include any visible values you can read using this schema: "
                "{\"weight_kg\": number|null, \"bmi\": number|null, \"bmr\": number|null, "
                "\"body_fat_pct\": number|null, \"visceral_fat_kg\": number|null, "
                "\"muscle_mass_kg\": number|null, \"body_water_pct\": number|null, "
                "\"body_water_kg\": number|null, \"protein_kg\": number|null, "
                "\"fat_mass_kg\": number|null, \"bone_mass_kg\": number|null, "
                "\"body_age_device\": number|null}. "
                "Use skeletal muscle for muscle_mass_kg. If body fat percent is not visible, leave it null."
            ),
            messages=[{"role": "user", "content": "Read the full report image carefully and extract every visible body composition value into the requested JSON schema."}],
            image=image_bytes,
        )
        text = getattr(response, "text", "") or "".join(getattr(block, "text", "") for block in getattr(response, "content", []))
        fallback_text = text
        payload = _extract_json_blob(text)
        if payload is not None:
            normalized = _normalize_cultfit_payload(payload, fallback_text=text)
            if normalized:
                return normalized
    except Exception:
        pass
    return _normalize_cultfit_payload({}, fallback_text=fallback_text)


async def analyze_meal_photo(image_bytes: bytes, user_id: str, db: Any) -> dict:
    """Analyze a meal photo with Gemini identification and USDA grounding when possible."""

    from backend.formulas import nutrition_targets

    items = [{"item": "Detected meal", "portion_g": 300}]
    try:
        from backend.ai_router import ai_router

        response = await ai_router.route(
            task="collector_meal_photo",
            system="Identify visible foods and estimated portions as strict JSON array.",
            messages=[{"role": "user", "content": "Analyze this meal."}],
            image=image_bytes,
        )
        text = getattr(response, "text", "") or "".join(getattr(block, "text", "") for block in getattr(response, "content", []))
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            items = json.loads(match.group())
    except Exception:
        pass

    collapsed_items: list[dict[str, Any]] = []
    aggregated: dict[tuple[str, float], dict[str, Any]] = {}
    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        item_name = str(raw_item.get("item", "food") or "food").strip() or "food"
        normalized_name = " ".join(item_name.lower().split())
        try:
            portion_g = round(float(raw_item.get("portion_g", 100) or 100), 1)
        except (TypeError, ValueError):
            portion_g = 100.0
        key = (normalized_name, portion_g)
        if key not in aggregated:
            aggregated[key] = {"item": item_name, "portion_g": portion_g, "count": 1}
        else:
            aggregated[key]["count"] += 1
    for value in aggregated.values():
        merged = dict(value)
        if merged["count"] > 1:
            merged["portion_g"] = round(float(merged["portion_g"]) * int(merged["count"]), 1)
        collapsed_items.append(merged)
    items = collapsed_items or items

    total = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "sat_fat_g": 0.0, "fiber_g": 0.0}
    item_details: list[dict[str, Any]] = []
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            for item in items:
                item_name = item.get("item", "food")
                portion_g = float(item.get("portion_g", 100))
                cached = await (await db.execute("SELECT * FROM usda_foods WHERE description LIKE ? LIMIT 1", (f"%{item_name}%",))).fetchone()
                usda = dict(cached) if cached else None
                if usda is None:
                    resp = await client.get(
                        "https://api.nal.usda.gov/fdc/v1/foods/search",
                        params={"query": item_name, "api_key": os.getenv("USDA_API_KEY", "DEMO_KEY"), "pageSize": 1},
                        timeout=5,
                    )
                    foods = resp.json().get("foods", [])
                    if not foods:
                        continue
                    food = foods[0]
                    nutrients = {n["nutrientName"]: n.get("value", 0) for n in food.get("foodNutrients", [])}
                    usda = {
                        "fdc_id": food["fdcId"],
                        "description": food["description"],
                        "calories_per_100g": nutrients.get("Energy", 0),
                        "protein_per_100g": nutrients.get("Protein", 0),
                        "fat_per_100g": nutrients.get("Total lipid (fat)", 0),
                        "carbs_per_100g": nutrients.get("Carbohydrate, by difference", 0),
                        "sat_fat_per_100g": nutrients.get("Fatty acids, total saturated", 0),
                        "fiber_per_100g": nutrients.get("Fiber, total dietary", 0),
                    }
                    await db.execute(
                        "INSERT OR REPLACE INTO usda_foods (fdc_id, description, calories_per_100g, protein_per_100g, fat_per_100g, carbs_per_100g, sat_fat_per_100g, fiber_per_100g) VALUES (?,?,?,?,?,?,?,?)",
                        (usda["fdc_id"], usda["description"], usda["calories_per_100g"], usda["protein_per_100g"], usda["fat_per_100g"], usda["carbs_per_100g"], usda["sat_fat_per_100g"], usda["fiber_per_100g"]),
                    )
                    await db.commit()
                scale = portion_g / 100
                detail = {"item": item_name, "portion_g": portion_g, "usda_id": usda.get("fdc_id"), "usda_description": usda.get("description")}
                if item.get("count", 1) > 1:
                    detail["repeat_count"] = int(item["count"])
                mapping = [("calories", "calories_per_100g"), ("protein_g", "protein_per_100g"), ("fat_g", "fat_per_100g"), ("carbs_g", "carbs_per_100g"), ("sat_fat_g", "sat_fat_per_100g"), ("fiber_g", "fiber_per_100g")]
                for key, usda_key in mapping:
                    value = round(float(usda.get(usda_key, 0) or 0) * scale, 1)
                    detail[key] = value
                    total[key] = round(total[key] + value, 1)
                item_details.append(detail)
    except Exception:
        item_details = [{"item": "Detected meal", "portion_g": 300, "calories": 450, "protein_g": 18, "carbs_g": 55, "fat_g": 16, "sat_fat_g": 5, "fiber_g": 6, "usda_id": None, "usda_description": "Fallback estimate"}]
        total = {"calories": 450, "protein_g": 18, "carbs_g": 55, "fat_g": 16, "sat_fat_g": 5, "fiber_g": 6}
    profile = await get_profile_dict(user_id, db) or {}
    targets = nutrition_targets(profile)
    flags: list[str] = []
    if total["sat_fat_g"] > targets.get("sat_fat_g", 13):
        flags.append(f"Saturated fat {total['sat_fat_g']}g exceeds your {targets.get('sat_fat_g', 13)}g target.")
    if total["calories"] > targets.get("calories_per_meal", 700):
        flags.append("Calories are above your target for one meal.")
    if total["fiber_g"] < 5:
        flags.append("Fiber is low for this meal.")
    return {"items": item_details, "total": total, "flags": flags, "grounding": "USDA FoodData Central"}


def parse_apple_health_xml(file_path: str) -> dict:
    """Parse Apple Health export.xml using streaming iterparse."""

    import xml.etree.ElementTree as et

    result: dict[str, Any] = {
        "resting_hr": None,
        "hrv_ms": None,
        "steps_avg_7d": None,
        "active_energy_kcal": None,
        "exercise_min": None,
        "vo2max": None,
        "respiratory_rate": None,
        "walking_asymmetry_pct": None,
        "flights_climbed": None,
        "blood_oxygen_pct": None,
        "sleep_hours": None,
        "workouts_7d": [],
    }
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    metrics: dict[str, list[float]] = defaultdict(list)
    sleep_samples: list[dict[str, Any]] = []
    workouts: list[dict[str, Any]] = []
    type_map = {
        "HKQuantityTypeIdentifierRestingHeartRate": "resting_hr",
        "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "hrv_ms",
        "HKQuantityTypeIdentifierStepCount": "steps",
        "HKQuantityTypeIdentifierActiveEnergyBurned": "active_energy_kcal",
        "HKQuantityTypeIdentifierAppleExerciseTime": "exercise_min",
        "HKQuantityTypeIdentifierVO2Max": "vo2max",
        "HKQuantityTypeIdentifierRespiratoryRate": "respiratory_rate",
        "HKQuantityTypeIdentifierWalkingAsymmetryPercentage": "walking_asymmetry_pct",
        "HKQuantityTypeIdentifierFlightsClimbed": "flights_climbed",
        "HKQuantityTypeIdentifierOxygenSaturation": "blood_oxygen_pct",
    }
    def normalize_record_value(record_type: str, raw_value: str) -> float | None:
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            return None
        if record_type == "HKQuantityTypeIdentifierOxygenSaturation":
            if 0 < value <= 1:
                value *= 100
            if value < 50 or value > 100:
                return None
        return value
    try:
        iterator = et.iterparse(file_path, events=("end",))
    except (FileNotFoundError, et.ParseError, OSError):
        return result
    try:
        for _, elem in iterator:
            if elem.tag == "Record":
                try:
                    start_dt = datetime.strptime((elem.get("startDate", "") or "")[:19], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    elem.clear()
                    continue
                if start_dt < week_ago:
                    elem.clear()
                    continue
                record_type = elem.get("type", "")
                if record_type in type_map:
                    normalized = normalize_record_value(record_type, elem.get("value", "0"))
                    if normalized is not None:
                        metrics[type_map[record_type]].append(normalized)
                if record_type == "HKCategoryTypeIdentifierSleepAnalysis":
                    sleep_samples.append({"startDate": elem.get("startDate", ""), "endDate": elem.get("endDate", ""), "value": elem.get("value", "")})
                elem.clear()
            elif elem.tag == "Workout":
                try:
                    start_dt = datetime.strptime((elem.get("startDate", "") or "")[:19], "%Y-%m-%d %H:%M:%S")
                    if start_dt >= week_ago:
                        workouts.append({"type": (elem.get("workoutActivityType", "") or "").replace("HKWorkoutActivityType", ""), "duration_min": round(float(elem.get("duration", 0))), "calories": round(float(elem.get("totalEnergyBurned", 0))), "date": start_dt.strftime("%Y-%m-%d")})
                except ValueError:
                    pass
                elem.clear()
    except et.ParseError:
        return result
    for key, values in metrics.items():
        if key in {"steps", "active_energy_kcal", "exercise_min", "flights_climbed"}:
            result[f"{key if key != 'steps' else 'steps'}_avg_7d"] = round(sum(values) / 7) if values else None
        else:
            result[key] = round(sum(values) / len(values), 1) if values else None
    total_sleep_seconds = 0.0
    sleep_nights = 0
    seen_dates: set[str] = set()
    for sample in sleep_samples:
        if "Asleep" not in sample.get("value", "") and "InBed" not in sample.get("value", ""):
            continue
        try:
            start_dt = datetime.strptime(sample["startDate"][:19], "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(sample["endDate"][:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        duration = (end_dt - start_dt).total_seconds()
        if duration > 0:
            total_sleep_seconds += duration
            date_key = start_dt.strftime("%Y-%m-%d")
            if date_key not in seen_dates:
                seen_dates.add(date_key)
                sleep_nights += 1
    result["sleep_hours"] = round(total_sleep_seconds / max(sleep_nights, 1) / 3600, 1) if sleep_nights else None
    if workouts:
        workout_minutes = sum(float(workout.get("duration_min") or 0) for workout in workouts)
        workout_calories = sum(float(workout.get("calories") or 0) for workout in workouts)
        if result["exercise_min"] is None:
            result["exercise_min"] = round(workout_minutes / 7)
        else:
            result["exercise_min"] = round(max(float(result["exercise_min"]), workout_minutes / 7))
        if result["active_energy_kcal"] is None:
            result["active_energy_kcal"] = round(workout_calories / 7, 1)
    result["workouts_7d"] = workouts
    return result


def parse_apple_health_file(file_path: str) -> dict:
    """Parse either an Apple Health export.xml file or a shared export zip."""

    lower_path = file_path.lower()
    if lower_path.endswith(".zip"):
        with zipfile.ZipFile(file_path, "r") as archive:
            candidates = [
                name for name in archive.namelist()
                if os.path.basename(name).lower() == "export.xml"
            ]
            if not candidates:
                raise ValueError("Apple Health zip does not contain export.xml")
            with archive.open(candidates[0]) as source, tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
                tmp.write(source.read())
                tmp_path = tmp.name
        try:
            return parse_apple_health_xml(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    return parse_apple_health_xml(file_path)
