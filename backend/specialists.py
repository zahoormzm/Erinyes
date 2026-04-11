from __future__ import annotations

from typing import Any

SPECIALIST_MAP: list[dict[str, Any]] = [
    {
        "specialist": "cardiologist",
        "triggers": [
            {"metric": "ldl", "threshold": 160, "op": ">", "reason": "Very high LDL cholesterol"},
            {"metric": "total_cholesterol", "threshold": 240, "op": ">", "reason": "High total cholesterol"},
            {"metric": "blood_pressure_systolic", "threshold": 140, "op": ">", "reason": "Stage 2 hypertension (systolic)"},
            {"metric": "blood_pressure_diastolic", "threshold": 90, "op": ">", "reason": "Stage 2 hypertension (diastolic)"},
            {"metric": "resting_hr", "threshold": 100, "op": ">", "reason": "Tachycardia at rest"},
        ],
        "hospitals": [
            "Narayana Institute of Cardiac Sciences, Bommasandra",
            "Jayadeva Institute of Cardiovascular Sciences, Jayanagar",
            "Manipal Hospital, Old Airport Road",
        ],
    },
    {
        "specialist": "endocrinologist",
        "triggers": [
            {"metric": "fasting_glucose", "threshold": 126, "op": ">=", "reason": "Diabetic-range fasting glucose"},
            {"metric": "hba1c", "threshold": 6.5, "op": ">=", "reason": "Diabetic-range HbA1c"},
            {"metric": "tsh", "threshold": 4.5, "op": ">", "reason": "Possible hypothyroidism"},
            {"metric": "tsh", "threshold": 0.4, "op": "<", "reason": "Possible hyperthyroidism"},
            {"metric": "vitamin_d", "threshold": 10, "op": "<", "reason": "Severe vitamin D deficiency"},
        ],
        "hospitals": [
            "Bangalore Endocrinology & Diabetes Research Centre",
            "M.S. Ramaiah Memorial Hospital, MSRIT Post",
            "Apollo Hospital, Bannerghatta Road",
        ],
    },
    {
        "specialist": "psychiatrist",
        "triggers": [{"metric": "phq9_score", "threshold": 15, "op": ">=", "reason": "Moderately severe depression (PHQ-9)"}],
        "hospitals": ["NIMHANS, Hosur Road", "Cadabams Hospitals, Whitefield", "The Mind Research Foundation, Indiranagar"],
    },
    {
        "specialist": "psychologist",
        "triggers": [
            {"metric": "phq9_score", "threshold": 10, "op": ">=", "reason": "Moderate depression (PHQ-9)"},
            {"metric": "stress_level", "threshold": 8, "op": ">=", "reason": "High chronic stress"},
        ],
        "hospitals": ["NIMHANS, Hosur Road", "Mpower, Indiranagar", "Amaha (online platform)"],
    },
    {
        "specialist": "pulmonologist",
        "triggers": [
            {"metric": "blood_oxygen_pct", "threshold": 94, "op": "<", "reason": "Low blood oxygen saturation"},
            {"metric": "respiratory_rate", "threshold": 20, "op": ">", "reason": "Elevated respiratory rate"},
        ],
        "hospitals": ["St. John's Medical College Hospital, Koramangala", "Aster CMI Hospital, Hebbal", "Fortis Hospital, Bannerghatta Road"],
    },
    {
        "specialist": "orthopedist",
        "triggers": [
            {"metric": "posture_score_pct", "threshold": 50, "op": "<", "reason": "Very poor posture score"},
            {"metric": "walking_asymmetry_pct", "threshold": 8, "op": ">", "reason": "Significant gait asymmetry"},
        ],
        "hospitals": ["Sparsh Hospital, Infantry Road", "Hosmat Hospital, Richmond Road", "Sakra World Hospital, Bellandur"],
    },
    {
        "specialist": "nephrologist",
        "triggers": [{"metric": "creatinine", "threshold": 1.3, "op": ">", "reason": "Elevated creatinine (kidney function)"}],
        "hospitals": ["BGS Global Hospitals, Uttarahalli", "Manipal Hospital, Old Airport Road", "Columbia Asia, Hebbal"],
    },
    {
        "specialist": "hepatologist",
        "triggers": [
            {"metric": "sgpt_alt", "threshold": 56, "op": ">", "reason": "Elevated liver enzyme (ALT)"},
            {"metric": "sgot_ast", "threshold": 40, "op": ">", "reason": "Elevated liver enzyme (AST)"},
        ],
        "hospitals": ["Aster CMI Hospital, Hebbal", "Manipal Hospital, Old Airport Road", "Apollo Hospital, Seshadripuram"],
    },
]


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_metric_value(metric: str, value: Any) -> str:
    units = {
        "blood_pressure_systolic": "mmHg",
        "blood_pressure_diastolic": "mmHg",
        "resting_hr": "bpm",
        "blood_oxygen_pct": "%",
        "respiratory_rate": "breaths/min",
        "ldl": "mg/dL",
        "hdl": "mg/dL",
        "triglycerides": "mg/dL",
        "total_cholesterol": "mg/dL",
        "fasting_glucose": "mg/dL",
        "hba1c": "%",
        "tsh": "mIU/L",
        "vitamin_d": "ng/mL",
        "creatinine": "mg/dL",
        "sgpt_alt": "U/L",
        "sgot_ast": "U/L",
        "posture_score_pct": "%",
        "walking_asymmetry_pct": "%",
    }
    numeric = _safe_float(value)
    if numeric is None:
        return str(value)
    rendered = str(int(numeric)) if numeric.is_integer() else f"{numeric:.1f}"
    unit = units.get(metric, "")
    return f"{rendered} {unit}".strip()


