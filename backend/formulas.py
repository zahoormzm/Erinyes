from __future__ import annotations

from copy import deepcopy
from typing import Any

OVERALL_WEIGHTS: dict[str, float] = {
    "cv": 0.30,
    "met": 0.25,
    "msk": 0.20,
    "neuro": 0.25,
}

DELTA_LIMITS: dict[str, tuple[float, float]] = {
    "cv": (-8.0, 8.0),
    "met": (-8.0, 8.0),
    "msk": (-6.0, 6.0),
    "neuro": (-6.0, 6.0),
}

SCENARIO_DURATION_FACTORS: dict[str, tuple[str, float]] = {
    "1w": ("1 week", 0.35),
    "1m": ("1 month", 0.7),
    "3m": ("3 months", 1.0),
    "6m": ("6 months", 1.35),
}


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a floating-point value to the provided range."""

    return max(low, min(high, value))


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    """Return a ratio when both values exist and denominator is non-zero."""

    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _num(value: Any, default: float = 0.0) -> float:
    """Convert nullable or loosely typed numeric values into safe floats."""

    if value in (None, ""):
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _positive_num(value: Any, default: float) -> float:
    """Return a positive numeric value or a safe default."""

    numeric = _num(value, default)
    return numeric if numeric > 0 else float(default)


def _diet_quality_delta(profile: dict[str, Any], *, metabolic: bool = False, neurological: bool = False) -> float:
    """Return diet-quality adjustments for metabolic or neurological scoring."""

    quality = str(profile.get("diet_quality") or "average").strip().lower()
    if metabolic:
        return {
            "poor": 1.0,
            "average": 0.0,
            "good": -0.5,
            "excellent": -1.0,
        }.get(quality, 0.0)
    if neurological:
        return {
            "poor": 0.6,
            "average": 0.0,
            "good": -0.3,
            "excellent": -0.6,
        }.get(quality, 0.0)
    return 0.0


def _scenario_duration_meta(duration_key: Any) -> tuple[str, float]:
    """Return a display label and scaling factor for simulation duration."""

    normalized = str(duration_key or "3m").strip().lower()
    return SCENARIO_DURATION_FACTORS.get(normalized, SCENARIO_DURATION_FACTORS["3m"])


def _build_component(input_name: str, value: Any, delta: float, reasoning: str) -> dict[str, Any]:
    """Build a formula component row."""

    return {
        "input": input_name,
        "value": value,
        "delta": round(delta, 2),
        "reasoning": reasoning,
    }


def _finalize_delta(components: list[dict[str, Any]], bucket: str) -> dict[str, Any]:
    """Clamp and package a subsystem delta with component detail."""

    total = round(sum(component["delta"] for component in components), 2)
    low, high = DELTA_LIMITS[bucket]
    clamped_total = _clamp(total, low, high)
    return {
        "total": round(clamped_total, 2),
        "raw_total": total,
        "components": components,
        "limits": {"low": low, "high": high},
    }


def _delta_total(delta: dict[str, Any] | float) -> float:
    """Return the numeric total from a detailed delta payload."""

    if isinstance(delta, dict):
        return float(delta.get("total", 0.0) or 0.0)
    return float(delta or 0.0)


def _build_bio_age_from_deltas(chrono: float, cv: float, met: float, msk: float, neuro: float) -> dict[str, Any]:
    """Build a bio-age payload from already-computed subsystem deltas."""

    overall = chrono + (
        OVERALL_WEIGHTS["cv"] * cv
        + OVERALL_WEIGHTS["met"] * met
        + OVERALL_WEIGHTS["msk"] * msk
        + OVERALL_WEIGHTS["neuro"] * neuro
    )
    result = {
        "overall": round(overall, 1),
        "cardiovascular": round(chrono + cv, 1),
        "metabolic": round(chrono + met, 1),
        "musculoskeletal": round(chrono + msk, 1),
        "neurological": round(chrono + neuro, 1),
        "deltas": {
            "cv": round(cv, 2),
            "met": round(met, 2),
            "msk": round(msk, 2),
            "neuro": round(neuro, 2),
        },
    }
    result["overall_bio_age"] = result["overall"]
    result["sub_ages"] = {
        "cardiovascular": result["cardiovascular"],
        "metabolic": result["metabolic"],
        "musculoskeletal": result["musculoskeletal"],
        "neurological": result["neurological"],
    }
    result["delta"] = round(result["overall"] - chrono, 1)
    return result


def cardiovascular_delta(profile: dict[str, Any]) -> dict[str, Any]:
    """Calculate cardiovascular age delta from profile data."""

    components: list[dict[str, Any]] = []
    hdl = profile.get("hdl")
    if hdl is not None:
        delta = 1.5 if hdl < 40 else -1.5 if hdl >= 60 else 0.0
        components.append(_build_component("HDL", hdl, delta, "HDL < 40 raises cardiovascular age; HDL >= 60 is protective." if delta else "HDL is in the neutral range."))
    ldl = profile.get("ldl")
    if ldl is not None:
        delta = -1.0 if ldl < 100 else 0.0 if ldl < 130 else 1.0 if ldl < 160 else 2.0
        components.append(_build_component("LDL", ldl, delta, "LDL below 100 is protective; LDL above 130 adds age burden." if delta else "LDL is in the neutral range."))
    triglycerides = profile.get("triglycerides")
    if triglycerides is not None:
        delta = 0.0 if triglycerides < 150 else 0.5 if triglycerides < 200 else 1.5
        components.append(_build_component("Triglycerides", triglycerides, delta, "Triglycerides above 150 increase cardiovascular strain." if delta else "Triglycerides are in range."))
    resting_hr = profile.get("resting_hr")
    if resting_hr is not None:
        delta = -1.0 if resting_hr < 60 else 0.0 if resting_hr <= 72 else 0.5 if resting_hr <= 84 else 1.5
        components.append(_build_component("Resting HR", resting_hr, delta, "Lower resting HR reflects better conditioning; elevated resting HR adds age burden." if delta else "Resting HR is neutral."))
    hrv_ms = profile.get("hrv_ms")
    if hrv_ms is not None:
        delta = -1.0 if hrv_ms >= 50 else 0.0 if hrv_ms >= 30 else 1.5
        components.append(_build_component("HRV", hrv_ms, delta, "Higher HRV is protective; HRV below 30 suggests poor recovery." if delta else "HRV is neutral."))
    vo2max = profile.get("vo2max")
    if vo2max is not None:
        delta = -1.5 if vo2max >= 45 else -0.5 if vo2max >= 35 else 0.5 if vo2max >= 25 else 1.5
        components.append(_build_component("VO2max", vo2max, delta, "Higher VO2max lowers cardiovascular age; low VO2max adds risk." if delta else "VO2max is neutral."))
    steps_avg = profile.get("steps_avg_7d")
    if steps_avg is not None:
        delta = -1.0 if steps_avg >= 10000 else -0.5 if steps_avg >= 7500 else 0.0 if steps_avg >= 5000 else 1.0
        components.append(_build_component("Steps (7d avg)", steps_avg, delta, "Higher step counts improve cardiovascular resilience." if delta else "Step volume is neutral."))
    exercise_min = profile.get("exercise_min")
    if exercise_min is not None:
        delta = -1.0 if exercise_min >= 45 else -0.5 if exercise_min >= 30 else 0.0 if exercise_min >= 15 else 1.0
        components.append(_build_component("Exercise Minutes", exercise_min, delta, "More daily exercise lowers cardiovascular age." if delta else "Exercise minutes are neutral."))
    systolic = profile.get("blood_pressure_systolic")
    if systolic is not None:
        delta = -0.5 if systolic < 120 else 0.0 if systolic < 130 else 1.0 if systolic < 140 else 2.0
        components.append(_build_component("Systolic BP", systolic, delta, "Higher blood pressure increases cardiovascular age." if delta else "Blood pressure is neutral."))
    return _finalize_delta(components, "cv")


def metabolic_delta(profile: dict[str, Any]) -> dict[str, Any]:
    """Calculate metabolic age delta from profile data."""

    components: list[dict[str, Any]] = []
    bmi = profile.get("bmi")
    if bmi is not None:
        if bmi < 18.5:
            delta = 0.5
        elif bmi < 23:
            delta = -0.5
        elif bmi < 25:
            delta = 0.0
        elif bmi < 30:
            delta = 1.0
        else:
            delta = 2.0
        components.append(_build_component("BMI", bmi, delta, "BMI in the 18.5-23 range is most favorable for metabolic age." if delta else "BMI is neutral."))
    visceral_fat = profile.get("visceral_fat_kg")
    if visceral_fat is not None:
        delta = -0.5 if visceral_fat < 1 else 0.0 if visceral_fat <= 2 else 1.5
        components.append(_build_component("Visceral Fat", visceral_fat, delta, "Higher visceral fat increases metabolic age." if delta else "Visceral fat is neutral."))
    fasting_glucose = profile.get("fasting_glucose")
    if fasting_glucose is not None:
        delta = -0.5 if fasting_glucose < 85 else 0.0 if fasting_glucose < 100 else 1.5 if fasting_glucose < 126 else 3.0
        components.append(_build_component("Fasting Glucose", fasting_glucose, delta, "Elevated fasting glucose increases metabolic age." if delta else "Fasting glucose is neutral."))
    hba1c = profile.get("hba1c")
    if hba1c is not None:
        delta = -0.5 if hba1c < 5.4 else 0.0 if hba1c < 5.7 else 1.5 if hba1c < 6.5 else 3.0
        components.append(_build_component("HbA1c", hba1c, delta, "HbA1c above 5.7 raises metabolic age." if delta else "HbA1c is neutral."))
    vitamin_d = profile.get("vitamin_d")
    if vitamin_d is not None:
        delta = -0.5 if vitamin_d >= 30 else 0.0 if vitamin_d >= 20 else 1.5
        components.append(_build_component("Vitamin D", vitamin_d, delta, "Vitamin D deficiency raises metabolic age." if delta else "Vitamin D is neutral."))
    b12 = profile.get("b12")
    if b12 is not None:
        delta = -0.5 if b12 >= 300 else 0.0 if b12 >= 200 else 1.0
        components.append(_build_component("B12", b12, delta, "Low B12 adds metabolic strain." if delta else "B12 is neutral."))
    tsh = profile.get("tsh")
    if tsh is not None:
        delta = 0.0 if 0.5 <= tsh <= 4.0 else 1.0
        components.append(_build_component("TSH", tsh, delta, "TSH outside the reference band adds metabolic burden." if delta else "TSH is neutral."))
    weight = profile.get("weight_kg")
    height = profile.get("height_cm")
    age = profile.get("age")
    sex = (profile.get("sex") or "").lower()
    bmr = profile.get("bmr")
    if all(value is not None for value in (weight, height, age, bmr)) and sex in {"male", "female"}:
        expected = 10 * float(weight) + 6.25 * float(height) - 5 * int(age) + (5 if sex == "male" else -161)
        if bmr > expected * 1.05:
            delta = -0.5
        elif bmr < expected * 0.95:
            delta = 0.5
        else:
            delta = 0.0
        components.append(_build_component("BMR vs expected", round(float(bmr), 1), delta, "Measured BMR below expected can suggest lower metabolic resilience." if delta else "BMR is close to expected."))
    diet_delta = _diet_quality_delta(profile, metabolic=True)
    components.append(_build_component("Diet Quality", profile.get("diet_quality") or "average", diet_delta, "Diet quality materially shifts metabolic age." if diet_delta else "Diet quality is neutral."))
    return _finalize_delta(components, "met")


def musculoskeletal_delta(profile: dict[str, Any]) -> dict[str, Any]:
    """Calculate musculoskeletal age delta from profile data."""

    components: list[dict[str, Any]] = []
    sex = (profile.get("sex") or "").lower()
    muscle_ratio = _safe_ratio(profile.get("muscle_mass_kg"), profile.get("weight_kg"))
    if muscle_ratio is not None and sex in {"male", "female"}:
        if sex == "male":
            delta = -1.0 if muscle_ratio >= 0.40 else 0.0 if muscle_ratio >= 0.35 else 1.5
        else:
            delta = -1.0 if muscle_ratio >= 0.32 else 0.0 if muscle_ratio >= 0.28 else 1.5
        components.append(_build_component("Muscle Ratio", round(muscle_ratio, 3), delta, "Higher muscle ratio lowers musculoskeletal age." if delta else "Muscle ratio is neutral."))
    bone_mass = profile.get("bone_mass_kg")
    if bone_mass is not None and sex in {"male", "female"}:
        if sex == "male":
            delta = -0.5 if bone_mass >= 3.0 else 1.0 if bone_mass < 2.5 else 0.0
        else:
            delta = -0.5 if bone_mass >= 2.5 else 1.0 if bone_mass < 2.0 else 0.0
        components.append(_build_component("Bone Mass", bone_mass, delta, "Lower bone mass increases musculoskeletal age." if delta else "Bone mass is neutral."))
    posture_score = profile.get("posture_score_pct")
    if posture_score is not None:
        delta = -1.0 if posture_score >= 80 else 0.0 if posture_score >= 60 else 1.5
        components.append(_build_component("Posture Score", posture_score, delta, "Strong posture lowers musculoskeletal age." if delta else "Posture score is neutral."))
    asymmetry = profile.get("walking_asymmetry_pct")
    if asymmetry is not None:
        delta = -0.5 if asymmetry < 3 else 0.0 if asymmetry <= 5 else 1.0
        components.append(_build_component("Walking Asymmetry", asymmetry, delta, "Higher gait asymmetry raises musculoskeletal age." if delta else "Walking asymmetry is neutral."))
    return _finalize_delta(components, "msk")


def neurological_delta(profile: dict[str, Any]) -> dict[str, Any]:
    """Calculate neurological age delta from profile data."""

    components: list[dict[str, Any]] = []
    sleep = profile.get("sleep_hours")
    if sleep is not None:
        delta = -1.0 if 7 <= sleep <= 9 else 0.0 if sleep >= 6 else 1.5 if sleep < 6 else 0.5
        components.append(_build_component("Sleep Hours", sleep, delta, "7-9 hours is most protective neurologically." if delta else "Sleep duration is neutral."))
    deep_sleep = profile.get("sleep_deep_pct")
    if deep_sleep is not None:
        delta = -0.5 if deep_sleep >= 20 else 0.0 if deep_sleep >= 13 else 1.0
        components.append(_build_component("Deep Sleep %", deep_sleep, delta, "Lower deep sleep reduces neurological recovery." if delta else "Deep sleep is neutral."))
    phq9 = profile.get("phq9_score")
    if phq9 is not None:
        if phq9 <= 4:
            delta = -0.5
        elif phq9 <= 9:
            delta = 0.0
        elif phq9 <= 14:
            delta = 1.0
        elif phq9 <= 19:
            delta = 2.0
        else:
            delta = 3.0
        components.append(_build_component("PHQ-9", phq9, delta, "Higher PHQ-9 scores raise neurological age." if delta else "PHQ-9 is neutral."))
    stress = profile.get("stress_level")
    if stress is not None:
        delta = -0.5 if stress <= 3 else 0.0 if stress <= 6 else 1.0 if stress <= 8 else 2.0
        components.append(_build_component("Stress Level", stress, delta, "Higher stress increases neurological age." if delta else "Stress is neutral."))
    screen = profile.get("screen_time_hours")
    if screen is not None:
        delta = -0.5 if screen < 4 else 0.0 if screen <= 8 else 0.5 if screen <= 12 else 1.0
        components.append(_build_component("Screen Time", screen, delta, "Higher screen time slightly increases neurological age." if delta else "Screen time is neutral."))
    exam_stress = profile.get("exam_stress")
    if exam_stress is not None:
        delta = 0.0 if exam_stress <= 3 else 0.3 if exam_stress <= 6 else 0.7 if exam_stress <= 8 else 1.5
        components.append(_build_component("Exam Stress", exam_stress, delta, "Academic stress contributes to neurological age." if delta else "Exam stress is neutral."))
    study_hours = profile.get("study_hours_daily")
    if study_hours is not None:
        delta = 0.0 if study_hours <= 6 else 0.3 if study_hours <= 10 else 1.0
        components.append(_build_component("Study Hours", study_hours, delta, "Long study hours increase recovery load." if delta else "Study hours are neutral."))
    diet_delta = _diet_quality_delta(profile, neurological=True)
    components.append(_build_component("Diet Quality", profile.get("diet_quality") or "average", diet_delta, "Diet quality affects neurological resilience." if diet_delta else "Diet quality is neutral."))
    return _finalize_delta(components, "neuro")


def _calculate_bio_age_base(profile: dict[str, Any]) -> dict[str, Any]:
    """Calculate biological age values without secondary ranking lookups."""

    chrono = profile.get("age", profile.get("chronological_age", 25)) or 25
    cv = cardiovascular_delta(profile)
    met = metabolic_delta(profile)
    msk = musculoskeletal_delta(profile)
    neuro = neurological_delta(profile)
    result = _build_bio_age_from_deltas(
        float(chrono),
        _delta_total(cv),
        _delta_total(met),
        _delta_total(msk),
        _delta_total(neuro),
    )
    result["delta_breakdowns"] = {"cv": cv, "met": met, "msk": msk, "neuro": neuro}
    return result


def calculate_bio_age(profile: dict[str, Any]) -> dict[str, Any]:
    """Calculate biological age from health profile data."""

    result = _calculate_bio_age_base(profile)
    result["contributing_factors"] = rank_impact(profile)["top_changes"]
    return result


def project_risk(profile: dict[str, Any], years: int = 15) -> list[dict[str, Any]]:
    """Project health risks over future years using biomarker-based multipliers."""

    diabetes_base = 0.002
    cvd_base = 0.001
    metabolic_base = 0.002
    mental_base = 0.003
    fasting_glucose = _num(profile.get("fasting_glucose"))
    hba1c = _num(profile.get("hba1c"))
    bmi = _num(profile.get("bmi"))
    exercise_hours_week = _num(profile.get("exercise_hours_week"))
    ldl = _num(profile.get("ldl"))
    blood_pressure_systolic = _num(profile.get("blood_pressure_systolic"))
    hdl = _num(profile.get("hdl"), 999)
    visceral_fat_kg = _num(profile.get("visceral_fat_kg"))
    triglycerides = _num(profile.get("triglycerides"))
    phq9_score = _num(profile.get("phq9_score"))
    sleep_hours = _num(profile.get("sleep_hours"), 8)
    stress_level = _num(profile.get("stress_level"))
    screen_time_hours = _num(profile.get("screen_time_hours"))
    vitamin_d = _num(profile.get("vitamin_d"), 30)
    exam_stress = _num(profile.get("exam_stress"))
    study_hours_daily = _num(profile.get("study_hours_daily"))
    diet_quality = str(profile.get("diet_quality") or "average").strip().lower()
    diabetes_mult = 1.0
    if fasting_glucose > 100:
        diabetes_mult *= 2.5
    if hba1c > 5.7:
        diabetes_mult *= 2.0
    if bmi > 25:
        diabetes_mult *= 1.5
    if profile.get("family_diabetes"):
        diabetes_mult *= 2.0
    if exercise_hours_week < 2.5:
        diabetes_mult *= 1.3
    if diet_quality == "poor":
        diabetes_mult *= 1.25
    cvd_mult = 1.0
    if ldl > 130:
        cvd_mult *= 1.8
    if blood_pressure_systolic > 130:
        cvd_mult *= 1.5
    if hdl < 40:
        cvd_mult *= 1.5
    if profile.get("smoking") == "current":
        cvd_mult *= 2.5
    if profile.get("family_heart"):
        cvd_mult *= 1.8
    if diet_quality == "poor":
        cvd_mult *= 1.3
    metabolic_mult = 1.0
    if bmi > 25:
        metabolic_mult *= 1.5
    if visceral_fat_kg > 2:
        metabolic_mult *= 1.5
    if triglycerides > 150:
        metabolic_mult *= 1.3
    if diet_quality == "poor":
        metabolic_mult *= 1.4
    mental_mult = 1.0
    if phq9_score > 10:
        mental_mult *= 2.0
    if sleep_hours < 6:
        mental_mult *= 1.5
    if stress_level > 7:
        mental_mult *= 1.3
    if screen_time_hours > 12:
        mental_mult *= 1.2
    if vitamin_d < 20:
        mental_mult *= 1.3
    if profile.get("family_mental"):
        mental_mult *= 1.5
    if exam_stress > 7:
        mental_mult *= 1.3
    if study_hours_daily > 8 and sleep_hours < 6:
        mental_mult *= 1.4
    results: list[dict[str, Any]] = []
    for year in range(1, years + 1):
        results.append(
            {
                "year": year,
                "diabetes_risk": round(min(1 - (1 - diabetes_base * diabetes_mult) ** year, 0.95), 4),
                "cvd_risk": round(min(1 - (1 - cvd_base * cvd_mult) ** year, 0.95), 4),
                "metabolic_risk": round(min(1 - (1 - metabolic_base * metabolic_mult) ** year, 0.95), 4),
                "mental_decline_risk": round(min(1 - (1 - mental_base * mental_mult) ** year, 0.95), 4),
            }
        )
    return results


def mental_wellness_score(profile: dict[str, Any], spotify_emotion_weight: float | None = None) -> dict[str, Any]:
    """Calculate mental wellness score (0-100) with detailed breakdown."""

    score = 100.0
    penalties: dict[str, float] = {}
    phq9 = _num(profile.get("phq9_score"))
    penalties["phq9_penalty"] = round(min(phq9 * 3, 30), 1)
    sleep = _num(profile.get("sleep_hours"), 7.5)
    penalties["sleep_penalty"] = round(15 if sleep < 6 else (7 - sleep) * 15 if sleep < 7 else 0, 1)
    stress = _num(profile.get("stress_level"), 5)
    penalties["stress_penalty"] = round(min(max(0, (stress - 4) * 2.5), 15), 1)
    screen = _num(profile.get("screen_time_hours"), 6)
    penalties["screen_penalty"] = round(min(max(0, (screen - 6) * 1.67), 10), 1)
    exam_stress = _num(profile.get("exam_stress"))
    study_hrs = _num(profile.get("study_hours_daily"))
    academic_penalty = 0.0
    if exam_stress > 6:
        academic_penalty += (exam_stress - 6) * 1.5
    if study_hrs > 8:
        academic_penalty += min(study_hrs - 8, 2) * 2
    penalties["academic_penalty"] = round(min(academic_penalty, 10), 1)
    exercise = _num(profile.get("exercise_min"), 30)
    penalties["exercise_penalty"] = 10.0 if exercise < 15 else 5.0 if exercise < 30 else 0.0
    posture = _num(profile.get("posture_score_pct"), 70)
    penalties["posture_penalty"] = round(min(max(0, (60 - posture) / 12), 5), 1)
    vitd = _num(profile.get("vitamin_d"), 30)
    penalties["vitd_penalty"] = 10.0 if vitd and vitd < 20 else 5.0 if vitd and vitd < 30 else 0.0
    hrv = _num(profile.get("hrv_ms"), 40)
    penalties["hrv_penalty"] = 5.0 if hrv and hrv < 20 else 3.0 if hrv and hrv < 30 else 0.0
    for value in penalties.values():
        score -= value
    breakdown_list = [{"name": key.replace("_penalty", "").replace("_", " ").title(), "penalty": value} for key, value in penalties.items() if value > 0]
    if spotify_emotion_weight is not None and spotify_emotion_weight != 0:
        score += spotify_emotion_weight
        breakdown_list.append({"name": "Spotify Mood", "penalty": abs(spotify_emotion_weight)})
    return {"score": round(max(score, 0), 1), "breakdown": penalties, "breakdown_list": breakdown_list}


def nutrition_targets(profile: dict[str, Any]) -> dict[str, Any]:
    """Calculate personalized daily nutrition targets based on profile data."""

    weight = _positive_num(profile.get("weight_kg"), 70)
    bmr = _positive_num(profile.get("bmr"), round(weight * 30))
    calories = round(bmr * 1.4) if bmr else round(weight * 30)
    muscle_ratio = max(0.0, _num(profile.get("muscle_mass_kg")) / weight) if weight else 0
    protein_mult = 1.5 if muscle_ratio < 0.35 else 1.2
    protein_g = round(weight * protein_mult)
    ldl = _num(profile.get("ldl"), 100)
    sat_fat_g = 10 if ldl > 160 else 11 if ldl > 130 else 13 if ldl > 100 else 16
    fiber_g = 30
    temp = max(0.0, _num(profile.get("temperature_c"), 28))
    water_ml = round(weight * 35 + max(0, temp - 25) * 100)
    vitd_ug = 50 if _num(profile.get("vitamin_d"), 30) < 20 else 15
    b12_ug = 100 if _num(profile.get("b12"), 300) < 300 else 2.4
    fat_g = round(calories * 0.25 / 9)
    carbs_g = round((calories - protein_g * 4 - fat_g * 9) / 4)
    return {
        "calories": calories,
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fat_g": fat_g,
        "sat_fat_g": sat_fat_g,
        "fiber_g": fiber_g,
        "water_ml": water_ml,
        "vitamin_d_ug": vitd_ug,
        "b12_ug": b12_ug,
        "calories_per_meal": round(calories / 3),
        "reasoning": [
            f"Sat fat limited to {sat_fat_g}g because LDL is {ldl} mg/dL.",
            f"Protein target set to {protein_g}g from weight and muscle ratio.",
        ],
    }


def simulate_habit_change(profile: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    """Apply hypothetical lifestyle changes and recalculate bio age."""

    modified = {**profile}
    duration_key = str(changes.get("duration") or "3m")
    duration_label, duration_factor = _scenario_duration_meta(duration_key)
    if "sleep" in changes:
        modified["sleep_hours"] = float(changes["sleep"])
    if "exercise" in changes:
        modified["exercise_hours_week"] = float(changes["exercise"])
        modified["exercise_min"] = int(float(changes["exercise"]) * 60 / 7)
    if "screen_time" in changes:
        modified["screen_time_hours"] = float(changes["screen_time"])
    if "stress" in changes:
        modified["stress_level"] = float(changes["stress"])
    if "exam_stress" in changes:
        modified["exam_stress"] = float(changes["exam_stress"])
    if "diet" in changes:
        modified["diet_quality"] = {1: "poor", 2: "average", 3: "good", 4: "excellent"}.get(int(changes["diet"]), "average")
    modified.update({key: value for key, value in changes.items() if key not in {"sleep", "exercise", "screen_time", "stress", "exam_stress", "diet", "duration"}})
    current = _calculate_bio_age_base(profile)
    projected_raw = _calculate_bio_age_base(modified)
    chrono = float(profile.get("age", profile.get("chronological_age", 25)) or 25)
    scaled_deltas: dict[str, float] = {}
    delta_shift: dict[str, float] = {}
    for key in ("cv", "met", "msk", "neuro"):
        current_delta = float(current["deltas"][key])
        raw_delta = float(projected_raw["deltas"][key])
        shifted_delta = current_delta + (raw_delta - current_delta) * duration_factor
        low, high = DELTA_LIMITS[key]
        scaled_deltas[key] = _clamp(shifted_delta, low, high)
        delta_shift[key] = round(scaled_deltas[key] - current_delta, 2)
    projected = _build_bio_age_from_deltas(
        chrono,
        scaled_deltas["cv"],
        scaled_deltas["met"],
        scaled_deltas["msk"],
        scaled_deltas["neuro"],
    )
    base_risk = project_risk(profile)
    raw_risk = project_risk(modified)
    scaled_risk: list[dict[str, Any]] = []
    for current_row, projected_row in zip(base_risk, raw_risk):
        scaled_risk.append(
            {
                "year": current_row["year"],
                "diabetes_risk": round(_clamp(current_row["diabetes_risk"] + (projected_row["diabetes_risk"] - current_row["diabetes_risk"]) * duration_factor, 0.0, 0.95), 4),
                "cvd_risk": round(_clamp(current_row["cvd_risk"] + (projected_row["cvd_risk"] - current_row["cvd_risk"]) * duration_factor, 0.0, 0.95), 4),
                "metabolic_risk": round(_clamp(current_row["metabolic_risk"] + (projected_row["metabolic_risk"] - current_row["metabolic_risk"]) * duration_factor, 0.0, 0.95), 4),
                "mental_decline_risk": round(_clamp(current_row["mental_decline_risk"] + (projected_row["mental_decline_risk"] - current_row["mental_decline_risk"]) * duration_factor, 0.0, 0.95), 4),
            }
        )
    return {
        "current": current,
        "projected": projected,
        "improvement": round(current["overall"] - projected["overall"], 1),
        "new_risk_projections": scaled_risk,
        "duration": {
            "key": duration_key,
            "label": duration_label,
            "factor": duration_factor,
        },
        "exact_math": {
            "formula": "overall = chrono + (0.30*cv + 0.25*met + 0.20*msk + 0.25*neuro)",
            "weights": deepcopy(OVERALL_WEIGHTS),
            "current_deltas": deepcopy(current["deltas"]),
            "projected_deltas": deepcopy(projected["deltas"]),
            "delta_shift": delta_shift,
        },
    }


def score_meal(profile: dict[str, Any], meal: dict[str, Any]) -> dict[str, Any]:
    """Score a meal against personalized nutrition targets."""

    total = meal.get("total", meal)
    targets = nutrition_targets(profile)
    score = 100.0
    flags: list[str] = []
    sat_fat = float(total.get("sat_fat_g", 0) or 0)
    calories = float(total.get("calories", 0) or 0)
    fiber = float(total.get("fiber_g", 0) or 0)
    protein = float(total.get("protein_g", 0) or 0)
    if sat_fat > targets["sat_fat_g"]:
        score -= min(25.0, (sat_fat - targets["sat_fat_g"]) * 4)
        flags.append(f"Saturated fat is above your daily target ({sat_fat}g vs {targets['sat_fat_g']}g).")
    if calories > targets["calories_per_meal"] * 1.2:
        score -= min(20.0, (calories - targets["calories_per_meal"]) / 20)
        flags.append("Calories are heavy for a single meal.")
    if fiber < 5:
        score -= 10
        flags.append("Fiber is low for this meal.")
    if protein < max(15, targets["protein_g"] / 4):
        score -= 8
        flags.append("Protein is lower than ideal.")
    if _num(profile.get("fasting_glucose")) > 100 and float(total.get("carbs_g", 0) or 0) > 60:
        score -= 12
        flags.append("High carbohydrate load for elevated fasting glucose.")
    suggestions: list[str] = []
    if fiber < 5:
        suggestions.append("Add vegetables, legumes, or fruit for fiber.")
    if protein < max(15, targets["protein_g"] / 4):
        suggestions.append("Add a lean protein source.")
    if sat_fat > targets["sat_fat_g"]:
        suggestions.append("Swap fried or creamy items for lower saturated fat options.")
    return {"score": round(max(score, 0), 1), "flags": flags, "suggestions": suggestions, "targets": targets}


def workout_targets(profile: dict[str, Any]) -> dict[str, Any]:
    """Generate profile-aware weekly workout recommendations."""

    bio = _calculate_bio_age_base(profile)
    chrono = profile.get("age", profile.get("chronological_age", 25)) or 25
    recommended_sessions: list[dict[str, Any]] = [
        {"type": "walking", "frequency": "5x/week", "duration_min": 30, "reason": "Baseline zone 2 cardio aligned with WHO guidance."},
        {"type": "strength", "frequency": "2x/week", "duration_min": 40, "reason": "Maintain muscle mass and metabolic resilience."},
    ]
    priority_areas: list[str] = []
    if bio["cardiovascular"] > chrono:
        recommended_sessions.append({"type": "cycling", "frequency": "1x/week", "duration_min": 45, "reason": "Extra cardio to improve cardiovascular bio age."})
        priority_areas.append("cardiovascular")
    if bio["musculoskeletal"] > chrono:
        recommended_sessions.append({"type": "weight_training", "frequency": "1x/week", "duration_min": 45, "reason": "Extra strength focus for musculoskeletal age."})
        priority_areas.append("strength")
    if bio["neurological"] > chrono:
        recommended_sessions.append({"type": "yoga", "frequency": "2x/week", "duration_min": 20, "reason": "Mobility and stress regulation for neurological age."})
        priority_areas.append("flexibility")
    if (profile.get("bmi") or 0) > 25:
        recommended_sessions.append({"type": "hiit", "frequency": "1x/week", "duration_min": 20, "reason": "BMI suggests added metabolic conditioning."})
        priority_areas.append("metabolic")
    if (profile.get("posture_score_pct") or 100) < 70:
        recommended_sessions.append({"type": "yoga", "frequency": "3x/week", "duration_min": 15, "reason": "Low posture score benefits from mobility and stretching."})
    if (profile.get("vo2max") or 40) < 35:
        recommended_sessions.append({"type": "walking", "frequency": "daily", "duration_min": 35, "reason": "Low VO2max favors steady zone 2 work."})
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for session in recommended_sessions:
        key = (session["type"], session["frequency"], session["duration_min"])
        if key not in seen:
            seen.add(key)
            deduped.append(session)
    return {"weekly_target_min": 150, "recommended_sessions": deduped, "priority_areas": priority_areas or ["consistency"]}


def rank_impact(profile: dict[str, Any]) -> dict[str, Any]:
    """Rank habit changes by estimated bio-age impact."""

    candidate_changes: list[tuple[str, dict[str, Any]]] = [
        ("Sleep 8h", {"sleep_hours": 8}),
        ("10k steps", {"steps_avg_7d": 10000}),
        ("Exercise 5h/week", {"exercise_hours_week": 5, "exercise_min": 40}),
        ("Reduce stress to 4", {"stress_level": 4}),
        ("Cut screen time to 5h", {"screen_time_hours": 5}),
    ]
    ranked: list[dict[str, Any]] = []
    current = _calculate_bio_age_base(profile)["overall"]
    for label, changes in candidate_changes:
        projected = _calculate_bio_age_base({**deepcopy(profile), **changes})["overall"]
        ranked.append({"change": label, "estimated_bio_age_reduction": round(current - projected, 1), "changes": changes})
    ranked.sort(key=lambda item: item["estimated_bio_age_reduction"], reverse=True)
    return {"top_changes": ranked[:3], "ranked_changes": ranked}
