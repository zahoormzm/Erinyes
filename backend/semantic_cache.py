"""Semantic query cache to reduce redundant LLM calls."""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_model = None
_cache: dict[str, dict[str, Any]] = {}

SIMILARITY_THRESHOLD = 0.92
CACHE_TTL_SECONDS = 1800
MAX_CACHE_SIZE = 200

NEVER_CACHE_AGENTS = {"mental_health"}
NEVER_CACHE_IF = {"phq9_score_above": 15}


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _profile_fingerprint(profile: dict) -> str:
    """Hash key health values that affect response relevance."""

    key_fields = [
        "bio_age_overall",
        "phq9_score",
        "stress_level",
        "sleep_hours",
        "vitamin_d",
        "ldl",
        "hdl",
        "steps_avg_7d",
        "mental_wellness_score",
        "exercise_min",
        "fasting_glucose",
        "hba1c",
        "resting_hr",
        "hrv_ms",
        "screen_time_hours",
        "body_fat_pct",
        "vo2max",
    ]
    snapshot = {key: profile.get(key) for key in key_fields if profile.get(key) is not None}
    return hashlib.md5(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest()[:12]


def should_cache(agent_type: str, profile: dict | None = None, difficulty: str = "medium") -> bool:
    """Determine if this query type should use caching.

    The 0.92 similarity threshold + profile fingerprint + 30-min TTL already
    prevent stale or wrong cache hits, so we allow caching at all difficulty
    levels.  Only mental_health is excluded (responses must always be fresh
    and context-sensitive) along with crisis situations.
    """

    if agent_type in NEVER_CACHE_AGENTS:
        return False
    if profile and (profile.get("phq9_score", 0) or 0) >= NEVER_CACHE_IF["phq9_score_above"]:
        return False
    return True


def _evict_expired(now: float) -> None:
    """Drop expired cache entries."""

    expired = [key for key, value in _cache.items() if now - value["timestamp"] > CACHE_TTL_SECONDS]
    for key in expired:
        del _cache[key]


def check_cache(query: str, profile: dict, agent_type: str, difficulty: str = "medium") -> str | None:
    """Check if a semantically similar query exists in cache for this profile state."""

    if not should_cache(agent_type, profile, difficulty):
        return None

    try:
        model = _get_model()
    except Exception as exc:
        logger.warning("Semantic cache unavailable (check_cache): %s", exc)
        return None

    profile_hash = _profile_fingerprint(profile)
    query_embedding = model.encode(query, normalize_embeddings=True)
    now = time.time()
    _evict_expired(now)

    best_similarity = 0.0
    best_response = None
    for entry in _cache.values():
        if entry["profile_hash"] != profile_hash or entry["agent_type"] != agent_type:
            continue
        similarity = float(np.dot(query_embedding, entry["embedding"]))
        if similarity > best_similarity and similarity >= SIMILARITY_THRESHOLD:
            best_similarity = similarity
            best_response = entry["response"]
    return best_response


def store_cache(query: str, response: str, profile: dict, agent_type: str, difficulty: str = "medium") -> None:
    """Store a query-response pair in the semantic cache."""

    if not response or not should_cache(agent_type, profile, difficulty):
        return

    try:
        model = _get_model()
    except Exception as exc:
        logger.warning("Semantic cache unavailable (store_cache): %s", exc)
        return

    now = time.time()
    _evict_expired(now)

    if len(_cache) >= MAX_CACHE_SIZE:
        oldest_key = min(_cache, key=lambda key: _cache[key]["timestamp"])
        del _cache[oldest_key]

    profile_hash = _profile_fingerprint(profile)
    embedding = model.encode(query, normalize_embeddings=True)
    cache_key = hashlib.md5(f"{query}{profile_hash}{agent_type}".encode()).hexdigest()
    _cache[cache_key] = {
        "embedding": embedding,
        "response": response,
        "profile_hash": profile_hash,
        "agent_type": agent_type,
        "timestamp": now,
    }
