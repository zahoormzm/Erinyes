from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.specialists import check_specialists

METRIC_METADATA: dict[str, dict[str, str]] = {
    "blood_pressure_systolic": {"label": "Blood Pressure Systolic", "unit": "mmHg", "group": "Vitals"},
    "blood_pressure_diastolic": {"label": "Blood Pressure Diastolic", "unit": "mmHg", "group": "Vitals"},
    "resting_hr": {"label": "Resting Heart Rate", "unit": "bpm", "group": "Vitals"},
    "blood_oxygen_pct": {"label": "Blood Oxygen Saturation", "unit": "%", "group": "Vitals"},
    "respiratory_rate": {"label": "Respiratory Rate", "unit": "breaths/min", "group": "Vitals"},
    "ldl": {"label": "LDL Cholesterol", "unit": "mg/dL", "group": "Cardiometabolic"},
    "hdl": {"label": "HDL Cholesterol", "unit": "mg/dL", "group": "Cardiometabolic"},
    "triglycerides": {"label": "Triglycerides", "unit": "mg/dL", "group": "Cardiometabolic"},
    "total_cholesterol": {"label": "Total Cholesterol", "unit": "mg/dL", "group": "Cardiometabolic"},
    "fasting_glucose": {"label": "Fasting Glucose", "unit": "mg/dL", "group": "Cardiometabolic"},
    "hba1c": {"label": "HbA1c", "unit": "%", "group": "Cardiometabolic"},
    "creatinine": {"label": "Creatinine", "unit": "mg/dL", "group": "Cardiometabolic"},
    "sgpt_alt": {"label": "ALT (SGPT)", "unit": "U/L", "group": "Cardiometabolic"},
    "sgot_ast": {"label": "AST (SGOT)", "unit": "U/L", "group": "Cardiometabolic"},
    "tsh": {"label": "TSH", "unit": "mIU/L", "group": "Micronutrients"},
    "vitamin_d": {"label": "Vitamin D", "unit": "ng/mL", "group": "Micronutrients"},
    "b12": {"label": "Vitamin B12", "unit": "pg/mL", "group": "Micronutrients"},
    "ferritin": {"label": "Ferritin", "unit": "ng/mL", "group": "Micronutrients"},
    "hemoglobin": {"label": "Hemoglobin", "unit": "g/dL", "group": "Micronutrients"},
    "bmi": {"label": "BMI", "unit": "", "group": "Body Composition"},
    "body_fat_pct": {"label": "Body Fat", "unit": "%", "group": "Body Composition"},
    "visceral_fat_kg": {"label": "Visceral Fat", "unit": "kg", "group": "Body Composition"},
    "weight_kg": {"label": "Weight", "unit": "kg", "group": "Body Composition"},
    "vo2max": {"label": "VO2max", "unit": "mL/kg/min", "group": "Fitness"},
    "hrv_ms": {"label": "HRV", "unit": "ms", "group": "Fitness"},
    "exercise_hours_week": {"label": "Exercise Hours per Week", "unit": "hours", "group": "Fitness"},
    "steps_avg_7d": {"label": "Average Daily Steps", "unit": "steps", "group": "Fitness"},
    "posture_score_pct": {"label": "Posture Score", "unit": "%", "group": "Fitness"},
    "walking_asymmetry_pct": {"label": "Walking Asymmetry", "unit": "%", "group": "Fitness"},
    "sleep_hours": {"label": "Sleep Duration", "unit": "hours", "group": "Lifestyle"},
    "stress_level": {"label": "Stress Level", "unit": "/10", "group": "Lifestyle"},
    "screen_time_hours": {"label": "Screen Time", "unit": "hours", "group": "Lifestyle"},
    "smoking": {"label": "Smoking Status", "unit": "", "group": "Lifestyle"},
    "diet_quality": {"label": "Diet Quality", "unit": "", "group": "Lifestyle"},
    "phq9_score": {"label": "PHQ-9 Score", "unit": "", "group": "Mental Health"},
    "exam_stress": {"label": "Exam Stress", "unit": "/10", "group": "Mental Health"},
    "study_hours_daily": {"label": "Study Hours per Day", "unit": "hours", "group": "Mental Health"},
}

