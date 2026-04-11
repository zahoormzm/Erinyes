from __future__ import annotations

import os
from typing import Any

import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL_DIR = os.path.join(BASE_DIR, "FaceAge-main", "models")

def _resolve_model_path(env_name: str, default_filename: str) -> str:
    """Resolve a model path from env, supporting stale relative paths in .env."""

    default_path = os.path.join(DEFAULT_MODEL_DIR, default_filename)
    raw_value = os.getenv(env_name, "").strip()
    if not raw_value:
        return default_path
    candidates = []
    if os.path.isabs(raw_value):
        candidates.append(raw_value)
    else:
        candidates.append(os.path.abspath(os.path.join(BASE_DIR, raw_value)))
        candidates.append(os.path.abspath(os.path.join(os.getcwd(), raw_value)))
    candidates.append(default_path)
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


ONNX_MODEL: str = _resolve_model_path("FACEAGE_MODEL_PATH", "faceage_model.onnx")
LANDMARKER: str = _resolve_model_path("FACE_LANDMARKER_PATH", "face_landmarker.task")
_session: Any = None


def _get_session() -> Any:
    """Lazy-load ONNX runtime session."""

    global _session
    if _session is None:
        if not os.path.exists(ONNX_MODEL):
            raise FileNotFoundError(f"FaceAge ONNX model not found at {ONNX_MODEL}")
        import onnxruntime as ort  # type: ignore

        _session = ort.InferenceSession(ONNX_MODEL)
    return _session


def detect_and_crop_face(img: np.ndarray) -> np.ndarray | None:
    """Detect a face using OpenCV Haar cascade and return a cropped region."""

    cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    detector = cv2.CascadeClassifier(cascade_path)
    if detector.empty():
        raise RuntimeError("OpenCV Haar face detector is unavailable in this environment")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return None
    x, y, bw, bh = max(faces, key=lambda item: item[2] * item[3])
    h, w, _ = img.shape
    margin_x = int(bw * 0.2)
    margin_y = int(bh * 0.25)
    x1 = max(0, int(x - margin_x))
    y1 = max(0, int(y - margin_y))
    x2 = min(w, int(x + bw + margin_x))
    y2 = min(h, int(y + bh + margin_y))
    crop = img[y1:y2, x1:x2]
    return crop if crop.size else None


def predict_face_age(image_bytes: bytes) -> float:
    """Run FaceAge ONNX inference and return predicted age."""

    session = _get_session()
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image")
    crop = detect_and_crop_face(image)
    if crop is None:
        raise ValueError("No face detected in the image")
    input_meta = session.get_inputs()[0]
    input_shape = input_meta.shape
    height = int(input_shape[1]) if len(input_shape) > 1 and isinstance(input_shape[1], int) else 160
    width = int(input_shape[2]) if len(input_shape) > 2 and isinstance(input_shape[2], int) else 160
    channels = int(input_shape[3]) if len(input_shape) > 3 and isinstance(input_shape[3], int) else 3
    if channels != 3:
        raise RuntimeError(f"Unexpected FaceAge channel count: {channels}")
    face = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    face = cv2.resize(face, (width, height)).astype(np.float32) / 255.0
    face = np.expand_dims(face, 0)
    output = session.run(None, {input_meta.name: face})
    predicted_age = output[0]
    if isinstance(predicted_age, np.ndarray):
        predicted_age = float(predicted_age.reshape(-1)[0])
    return round(float(predicted_age), 1)
