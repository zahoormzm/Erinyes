from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any

import aiosqlite

from backend.database import get_profile_dict
from backend.reports import build_doctor_report, render_doctor_report_text
from backend.specialists import check_specialists

CRITICAL_THRESHOLDS: list[dict[str, Any]] = [
    {"metric": "blood_pressure_systolic", "threshold": 180, "op": ">", "severity": "critical", "message": "Hypertensive crisis - systolic BP {value}"},
    {"metric": "blood_pressure_diastolic", "threshold": 120, "op": ">", "severity": "critical", "message": "Hypertensive crisis - diastolic BP {value}"},
    {"metric": "fasting_glucose", "threshold": 250, "op": ">", "severity": "critical", "message": "Dangerously high blood glucose: {value} mg/dL"},
    {"metric": "resting_hr", "threshold": 120, "op": ">", "severity": "critical", "message": "Resting heart rate critically high: {value} bpm"},
    {"metric": "resting_hr", "threshold": 40, "op": "<", "severity": "critical", "message": "Resting heart rate critically low: {value} bpm"},
    {"metric": "blood_oxygen_pct", "threshold": 90, "op": "<", "severity": "critical", "message": "Blood oxygen dangerously low: {value}%"},
    {"metric": "phq9_score", "threshold": 20, "op": ">", "severity": "critical", "message": "Severe depression score (PHQ-9): {value}"},
    {"metric": "ldl", "threshold": 190, "op": ">", "severity": "high", "message": "Very high LDL cholesterol: {value} mg/dL"},
    {"metric": "hba1c", "threshold": 9, "op": ">", "severity": "high", "message": "Very high HbA1c: {value}%"},
]

CRISIS_RESOURCES_INDIA: dict[str, str] = {
    "Vandrevala Foundation": "1860-2662-345",
    "iCall": "9152987821",
    "AASRA": "9820466726",
}


def _compare(value: float, threshold: float, op: str) -> bool:
    """Compare a value against a threshold."""

    return value > threshold if op == ">" else value < threshold


def _match_rule(alert: dict[str, Any]) -> dict[str, Any] | None:
    metric = alert.get("metric")
    severity = alert.get("severity")
    threshold = alert.get("threshold")
    for rule in CRITICAL_THRESHOLDS:
        if rule["metric"] != metric or rule["severity"] != severity:
            continue
        if threshold is not None and float(rule["threshold"]) != float(threshold):
            continue
        return rule
    return None