SNAPSHOT_GROUPS: dict[str, list[str]] = {
    "Vitals": ["blood_pressure_systolic", "blood_pressure_diastolic", "resting_hr", "blood_oxygen_pct", "respiratory_rate"],
    "Cardiometabolic": ["ldl", "hdl", "triglycerides", "total_cholesterol", "fasting_glucose", "hba1c", "creatinine", "sgpt_alt", "sgot_ast"],
    "Micronutrients": ["vitamin_d", "b12", "ferritin", "hemoglobin", "tsh"],
    "Body Composition": ["weight_kg", "bmi", "body_fat_pct", "visceral_fat_kg"],
    "Fitness": ["vo2max", "hrv_ms", "exercise_hours_week", "steps_avg_7d", "posture_score_pct", "walking_asymmetry_pct"],
    "Lifestyle": ["sleep_hours", "stress_level", "screen_time_hours", "smoking", "diet_quality"],
    "Mental Health": ["phq9_score", "exam_stress", "study_hours_daily"],
}

IMPORTANT_MISSING_FIELDS: list[str] = [
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
    "resting_hr",
    "blood_oxygen_pct",
    "ldl",
    "hdl",
    "triglycerides",
    "fasting_glucose",
    "hba1c",
    "creatinine",
    "vitamin_d",
    "b12",
    "sleep_hours",
    "stress_level",
    "phq9_score",
]


def _metric_meta(metric: str) -> dict[str, str]:
    return METRIC_METADATA.get(metric, {"label": metric.replace("_", " ").title(), "unit": "", "group": "Other"})


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: Any) -> str:
    numeric = _to_float(value)
    if numeric is None:
        return str(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.1f}"


def format_metric_value(metric: str, value: Any) -> str:
    if value in (None, ""):
        return "Not provided"
    meta = _metric_meta(metric)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, str) and not _to_float(value):
        return value
    rendered = _format_number(value)
    return f"{rendered} {meta['unit']}".strip()


def _severity_rank(value: str) -> int:
    ranks = {"routine": 0, "soon": 1, "high": 1, "urgent": 2, "critical": 3}
    return ranks.get(value, 0)


def _max_urgency(current: str, candidate: str) -> str:
    return candidate if _severity_rank(candidate) > _severity_rank(current) else current


