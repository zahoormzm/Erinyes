from __future__ import annotations

import sys
import time
from typing import Any

import cv2
import numpy as np
import requests

mp_pose = None
mp_drawing = None
_MEDIAPIPE_IMPORT_ERROR: Exception | None = None


def _ensure_mediapipe() -> None:
    global mp_pose, mp_drawing, _MEDIAPIPE_IMPORT_ERROR
    if mp_pose is not None and mp_drawing is not None:
        return
    if _MEDIAPIPE_IMPORT_ERROR is not None:
        raise RuntimeError(f"MediaPipe posture estimation is unavailable: {_MEDIAPIPE_IMPORT_ERROR}")
    try:  # pragma: no cover - optional native dependency
        import mediapipe as mp  # type: ignore
    except Exception as exc:  # pragma: no cover - optional native dependency
        _MEDIAPIPE_IMPORT_ERROR = exc
        raise RuntimeError(f"MediaPipe posture estimation is unavailable: {exc}") from exc
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils


def calculate_posture_angle(landmarks: Any) -> float:
    """Calculate ear-shoulder-hip angle for posture quality."""

    _ensure_mediapipe()
    ear = landmarks[mp_pose.PoseLandmark.LEFT_EAR]
    shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
    if ear.visibility < 0.5 or shoulder.visibility < 0.5:
        ear = landmarks[mp_pose.PoseLandmark.RIGHT_EAR]
        shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
    vec1 = np.array([ear.x - shoulder.x, ear.y - shoulder.y])
    vec2 = np.array([hip.x - shoulder.x, hip.y - shoulder.y])
    cos_angle = float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-6))
    return float(np.degrees(np.arccos(np.clip(cos_angle, -1, 1))))


def angle_to_score(angle: float) -> float:
    """Map posture angle to a 0-100 score."""

    if angle >= 170:
        return 100
    if angle >= 160:
        return 80
    if angle >= 150:
        return 60
    if angle >= 140:
        return 40
    return 20


def analyze_posture_image(image_bytes: bytes) -> dict[str, float | bool]:
    """Analyze one image frame and return a posture reading."""

    _ensure_mediapipe()
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode posture image")
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        results = pose.process(rgb)
    if not results.pose_landmarks:
        raise ValueError("No body pose detected. Make sure your head, shoulders, and torso are visible.")
    angle = calculate_posture_angle(results.pose_landmarks.landmark)
    score = angle_to_score(angle)
    return {
        "score_pct": round(float(score), 1),
        "avg_angle": round(float(angle), 1),
        "is_slouching": bool(score < 60),
    }


def main() -> int:
    """Run the posture detection loop and post readings to the backend."""

    _ensure_mediapipe()
    api_base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    user_id = sys.argv[2] if len(sys.argv) > 2 else "zahoor"
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam")
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        last_sent = 0.0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)
            if results.pose_landmarks:
                angle = calculate_posture_angle(results.pose_landmarks.landmark)
                score = angle_to_score(angle)
                slouching = score < 60
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                cv2.putText(frame, f"Posture: {score:.0f}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 0) if score >= 60 else (0, 0, 255), 2)
                if time.time() - last_sent > 10:
                    try:
                        requests.post(f"{api_base}/api/posture", json={"user_id": user_id, "score_pct": score, "avg_angle": angle, "is_slouching": slouching}, timeout=3)
                    except requests.RequestException:
                        pass
                    last_sent = time.time()
            cv2.imshow("EirView Posture Runner", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
