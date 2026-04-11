from __future__ import annotations

import json
import os
import time
from typing import Any

from dotenv import load_dotenv

try:
    import anthropic  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    anthropic = None

try:
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    genai = None

load_dotenv()


class _FallbackUsage:
    """Minimal usage object for deterministic fallback responses."""

    input_tokens: int = 0
    output_tokens: int = 0


class _FallbackTextBlock:
    """Simple text block mimicking Anthropic response content."""

    type: str = "text"

    def __init__(self, text: str) -> None:
        """Store text content."""

        self.text = text


class _FallbackResponse:
    """Synthetic response object used when model SDKs are unavailable."""

    def __init__(self, text: str) -> None:
        """Create a deterministic fallback response."""

        self.text = text
        self.stop_reason = "end_turn"
        self.content = [_FallbackTextBlock(text)]
        self.usage = _FallbackUsage()


class _FallbackDelta:
    """Synthetic streamed text delta."""

    def __init__(self, text: str) -> None:
        """Store chunk text."""

        self.text = text


class _FallbackEvent:
    """Synthetic stream event."""

    type: str = "content_block_delta"

    def __init__(self, text: str) -> None:
        """Create a delta event."""

        self.delta = _FallbackDelta(text)


class _FallbackStream:
    """Context-manager stream for deterministic text fallback."""

    def __init__(self, text: str) -> None:
        """Store final text."""

        self._text = text

    def __enter__(self) -> "_FallbackStream":
        """Enter context manager."""

        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Exit context manager."""

        return None

    def __iter__(self) -> Any:
        """Yield a single synthetic streaming event."""

        yield _FallbackEvent(self._text)

    def get_final_message(self) -> _FallbackResponse:
        """Return final fallback message."""

        return _FallbackResponse(self._text)


class AIRouter:
    """Routes tasks to configured AI backends with graceful fallbacks."""

    MODEL_MAP: dict[str, str] = {
        "collector_blood_pdf": "claude",
        "mirror": "claude",
        "time_machine": "claude",
        "coach": "claude",
        "coach_chat": "claude",
        "mental_health": "claude",
        "future_self": "claude",
        "collector_cultfit": "gemini",
        "collector_meal_photo": "gemini",
        "collector_apple_health_summary": "gemini",
        "classify_value": "gemini",
        "spotify_analysis": "gemini",
        "emotional_eating_check": "gemini",
    }

    def __init__(self) -> None:
        """Initialize API clients and fallback cache."""

        self.claude_model: str = os.getenv("EIRVIEW_CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.default_max_tokens: int = int(os.getenv("EIRVIEW_CLAUDE_MAX_TOKENS", "768"))
        self.chat_max_tokens: int = int(os.getenv("EIRVIEW_CLAUDE_CHAT_MAX_TOKENS", "512"))
        self.extraction_max_tokens: int = int(os.getenv("EIRVIEW_CLAUDE_EXTRACTION_MAX_TOKENS", "600"))
        self.anthropic = None
        if anthropic is not None and os.getenv("ANTHROPIC_API_KEY"):
            self.anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        if genai is not None and os.getenv("GEMINI_API_KEY"):
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.gemini = genai.GenerativeModel("gemini-2.5-flash")
            self.gemini_vision = genai.GenerativeModel("gemini-2.5-flash")
        else:
            self.gemini = None
            self.gemini_vision = None
        self.fallbacks: dict[str, Any] = self._load_fallbacks()
        self.call_log: list[dict[str, Any]] = []

    def _load_fallbacks(self) -> dict[str, Any]:
        """Load cached fallback responses if present."""

        path = os.path.join("data", "fallbacks.json")
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {}

    async def route(
        self,
        task: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        image: bytes | None = None,
    ) -> Any:
        """Route a task to the configured model with automatic fallback."""

        max_tokens = self._bounded_max_tokens(max_tokens)
        model = self.MODEL_MAP.get(task, "claude")
        start = time.time()
        try:
            if model == "claude":
                response = self._call_claude(system, messages, tools, max_tokens)
            elif image is not None:
                response = self._call_gemini_vision(system, image, messages)
            else:
                response = self._call_gemini_text(system, messages)
            self._log(task, model, time.time() - start, True)
            return response
        except Exception as exc:  # pragma: no cover - external integrations
            self._log(task, model, time.time() - start, False, str(exc))
            return await self._fallback(task, system, messages, model)

    def _call_claude(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        max_tokens: int,
    ) -> Any:
        """Call Claude or return a deterministic fallback response."""

        if self.anthropic is None:
            return _FallbackResponse(self._deterministic_text(system, messages))
        kwargs: dict[str, Any] = {
            "model": self.claude_model,
            "system": system,
            "messages": messages,
            "max_tokens": self._bounded_max_tokens(max_tokens),
            "timeout": 15,
        }
        if tools:
            kwargs["tools"] = tools
        return self.anthropic.messages.create(**kwargs)

    def _call_gemini_text(self, system: str, messages: list[dict[str, Any]]) -> Any:
        """Call Gemini text or return a deterministic fallback response."""

        if self.gemini is None:
            return _FallbackResponse(self._deterministic_text(system, messages))
        prompt = f"System: {system}\n\nUser: {messages[-1]['content'] if messages else ''}"
        return self.gemini.generate_content(prompt)

    def _call_gemini_vision(self, system: str, image_bytes: bytes, messages: list[dict[str, Any]]) -> Any:
        """Call Gemini vision or return a deterministic fallback response."""

        if self.gemini_vision is None:
            return _FallbackResponse(self._deterministic_text(system, messages))
        import io

        from PIL import Image

        prompt = f"{system}\n\n{messages[-1]['content'] if messages else ''}"
        return self.gemini_vision.generate_content([prompt, Image.open(io.BytesIO(image_bytes))])

    async def _fallback(self, task: str, system: str, messages: list[dict[str, Any]], failed_model: str) -> Any:
        """Attempt the alternate provider, else return cached fallback."""

        try:
            if failed_model == "claude":
                return self._call_gemini_text(system, messages)
            return self._call_claude(system, messages, None, self.default_max_tokens)
        except Exception:
            return self._get_cached(task)

    def stream_claude(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
    ) -> Any:
        """Return a Claude stream if available, else a deterministic stream."""

        if self.anthropic is None:
            return _FallbackStream(self._deterministic_text(system, messages))
        kwargs: dict[str, Any] = {
            "model": self.claude_model,
            "system": system,
            "messages": messages,
            "max_tokens": self._bounded_max_tokens(max_tokens),
        }
        if tools:
            kwargs["tools"] = tools
        return self.anthropic.messages.stream(**kwargs)

    def _bounded_max_tokens(self, requested: int) -> int:
        """Clamp max tokens to a budget-friendly ceiling."""

        return max(128, min(int(requested), self.default_max_tokens))

    def _deterministic_text(self, system: str, messages: list[dict[str, Any]]) -> str:
        """Build a short deterministic response when live models are unavailable."""

        last = messages[-1]["content"] if messages else ""
        return f"AI service fallback response. Prompt context: {system[:140]}. Latest input: {str(last)[:280]}"

    def _log(self, task: str, model: str, latency: float, success: bool, error: str | None = None) -> None:
        """Log a model call for transparency."""

        self.call_log.append(
            {
                "task": task,
                "model": model,
                "latency_ms": int(latency * 1000),
                "success": success,
                "error": error,
                "timestamp": time.time(),
            }
        )

    def _get_cached(self, task: str) -> dict[str, Any]:
        """Return a cached fallback response for a task."""

        return self.fallbacks.get(task, {"text": "Service temporarily unavailable."})


ai_router: AIRouter = AIRouter()