def _build_snapshot(profile: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    snapshot: dict[str, list[dict[str, Any]]] = {}
    for group, metrics in SNAPSHOT_GROUPS.items():
        rows: list[dict[str, Any]] = []
        for metric in metrics:
            value = profile.get(metric)
            if value in (None, ""):
                continue
            meta = _metric_meta(metric)
            rows.append(
                {
                    "metric": metric,
                    "label": meta["label"],
                    "value": value,
                    "display_value": format_metric_value(metric, value),
                }
            )
        if rows:
            snapshot[group] = rows
    return snapshot


def _missing_relevant_fields(profile: dict[str, Any], specialists: list[dict[str, Any]]) -> list[str]:
    requested = set(IMPORTANT_MISSING_FIELDS)
    for specialist in specialists:
        for metric in specialist.get("metrics", []):
            requested.add(metric.get("metric", ""))
    missing: list[str] = []
    for metric in requested:
        if not metric:
            continue
        if profile.get(metric) in (None, ""):
            missing.append(_metric_meta(metric)["label"])
    return sorted(set(missing))


def _alert_reason(alert: dict[str, Any]) -> str:
    metric = alert.get("metric", "")
    label = _metric_meta(metric)["label"]
    value = alert.get("value")
    threshold = alert.get("threshold")
    direction = "above" if (_to_float(value) or 0) >= (_to_float(threshold) or 0) else "below"
    base = alert.get("message") or f"{label} is {direction} the alert threshold"
    if threshold in (None, ""):
        return base
    return f"{base}. Measured {format_metric_value(metric, value)} versus threshold {format_metric_value(metric, threshold)}."


def _build_next_steps(alerts: list[dict[str, Any]], specialists: list[dict[str, Any]], missing_fields: list[str]) -> list[str]:
    steps: list[str] = []
    if alerts:
        steps.append("Review the flagged values clinically and confirm whether repeat testing or urgent evaluation is required.")
    if specialists:
        specialist_names = ", ".join(item["specialist"] for item in specialists[:3])
        steps.append(f"Arrange follow-up with the recommended specialist(s): {specialist_names}.")
    if missing_fields:
        steps.append(f"Interpretation is based only on available inputs. Missing relevant data includes: {', '.join(missing_fields[:6])}.")
    if not steps:
        steps.append("No active doctor escalation is required from the currently available data.")
    return steps


def build_doctor_report(
    profile: dict[str, Any],
    alerts: list[dict[str, Any]] | None = None,
    specialists: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a doctor-facing report using only the data currently available."""

    current_alerts = alerts or []
    current_specialists = specialists if specialists is not None else check_specialists(profile)
    urgency = "routine"
    for alert in current_alerts:
        urgency = _max_urgency(urgency, str(alert.get("severity", "routine")))
    for specialist in current_specialists:
        urgency = _max_urgency(urgency, str(specialist.get("urgency", "routine")))
    snapshot = _build_snapshot(profile)
    missing_fields = _missing_relevant_fields(profile, current_specialists)
    snapshot_count = sum(len(rows) for rows in snapshot.values())
    flagged_reasons: list[str] = []
    flagged_reasons.extend(_alert_reason(alert) for alert in current_alerts)
    for specialist in current_specialists:
        if specialist.get("reasons"):
            flagged_reasons.append(
                f"{specialist['specialist'].title()} recommended because {', '.join(specialist['reasons'])}."
            )
    if flagged_reasons:
        headline = f"EirView recommends clinical follow-up based on {len(flagged_reasons)} flagged finding(s)."
    else:
        headline = "No active doctor escalation is required from the available data."
    return {
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "patient": {
            "id": profile.get("user_id") or profile.get("id"),
            "name": profile.get("name"),
            "age": profile.get("age"),
            "sex": profile.get("sex"),
        },
        "doctor_required": bool(current_alerts or current_specialists),
        "urgency": urgency,
        "summary": {
            "headline": headline,
            "why_now": flagged_reasons[:3],
            "available_metric_count": snapshot_count,
            "missing_relevant_count": len(missing_fields),
        },
        "alerts": [
            {
                "metric": alert.get("metric"),
                "label": _metric_meta(str(alert.get("metric", "")))["label"],
                "value": alert.get("value"),
                "display_value": format_metric_value(str(alert.get("metric", "")), alert.get("value")),
                "threshold": alert.get("threshold"),
                "display_threshold": format_metric_value(str(alert.get("metric", "")), alert.get("threshold")),
                "severity": alert.get("severity"),
                "message": alert.get("message"),
                "reason": _alert_reason(alert),
            }
            for alert in current_alerts
        ],
        "specialists": current_specialists,
        "clinical_snapshot": snapshot,
        "missing_relevant_data": missing_fields,
        "next_steps": _build_next_steps(current_alerts, current_specialists, missing_fields),
    }


def render_doctor_report_text(report: dict[str, Any]) -> str:
    """Render a doctor report as plain text for email and previews."""

    patient = report.get("patient", {})
    lines = [
        "EirView Clinical Escalation Report",
        f"Generated: {report.get('generated_at', 'Unknown')}",
        f"Patient: {patient.get('name', 'Unknown')} ({patient.get('id', 'Unknown')})",
        f"Age/Sex: {patient.get('age', 'Unknown')} / {patient.get('sex', 'Unknown')}",
        f"Urgency: {report.get('urgency', 'routine').upper()}",
        "",
        report.get("summary", {}).get("headline", ""),
        "",
        "Why It Was Flagged:",
    ]
    reasons = report.get("summary", {}).get("why_now", [])
    if reasons:
        lines.extend(f"- {reason}" for reason in reasons)
    else:
        lines.append("- No active escalations from the current data.")
    alerts = report.get("alerts", [])
    if alerts:
        lines.extend(["", "Alert Evidence:"])
        for alert in alerts:
            lines.append(f"- {alert['label']}: {alert['display_value']} (threshold {alert['display_threshold']})")
    specialists = report.get("specialists", [])
    if specialists:
        lines.extend(["", "Recommended Specialists:"])
        for specialist in specialists:
            lines.append(
                f"- {specialist['specialist'].title()} [{specialist.get('urgency', 'routine')}]: {', '.join(specialist.get('reasons', []))}"
            )
    snapshot = report.get("clinical_snapshot", {})
    if snapshot:
        lines.extend(["", "Available Clinical Snapshot:"])
        for group, rows in snapshot.items():
            lines.append(f"{group}:")
            for row in rows:
                lines.append(f"- {row['label']}: {row['display_value']}")
    missing = report.get("missing_relevant_data", [])
    if missing:
        lines.extend(["", "Missing Relevant Data:", f"- {', '.join(missing)}"])
    next_steps = report.get("next_steps", [])
    if next_steps:
        lines.extend(["", "Recommended Next Steps:"])
        lines.extend(f"- {step}" for step in next_steps)
    return "\n".join(lines).strip()