def _compare(value: float, threshold: float, op: str) -> bool:
    """Compare a value against a threshold using a simple operator."""

    if op == ">":
        return value > threshold
    if op == ">=":
        return value >= threshold
    if op == "<":
        return value < threshold
    if op == "<=":
        return value <= threshold
    return False


def check_specialist_needs(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Check all specialist triggers against the profile."""

    results: list[dict[str, Any]] = []
    for specialist in SPECIALIST_MAP:
        reasons: list[str] = []
        metrics: list[dict[str, Any]] = []
        urgency = "routine"
        for trigger in specialist["triggers"]:
            numeric_value = _safe_float(profile.get(trigger["metric"]))
            if numeric_value is None or not _compare(numeric_value, float(trigger["threshold"]), trigger["op"]):
                continue
            reasons.append(trigger["reason"])
            metrics.append(
                {
                    "metric": trigger["metric"],
                    "value": numeric_value,
                    "display_value": _format_metric_value(trigger["metric"], numeric_value),
                    "threshold": trigger["threshold"],
                    "display_threshold": _format_metric_value(trigger["metric"], trigger["threshold"]),
                    "op": trigger["op"],
                    "reason": trigger["reason"],
                }
            )
            if trigger["op"] in {">", ">="}:
                ratio = numeric_value / float(trigger["threshold"]) if trigger["threshold"] else 1
                if ratio > 1.5:
                    urgency = "urgent"
                elif ratio > 1.2 and urgency != "urgent":
                    urgency = "soon"
            else:
                ratio = numeric_value / float(trigger["threshold"]) if trigger["threshold"] else 1
                if ratio < 0.5:
                    urgency = "urgent"
                elif ratio < 0.8 and urgency != "urgent":
                    urgency = "soon"
        if reasons:
            results.append(
                {
                    "specialist": specialist["specialist"],
                    "reasons": reasons,
                    "metrics": metrics,
                    "urgency": urgency,
                    "hospitals": specialist["hospitals"],
                }
            )
    return results


def check_specialists(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Compatibility alias returning specialist recommendations."""

    return check_specialist_needs(profile)
