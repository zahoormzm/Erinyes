"""DAAO-inspired difficulty classifier for query routing."""
from __future__ import annotations

import re
from typing import Any


def classify_difficulty(query: str, profile: dict[str, Any] | None = None) -> str:
    """
    Classify query difficulty as 'easy', 'medium', or 'hard'.

    EASY — Single data lookup, factual retrieval, one-liner answer.
      "what is my bio age", "how many steps today", "my water intake"
    MEDIUM — One specialist domain, needs some context and reasoning.
      "what should I eat", "am I sleeping enough", "tips for better sleep",
      "what happens if I keep this up", "how is my heart health"
    HARD — Genuinely multi-domain crisis/analysis needing extensive reasoning.
      "I feel burnt out AND my sleep is terrible AND nothing helps",
      "explain every single subsystem of my bio age in detail",
      long emotional messages about being overwhelmed across multiple life areas.

    The default is MEDIUM. Hard is reserved for genuinely complex queries.
    """

    q = query.lower().strip()
    words = q.split()
    word_count = len(words)

    # ── EASY: direct data lookups ──
    easy_patterns = [
        r"^what(?:'s| is) my (?:bio age|age|hrv|heart rate|hr|steps|sleep|vo2|weight|bmi|level|xp|streak|water|spo2|calories)",
        r"^how (?:many|much) (?:steps|water|sleep|calories|exercise|flights|workouts)",
        r"^show (?:me )?my",
        r"^my (?:bio age|steps|sleep|streak|level|xp|water|weight)",
        r"^what (?:level|rank) am i",
        r"^(?:current|today'?s?) (?:steps|sleep|water|exercise|hr|hrv)",
    ]
    for pattern in easy_patterns:
        if re.search(pattern, q):
            return "easy"

    # Short messages (< 6 words) that are not emotional are easy or medium
    if word_count <= 5:
        # Check for emotional short messages that should still be medium
        emotional_words = {"stressed", "anxious", "sad", "depressed", "overwhelmed", "burnout", "lonely", "scared"}
        if any(w in words for w in emotional_words):
            return "medium"
        return "easy"

    # ── HARD: only for genuinely complex, multi-signal situations ──
    # Requires STRONG signals — not just any mention of feelings or future.
    hard_signals = [
        # Crisis language — always hard (needs maximum care)
        r"(?:self[- ]harm|suicid|kill myself|end (?:it|my life)|don'?t want to (?:live|be here))",
        # Explicit request for exhaustive analysis
        r"(?:explain (?:my )?(?:full|entire|complete|all|every).*(?:age|health|breakdown|score))",
        # Long emotional distress with explicit multi-domain mentions
        r"(?:(?:burnt? out|overwhelm|exhausted|falling apart).*(?:sleep|exercise|eat|nothing helps))",
        r"(?:(?:sleep|exercise|eat).*(?:burnt? out|overwhelm|exhausted|falling apart))",
        # Explicit "nothing works" despair
        r"(?:nothing (?:works|helps|is working|i do|seems to))",
    ]
    for pattern in hard_signals:
        if re.search(pattern, q):
            return "hard"

    # Multi-domain check: 3+ distinct health domains in one message = hard
    domains_mentioned = 0
    domain_keywords = [
        {"sleep", "insomnia", "tired", "fatigue"},
        {"exercise", "workout", "steps", "gym", "active", "running"},
        {"eat", "food", "meal", "diet", "nutrition", "protein", "calories"},
        {"stress", "anxiety", "mood", "mental", "burnout"},
        {"heart", "cardio", "blood pressure", "cholesterol", "ldl", "hdl"},
        {"music", "spotify"},
        {"vitamin", "supplement", "deficien"},
    ]
    for domain in domain_keywords:
        if any(kw in q for kw in domain):
            domains_mentioned += 1
    if domains_mentioned >= 3:
        return "hard"

    # Very long messages (> 50 words) with emotional content = hard
    if word_count > 50:
        emotional_markers = {"feel", "feeling", "stressed", "anxious", "overwhelm", "depressed", "struggling", "burnt"}
        if any(w in words for w in emotional_markers):
            return "hard"

    # ── Everything else is MEDIUM ──
    return "medium"


def select_model_for_difficulty(difficulty: str) -> str:
    """Select the appropriate Claude model based on query difficulty."""

    if difficulty == "easy":
        return "claude-haiku-4-5-20251001"
    return "claude-sonnet-4-20250514"


def select_max_iterations(difficulty: str) -> int:
    """Select max ReAct iterations based on difficulty."""

    return {"easy": 2, "medium": 4, "hard": 6}.get(difficulty, 4)