def _enrich_alert(alert: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(alert)
    rule = _match_rule(enriched)
    if rule:
        enriched.setdefault("op", rule["op"])
        enriched.setdefault("message", rule["message"].format(value=enriched.get("value")))
    enriched["requires_doctor_alert"] = enriched.get("severity") == "critical"
    return enriched


def check_critical_values(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Check all critical thresholds against the profile."""

    alerts: list[dict[str, Any]] = []
    for rule in CRITICAL_THRESHOLDS:
        value = profile.get(rule["metric"])
        if value is None or not _compare(float(value), float(rule["threshold"]), rule["op"]):
            continue
        alert = {
            "metric": rule["metric"],
            "value": float(value),
            "threshold": float(rule["threshold"]),
            "op": rule["op"],
            "severity": rule["severity"],
            "message": rule["message"].format(value=value),
            "requires_doctor_alert": rule["severity"] == "critical",
            "crisis_resources": CRISIS_RESOURCES_INDIA if rule["metric"] == "phq9_score" else None,
        }
        alerts.append(alert)
    return alerts


async def process_alerts(user_id: str, profile: dict[str, Any], db: aiosqlite.Connection) -> list[dict[str, Any]]:
    """Run critical-value detection, log alerts, and optionally notify doctors."""

    generated = check_critical_values(profile)
    results: list[dict[str, Any]] = []
    for alert in generated:
        cursor = await db.execute(
            """
            INSERT INTO alerts (user_id, metric, value, threshold, severity, doctor_notified, user_approved_doctor_alert)
            VALUES (?,?,?,?,?,?,?)
            """,
            (user_id, alert["metric"], alert["value"], alert["threshold"], alert["severity"], 0, None),
        )
        alert["id"] = cursor.lastrowid
        if alert["requires_doctor_alert"] and profile.get("doctor_email"):
            sent = await send_doctor_alert(user_id, alert, db)
            alert["doctor_notified"] = sent
        else:
            alert["doctor_notified"] = False
        results.append(alert)
    await db.commit()
    return results


async def _send_doctor_report_email(
    user_id: str,
    doctor_email: str | None,
    profile: dict[str, Any],
    alerts: list[dict[str, Any]],
    db: aiosqlite.Connection,
) -> dict[str, Any]:
    """Send a consolidated doctor report email for the selected alerts."""

    if not doctor_email:
        return {"success": False, "report": None, "report_text": "", "sent_alert_ids": []}
    enriched_alerts = [_enrich_alert(alert) for alert in alerts]
    specialists = check_specialists(profile)
    report = build_doctor_report(profile, alerts=enriched_alerts, specialists=specialists)
    report_text = render_doctor_report_text(report)
    host = os.getenv("SMTP_HOST")
    port = os.getenv("SMTP_PORT")
    username = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    from_email = os.getenv("SMTP_FROM_EMAIL", username or "")
    from_name = os.getenv("SMTP_FROM_NAME", "EirView Alerts")
    if not all([host, port, username, password]):
        return {"success": False, "report": report, "report_text": report_text, "sent_alert_ids": []}
    message = EmailMessage()
    message["Subject"] = f"EirView clinical escalation report for {profile.get('name', user_id)}"
    message["From"] = f"{from_name} <{from_email}>" if from_email else username
    message["To"] = doctor_email
    message.set_content(report_text)
    try:
        with smtplib.SMTP(host, int(port)) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(message)
        sent_ids = [alert.get("id") for alert in alerts if alert.get("id") is not None]
        if sent_ids:
            placeholders = ",".join(["?"] * len(sent_ids))
            await db.execute(
                f"UPDATE alerts SET doctor_notified=1, doctor_email_sent_at=CURRENT_TIMESTAMP WHERE id IN ({placeholders})",
                sent_ids,
            )
        await db.commit()
        return {"success": True, "report": report, "report_text": report_text, "sent_alert_ids": sent_ids}
    except Exception:
        return {"success": False, "report": report, "report_text": report_text, "sent_alert_ids": []}


async def send_doctor_alert(user_id: str, alert: dict[str, Any], db: aiosqlite.Connection) -> bool:
    """Send a consolidated doctor report for a single alert."""

    profile = await get_profile_dict(user_id, db)
    if profile is None:
        return False
    result = await _send_doctor_report_email(user_id, profile.get("doctor_email"), profile, [alert], db)
    return bool(result.get("success"))


async def check_alerts(user_id: str, db: aiosqlite.Connection) -> list[dict[str, Any]]:
    """Return existing logged alerts and create any missing current alerts."""

    profile_row = await (await db.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,))).fetchone()
    full_profile = await get_profile_dict(user_id, db)
    if profile_row:
        existing_keys = {
            (row["metric"], row["severity"])
            for row in await (await db.execute("SELECT metric, severity FROM alerts WHERE user_id=?", (user_id,))).fetchall()
        }
        for alert in check_critical_values(dict(profile_row)):
            if (alert["metric"], alert["severity"]) not in existing_keys:
                await process_alerts(user_id, dict(profile_row), db)
                break
    rows = await (await db.execute("SELECT * FROM alerts WHERE user_id=? ORDER BY timestamp DESC", (user_id,))).fetchall()
    alerts = []
    specialists = check_specialists(full_profile) if full_profile else []
    for row in rows:
        item = _enrich_alert(dict(row))
        item["doctor_available"] = bool(profile_row and profile_row["doctor_email"])
        threshold = item.get("threshold") or 0
        value = item.get("value") or 0
        item["direction"] = "high" if value >= threshold else "low"
        if full_profile:
            report = build_doctor_report(full_profile, alerts=[item], specialists=specialists)
            item["flag_reason"] = report["summary"]["why_now"][0] if report["summary"]["why_now"] else item.get("message")
            item["doctor_report_summary"] = report["summary"]
        alerts.append(item)
    return alerts


async def notify_doctor(user_id: str, doctor_email_or_alert: str | dict[str, Any] | None, alert_ids: list[int] | None = None, db: aiosqlite.Connection | None = None) -> dict[str, Any]:
    """Notify doctor for specific alert IDs or a single alert dict."""

    own_connection = db is None
    conn = db or await aiosqlite.connect(os.environ.get("EIRVIEW_DB_PATH", "eirview.db"))
    conn.row_factory = aiosqlite.Row
    try:
        profile = await get_profile_dict(user_id, conn)
        if profile is None:
            return {"success": False, "sent_alert_ids": [], "report": None, "report_text": ""}
        if isinstance(doctor_email_or_alert, dict):
            return await _send_doctor_report_email(
                user_id,
                doctor_email_or_alert.get("doctor_email") or profile.get("doctor_email"),
                profile,
                [doctor_email_or_alert],
                conn,
            )
        selected_alerts: list[dict[str, Any]] = []
        for alert_id in alert_ids or []:
            row = await (await conn.execute("SELECT * FROM alerts WHERE id=? AND user_id=?", (alert_id, user_id))).fetchone()
            if row:
                selected_alerts.append(dict(row))
        if not selected_alerts:
            selected_alerts = check_critical_values(profile)
        return await _send_doctor_report_email(
            user_id,
            doctor_email_or_alert if isinstance(doctor_email_or_alert, str) and doctor_email_or_alert else profile.get("doctor_email"),
            profile,
            selected_alerts,
            conn,
        )
    finally:
        if own_connection:
            await conn.close()
