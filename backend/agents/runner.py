from __future__ import annotations

import json
import os
import re
import tempfile
import time
from datetime import datetime
from typing import Any, AsyncGenerator

from backend.difficulty import classify_difficulty, select_max_iterations
from backend.semantic_cache import check_cache, should_cache, store_cache

MAX_AGENT_ITERATIONS: int = 6

_SHARED_ANSWER_STYLE = """

FINAL ANSWER FORMAT:
- Use markdown bullets or numbered lists instead of long paragraphs whenever possible.
- Preserve every important data point, caveat, and recommendation. Do not drop information to be shorter.
- Keep each bullet tight: usually 1-2 sentences, one idea per bullet.
- If there is a ranked plan or sequence, use a numbered list.
- If there is a direct conclusion, put it first as a short bullet, then the supporting points.
- Avoid walls of prose. Do not write more than 2 consecutive non-list sentences unless the task truly requires it.
"""

_REACT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("thought", re.compile(r"^\*{0,2}Thought:\*{0,2}\s*(.*)$", re.IGNORECASE)),
    ("action", re.compile(r"^\*{0,2}Action:\*{0,2}\s*(.*)$", re.IGNORECASE)),
    ("observation", re.compile(r"^\*{0,2}Observation:\*{0,2}\s*(.*)$", re.IGNORECASE)),
]
_ANSWER_PATTERN = re.compile(r"^\*{0,2}Answer:\*{0,2}\s*(.*)$", re.IGNORECASE)


def _truncate_payload(input_data: dict[str, Any]) -> dict[str, Any]:
    """Trim long chat histories and oversized text before sending to the model."""

    payload = dict(input_data)
    history = payload.get("history")
    if isinstance(history, list):
        payload["history"] = history[-6:]
    message = payload.get("message")
    if isinstance(message, str):
        payload["message"] = message[-1200:]
    return payload


def _sse(payload: dict[str, Any]) -> str:
    """Serialize one SSE event."""

    return f"data: {json.dumps(payload)}\n\n"


def _extract_text_from_blocks(blocks: list[Any]) -> str:
    """Concatenate text blocks from an Anthropic response content list."""

    parts: list[str] = []
    for block in blocks:
        if getattr(block, "type", "") == "text" and getattr(block, "text", ""):
            parts.append(str(block.text))
    return "".join(parts)


def _accumulate_react_trace(trace: list[dict[str, Any]], event_type: str, content: str) -> None:
    """Append a normalized ReAct step to the structured trace."""

    content = str(content or "").strip()
    if not content:
        return
    trace.append(
        {
            "type": event_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
    )


def _flatten_pairs(payload: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """Flatten a nested structure into key/value pairs for short summaries."""

    pairs: list[tuple[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            compound = f"{prefix}.{key}" if prefix else str(key)
            pairs.extend(_flatten_pairs(value, compound))
    elif isinstance(payload, list):
        for index, value in enumerate(payload[:3]):
            compound = f"{prefix}[{index}]" if prefix else f"[{index}]"
            pairs.extend(_flatten_pairs(value, compound))
    else:
        pairs.append((prefix, payload))
    return pairs


def _summarize_tool_result(tool_name: str, result: dict[str, Any]) -> str:
    """Convert a tool result into a short user-readable observation."""

    if not isinstance(result, dict):
        return f"{tool_name} returned a result."
    if tool_name == "get_profile":
        bio = result.get("bio_age_overall")
        sleep = result.get("sleep_hours")
        vitd = result.get("vitamin_d")
        bits = []
        if bio is not None:
            bits.append(f"bio age {bio}")
        if sleep is not None:
            bits.append(f"sleep {sleep}h")
        if vitd is not None:
            bits.append(f"vitamin D {vitd}")
        return f"Retrieved health profile: {', '.join(bits)}." if bits else "Retrieved the user's health profile."
    if tool_name == "mental_wellness_score":
        score = result.get("score")
        breakdown = result.get("breakdown_list") or []
        top = ", ".join(f"{item.get('name')} ({item.get('penalty')})" for item in breakdown[:3] if item.get("name"))
        return f"Mental wellness score: {score}/100. Top penalties: {top}." if score is not None and top else f"Mental wellness score: {score}/100." if score is not None else "Calculated mental wellness score."
    if tool_name == "get_weather":
        temp = result.get("temp_c")
        aqi = result.get("aqi")
        desc = result.get("description") or result.get("label")
        outdoor_ok = result.get("outdoor_ok")
        safety = " Safe for outdoor activity." if outdoor_ok else ""
        bits = [f"{temp}°C" if temp is not None else None, f"AQI {aqi}" if aqi is not None else None, desc]
        return f"Weather: {', '.join(bit for bit in bits if bit)}.{safety}".strip()
    if tool_name == "get_spotify_mood":
        valence = result.get("avg_valence")
        energy = result.get("avg_energy")
        emotion = ((result.get("emotion_class") or {}).get("label") if isinstance(result.get("emotion_class"), dict) else None) or result.get("message")
        bits = []
        if valence is not None:
            bits.append(f"valence {valence}")
        if energy is not None:
            bits.append(f"energy {energy}")
        if emotion:
            bits.append(f"classified as {emotion}")
        return f"Spotify mood: {', '.join(bits)}." if bits else "Retrieved Spotify mood data."
    if tool_name == "calculate_bio_age":
        overall = result.get("overall")
        subs = result.get("sub_ages") or {}
        top = ", ".join(f"{key} {value}" for key, value in list(subs.items())[:2])
        return f"Calculated bio age {overall}. Key subsystem ages: {top}." if overall is not None and top else f"Calculated bio age {overall}." if overall is not None else "Calculated biological age."
    if tool_name == "project_risk":
        projections = result.get("projections") or result
        if isinstance(projections, list) and projections:
            ten_year = next((row for row in projections if int(row.get("year", 0)) == 10), projections[-1])
            return (
                f"Projected risk at year {ten_year.get('year')}: diabetes {round((ten_year.get('diabetes_risk', 0) or 0) * 100, 1)}%, "
                f"heart {round((ten_year.get('cvd_risk', 0) or 0) * 100, 1)}%."
            )
    if tool_name == "simulate_habit_change":
        current = (result.get("current") or {}).get("overall")
        projected = (result.get("projected") or {}).get("overall")
        improvement = result.get("improvement")
        if current is not None and projected is not None:
            return f"Simulation changed bio age from {current} to {projected} ({improvement} years)."
    if result.get("error"):
        return f"{tool_name} returned an error: {result.get('error')}."
    pairs = []
    for key, value in _flatten_pairs(result):
        if value in (None, "", [], {}):
            continue
        if isinstance(value, (dict, list)):
            continue
        short_key = key.split(".")[-1]
        if short_key in {"response", "result", "tool_output", "tool_input"}:
            continue
        pairs.append(f"{short_key} {value}")
        if len(pairs) >= 4:
            break
    return f"{tool_name} result: {', '.join(pairs)}." if pairs else f"{tool_name} returned successfully."


class _ReactStreamParser:
    """Parse streamed ReAct-formatted model text into reasoning and answer events."""

    def __init__(self, trace: list[dict[str, Any]]) -> None:
        self.trace = trace
        self.buffer = ""
        self.in_answer = False
        self.answer_parts: list[str] = []

    def feed(self, chunk: str) -> list[dict[str, Any]]:
        """Consume one streamed text chunk."""

        self.buffer += chunk
        outputs: list[dict[str, Any]] = []
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            outputs.extend(self._handle_line(line))
        return outputs

    def flush(self, final_turn: bool = False) -> list[dict[str, Any]]:
        """Flush any remaining buffered content."""

        outputs = self._handle_line(self.buffer, final_turn=final_turn) if self.buffer else []
        self.buffer = ""
        return outputs

    def _handle_line(self, line: str, final_turn: bool = False) -> list[dict[str, Any]]:
        stripped = line.strip()
        outputs: list[dict[str, Any]] = []
        if not stripped and not (self.in_answer and line):
            return outputs

        if stripped == "---":
            self.in_answer = True
            return outputs

        answer_match = _ANSWER_PATTERN.match(stripped)
        if answer_match:
            self.in_answer = True
            answer_content = answer_match.group(1).strip()
            if answer_content:
                self.answer_parts.append(answer_content)
                outputs.append({"type": "text", "content": answer_content})
            return outputs

        if not self.in_answer:
            for event_type, pattern in _REACT_PATTERNS:
                match = pattern.match(stripped)
                if match:
                    content = match.group(1).strip() or stripped
                    _accumulate_react_trace(self.trace, event_type, content)
                    outputs.append({"type": event_type, "content": content})
                    return outputs
            if final_turn:
                self.in_answer = True
            else:
                _accumulate_react_trace(self.trace, "thought", stripped)
                outputs.append({"type": "thought", "content": stripped})
                return outputs

        if self.in_answer:
            text = line if line else stripped
            self.answer_parts.append(text)
            suffix = "\n" if not final_turn and line else ""
            outputs.append({"type": "text", "content": f"{text}{suffix}"})
        return outputs

    @property
    def answer_text(self) -> str:
        """Return the accumulated final answer text."""

        return "".join(self.answer_parts).strip()


def _parse_react_text(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Parse a complete ReAct response into final answer and reasoning trace."""

    trace: list[dict[str, Any]] = []
    parser = _ReactStreamParser(trace)
    parser.feed(text)
    parser.flush(final_turn=True)
    answer = parser.answer_text or text.strip()
    return answer, trace


async def _build_system_prompt(agent_module: Any, user_id: str, db: Any) -> str:
    """Inject recent reflections into the system prompt for this user/agent."""

    system_prompt = f"{agent_module.SYSTEM_PROMPT}{_SHARED_ANSWER_STYLE}"
    try:
        rows = await (
            await db.execute(
                "SELECT reflection FROM reflections WHERE user_id=? AND agent_type=? AND is_active=1 ORDER BY created_at DESC LIMIT 3",
                (user_id, agent_module.NAME),
            )
        ).fetchall()
    except Exception:
        rows = []
    if not rows:
        return system_prompt
    lessons = "\n".join(f"- {row['reflection']}" for row in rows if row["reflection"])
    return (
        "LESSONS FROM PREVIOUS INTERACTIONS WITH THIS USER:\n"
        f"{lessons}\n\n"
        "Apply these lessons to improve your response. Check for signals you previously missed.\n\n"
        f"{system_prompt}"
    )


async def _get_profile_snapshot(user_id: str, db: Any) -> dict[str, Any] | None:
    """Return the current profile snapshot when available."""

    try:
        row = await (await db.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,))).fetchone()
        return dict(row) if row else None
    except Exception:
        return None


async def _generate_reflection(
    agent_module: Any,
    user_id: str,
    query: str,
    response_text: str,
    traces: list[dict[str, Any]],
    db: Any,
    difficulty: str,
) -> None:
    """Generate a short reflection after medium/hard agent runs."""

    from backend.ai_router import ai_router

    if difficulty == "easy" or agent_module.NAME not in {"coach", "mental_health", "time_machine"}:
        return

    trace_summary = (
        "; ".join(f"{trace.get('tool', '?')}: {str(trace.get('output', ''))[:100]}" for trace in traces[:5])
        if traces
        else "No tools called"
    )
    try:
        reflection_response = ai_router._call_claude(
            system="You are a reflective health AI assistant. Generate a brief reflection.",
            messages=[
                {
                    "role": "user",
                    "content": (
                        f'You just answered this health query: "{query[:200]}"\n\n'
                        f"Tools you called: {trace_summary}\n\n"
                        f"Your answer (summary): {response_text[:300]}\n\n"
                        "In 2-3 sentences, reflect:\n"
                        "1. What context did you check vs what you should have checked?\n"
                        "2. What might you have missed that would make your answer more personalized?\n"
                        "3. What should you do differently next time for this type of query?\n\n"
                        "Be specific about health signals and data points."
                    ),
                }
            ],
            tools=None,
            max_tokens=200,
        )
        reflection_text = _extract_text_from_blocks(getattr(reflection_response, "content", [])).strip()
        if reflection_text:
            await db.execute(
                "INSERT INTO reflections (user_id, agent_type, reflection, query_summary) VALUES (?,?,?,?)",
                (user_id, agent_module.NAME, reflection_text, query[:200]),
            )
            await db.commit()
            await db.execute(
                """
                UPDATE reflections SET is_active = 0
                WHERE user_id = ? AND agent_type = ? AND is_active = 1
                AND id NOT IN (
                    SELECT id FROM reflections
                    WHERE user_id = ? AND agent_type = ? AND is_active = 1
                    ORDER BY created_at DESC LIMIT 10
                )
                """,
                (user_id, agent_module.NAME, user_id, agent_module.NAME),
            )
            await db.commit()
    except Exception:
        return


async def run_agent(agent_module: Any, user_id: str, input_data: dict[str, Any], db: Any) -> dict[str, Any]:
    """Run a bounded Anthropic-style tool-use loop or deterministic fallback."""

    from backend.ai_router import ai_router

    truncated = _truncate_payload(input_data)
    query_text = str(truncated.get("message", "") or "")
    cache_key = str(truncated.get("cache_key", "") or "") or query_text
    profile = await _get_profile_snapshot(user_id, db)
    difficulty = str(truncated.get("difficulty") or classify_difficulty(query_text, profile))
    max_iterations = select_max_iterations(difficulty)
    system_prompt = await _build_system_prompt(agent_module, user_id, db)
    messages: list[dict[str, Any]] = [{"role": "user", "content": json.dumps(truncated)}]
    all_traces: list[dict[str, Any]] = []
    react_trace: list[dict[str, Any]] = []
    total_tokens_in = 0
    total_tokens_out = 0

    for _ in range(max_iterations):
        start = time.time()
        try:
            response = ai_router._call_claude(
                system=system_prompt,
                messages=messages,
                tools=getattr(agent_module, "TOOLS", None),
                max_tokens=500 if difficulty == "easy" else ai_router.default_max_tokens,
            )
        except Exception as exc:
            latency = int((time.time() - start) * 1000)
            fallback_text = ai_router._deterministic_text(system_prompt, messages)
            ai_router._log(agent_module.NAME, ai_router.claude_model, latency / 1000, False, str(exc))
            await db.execute(
                "INSERT INTO agent_logs (user_id, agent_name, action, latency_ms, model, response, difficulty) VALUES (?,?,?,?,?,?,?)",
                (user_id, agent_module.NAME, "error_fallback", latency, ai_router.claude_model, str(exc)[:4000], difficulty),
            )
            await db.commit()
            return {
                "result": fallback_text,
                "traces": all_traces,
                "react_trace": react_trace,
                "difficulty": difficulty,
                "tokens_in": total_tokens_in,
                "tokens_out": total_tokens_out,
                "fallback": True,
                "error": str(exc),
            }

        latency = int((time.time() - start) * 1000)
        usage = getattr(response, "usage", None)
        total_tokens_in += int(getattr(usage, "input_tokens", 0))
        total_tokens_out += int(getattr(usage, "output_tokens", 0))
        await db.execute(
            "INSERT INTO agent_logs (user_id, agent_name, action, tokens_in, tokens_out, latency_ms, model, difficulty) VALUES (?,?,?,?,?,?,?,?)",
            (
                user_id,
                agent_module.NAME,
                "tool_use_round",
                getattr(usage, "input_tokens", 0),
                getattr(usage, "output_tokens", 0),
                latency,
                ai_router.claude_model,
                difficulty,
            ),
        )
        await db.commit()

        response_text = _extract_text_from_blocks(getattr(response, "content", []))
        _, parsed_trace = _parse_react_text(response_text)
        for item in parsed_trace:
            _accumulate_react_trace(react_trace, item["type"], item["content"])

        if getattr(response, "stop_reason", "end_turn") == "end_turn":
            final_text, _ = _parse_react_text(response_text)
            await db.execute(
                "INSERT INTO agent_logs (user_id, agent_name, action, response, tokens_in, tokens_out, latency_ms, model, react_trace, difficulty) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    user_id,
                    agent_module.NAME,
                    "completed",
                    final_text,
                    total_tokens_in,
                    total_tokens_out,
                    latency,
                    ai_router.claude_model,
                    json.dumps(react_trace),
                    difficulty,
                ),
            )
            await db.commit()
            profile_for_cache = await _get_profile_snapshot(user_id, db)
            if profile_for_cache and query_text:
                store_cache(cache_key, final_text, profile_for_cache, agent_module.NAME, difficulty)
            await _generate_reflection(agent_module, user_id, query_text, final_text, all_traces, db, difficulty)
            return {
                "result": final_text,
                "traces": all_traces,
                "react_trace": react_trace,
                "difficulty": difficulty,
                "tokens_in": total_tokens_in,
                "tokens_out": total_tokens_out,
            }

        tool_results: list[dict[str, Any]] = []
        for block in getattr(response, "content", []):
            if getattr(block, "type", "") != "tool_use":
                continue
            action_text = f"Calling {block.name} to gather relevant data."
            _accumulate_react_trace(react_trace, "action", action_text)
            result = await execute_tool(block.name, block.input, user_id, db)
            observation = _summarize_tool_result(block.name, result)
            _accumulate_react_trace(react_trace, "observation", observation)
            trace = {
                "agent": agent_module.NAME,
                "tool": block.name,
                "input": block.input,
                "output": result,
                "timestamp": datetime.now().isoformat(),
            }
            all_traces.append(trace)
            await db.execute(
                "INSERT INTO agent_logs (user_id, agent_name, action, tool_name, tool_input, tool_output, model, difficulty) VALUES (?,?,?,?,?,?,?,?)",
                (
                    user_id,
                    agent_module.NAME,
                    "tool_call",
                    block.name,
                    json.dumps(block.input),
                    json.dumps(result),
                    ai_router.claude_model,
                    difficulty,
                ),
            )
            await db.commit()
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})

        # If no tool calls were made, treat response as final to avoid empty user messages
        if not tool_results:
            text = _extract_text_from_blocks(getattr(response, "content", []))
            final_text, _ = _parse_react_text(text)
            return {
                "result": final_text or text.strip() or "Agent reached max iterations",
                "traces": all_traces,
                "react_trace": react_trace,
                "difficulty": difficulty,
                "tokens_in": total_tokens_in,
                "tokens_out": total_tokens_out,
            }

        messages.append({"role": "assistant", "content": getattr(response, "content", [])})
        messages.append({"role": "user", "content": tool_results})

    return {
        "result": "Agent reached max iterations",
        "traces": all_traces,
        "react_trace": react_trace,
        "difficulty": difficulty,
        "tokens_in": total_tokens_in,
        "tokens_out": total_tokens_out,
    }


async def stream_agent(agent_module: Any, user_id: str, input_data: dict[str, Any], db: Any, close_db: bool = False) -> AsyncGenerator[str, None]:
    """Stream an agent response as SSE using explicit ReAct event types."""

    from backend.ai_router import ai_router

    truncated = _truncate_payload(input_data)
    query_text = str(truncated.get("message", "") or "")
    # Use the raw user message (without prepended context) for cache key
    # so that the same question always matches regardless of page context.
    cache_key = str(truncated.get("cache_key", "") or "") or query_text
    profile = await _get_profile_snapshot(user_id, db)
    difficulty = str(truncated.get("difficulty") or classify_difficulty(query_text, profile))
    max_iterations = select_max_iterations(difficulty)
    system_prompt = await _build_system_prompt(agent_module, user_id, db)
    messages: list[dict[str, Any]] = [{"role": "user", "content": json.dumps(truncated)}]
    react_trace: list[dict[str, Any]] = []
    all_traces: list[dict[str, Any]] = []
    final_text = ""

    try:
        if profile and cache_key and should_cache(agent_module.NAME, profile, difficulty):
            cached = check_cache(cache_key, profile, agent_module.NAME, difficulty)
            if cached:
                await db.execute(
                    "INSERT INTO agent_logs (user_id, agent_name, action, model, response, difficulty) VALUES (?,?,?,?,?,?)",
                    (user_id, agent_module.NAME, "cache_hit", "none", cached, difficulty),
                )
                await db.commit()
                yield _sse({"type": "text", "content": cached})
                yield _sse({"type": "done"})
                return

        for _ in range(max_iterations):
            parser = _ReactStreamParser(react_trace)
            with ai_router.stream_claude(
                system=system_prompt,
                messages=messages,
                tools=getattr(agent_module, "TOOLS", None),
                max_tokens=500 if difficulty == "easy" else ai_router.chat_max_tokens,
            ) as stream:
                for event in stream:
                    if getattr(event, "type", "") == "content_block_delta" and hasattr(event, "delta") and hasattr(event.delta, "text"):
                        for payload in parser.feed(str(event.delta.text)):
                            if payload["type"] == "text":
                                final_text += payload["content"]
                            yield _sse(payload)
                response = stream.get_final_message()

            for payload in parser.flush(final_turn=getattr(response, "stop_reason", "end_turn") == "end_turn"):
                if payload["type"] == "text":
                    final_text += payload["content"]
                yield _sse(payload)

            usage = getattr(response, "usage", None)
            await db.execute(
                "INSERT INTO agent_logs (user_id, agent_name, action, tokens_in, tokens_out, model, difficulty) VALUES (?,?,?,?,?,?,?)",
                (
                    user_id,
                    agent_module.NAME,
                    "stream_round",
                    getattr(usage, "input_tokens", 0),
                    getattr(usage, "output_tokens", 0),
                    ai_router.claude_model,
                    difficulty,
                ),
            )
            await db.commit()

            if getattr(response, "stop_reason", "end_turn") == "end_turn":
                final_text = final_text.strip() or _parse_react_text(_extract_text_from_blocks(getattr(response, "content", [])))[0]
                await db.execute(
                    "INSERT INTO agent_logs (user_id, agent_name, action, response, model, react_trace, difficulty) VALUES (?,?,?,?,?,?,?)",
                    (
                        user_id,
                        agent_module.NAME,
                        "completed",
                        final_text,
                        ai_router.claude_model,
                        json.dumps(react_trace),
                        difficulty,
                    ),
                )
                await db.commit()
                yield _sse({"type": "done"})
                profile_for_cache = await _get_profile_snapshot(user_id, db)
                if profile_for_cache and query_text:
                    store_cache(cache_key, final_text, profile_for_cache, agent_module.NAME, difficulty)
                await _generate_reflection(agent_module, user_id, query_text, final_text, all_traces, db, difficulty)
                return

            tool_results: list[dict[str, Any]] = []
            for block in getattr(response, "content", []):
                if getattr(block, "type", "") != "tool_use":
                    continue
                action_text = f"Calling {block.name} to gather relevant data."
                _accumulate_react_trace(react_trace, "action", action_text)
                yield _sse({"type": "action", "content": action_text})
                result = await execute_tool(block.name, block.input, user_id, db)
                observation = _summarize_tool_result(block.name, result)
                _accumulate_react_trace(react_trace, "observation", observation)
                yield _sse({"type": "observation", "content": observation})
                trace = {
                    "agent": agent_module.NAME,
                    "tool": block.name,
                    "input": block.input,
                    "output": result,
                    "timestamp": datetime.now().isoformat(),
                }
                all_traces.append(trace)
                await db.execute(
                    "INSERT INTO agent_logs (user_id, agent_name, action, tool_name, tool_input, tool_output, model, difficulty) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        user_id,
                        agent_module.NAME,
                        "tool_call",
                        block.name,
                        json.dumps(block.input),
                        json.dumps(result),
                        ai_router.claude_model,
                        difficulty,
                    ),
                )
                await db.commit()
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})

            # If the model stopped (e.g. max_tokens) but made no tool calls,
            # treat the response as final — do NOT append empty messages.
            if not tool_results:
                final_text = final_text.strip() or _parse_react_text(
                    _extract_text_from_blocks(getattr(response, "content", []))
                )[0]
                yield _sse({"type": "done"})
                return

            messages.append({"role": "assistant", "content": getattr(response, "content", [])})
            messages.append({"role": "user", "content": tool_results})

        yield _sse({"type": "done"})
    except Exception as exc:
        # Emit an error message so the frontend gets something visible,
        # then always close the stream cleanly with a done event.
        yield _sse({"type": "text", "content": f"\n\n*An error occurred while generating the response. Please try again.*"})
        yield _sse({"type": "done"})
    finally:
        if close_db and hasattr(db, "close"):
            await db.close()


async def execute_tool(tool_name: str, tool_input: dict[str, Any], user_id: str, db: Any) -> dict[str, Any]:
    """Route tool calls to actual implementations."""

    from backend.agents import coach, collector, mental_health, mirror, time_machine
    from backend.tools import calculation_tools, context_tools, data_tools, spotify_tools

    registry: dict[str, Any] = {
        "calculate_bio_age": calculation_tools.calculate_bio_age,
        "project_risk": calculation_tools.project_risk,
        "simulate_habit_change": calculation_tools.simulate_habit_change,
        "mental_wellness_score": calculation_tools.mental_wellness_score,
        "nutrition_targets": calculation_tools.nutrition_targets,
        "score_meal": calculation_tools.score_meal,
        "workout_targets": calculation_tools.workout_targets,
        "parse_blood_pdf": data_tools.parse_blood_pdf,
        "parse_cultfit_image": data_tools.parse_cultfit_image,
        "parse_apple_health_xml": data_tools.parse_apple_health_xml,
        "validate_ranges": data_tools.validate_ranges,
        "update_profile": data_tools.update_profile,
        "get_profile": context_tools.get_profile,
        "get_weather": context_tools.get_weather,
        "get_nutrition_targets": context_tools.get_nutrition_targets,
        "get_recent_meals": context_tools.get_recent_meals,
        "get_workout_targets": context_tools.get_workout_targets,
        "rank_impact": context_tools.rank_impact,
        "get_reminders": context_tools.get_reminders,
        "check_specialists": context_tools.check_specialists,
        "get_spotify_mood": spotify_tools.get_spotify_mood,
        "get_cross_signals": spotify_tools.get_cross_signals,
    }
    if tool_name == "call_mirror":
        target_user = str(tool_input.get("user_id") or user_id)
        nested = await run_agent(mirror, target_user, {}, db)
        return {"agent": "mirror", **nested}
    if tool_name == "call_time_machine":
        target_user = str(tool_input.get("user_id") or user_id)
        nested = await run_agent(time_machine, target_user, {"changes": tool_input.get("changes", {})}, db)
        return {"agent": "time_machine", **nested}
    if tool_name == "call_coach":
        target_user = str(tool_input.get("user_id") or user_id)
        nested = await run_agent(coach, target_user, {}, db)
        return {"agent": "coach", **nested}
    if tool_name == "call_mental_health":
        target_user = str(tool_input.get("user_id") or user_id)
        nested = await run_agent(mental_health, target_user, {"message": tool_input.get("message", ""), "history": tool_input.get("history", [])}, db)
        return {"agent": "mental_health", **nested}
    if tool_name == "call_collector":
        data_type = str(tool_input.get("data_type", "")).strip().lower()
        content = tool_input.get("content")
        file_path = str(tool_input.get("file_path") or "")
        temp_path = ""
        try:
            if file_path and os.path.exists(file_path):
                temp_path = file_path
            elif isinstance(content, str) and content and os.path.exists(content):
                temp_path = content
            elif isinstance(content, str) and content:
                suffix_map = {"blood_pdf": ".pdf", "cultfit_image": ".txt", "apple_health_xml": ".xml"}
                with tempfile.NamedTemporaryFile("w", delete=False, suffix=suffix_map.get(data_type, ".txt")) as handle:
                    handle.write(content)
                    temp_path = handle.name
            if not temp_path:
                return {"error": "Collector requires file_path or content"}
            if data_type == "blood_pdf":
                parsed = await data_tools.parse_blood_pdf(user_id=user_id, db=db, file_path=temp_path)
            elif data_type == "cultfit_image":
                parsed = await data_tools.parse_cultfit_image(user_id=user_id, db=db, file_path=temp_path)
            elif data_type == "apple_health_xml":
                parsed = await data_tools.parse_apple_health_xml(user_id=user_id, db=db, file_path=temp_path)
            else:
                return {"error": f"Unsupported collector data_type: {data_type}"}
            values = parsed.get("profile_updates", parsed) if isinstance(parsed, dict) else {}
            validations = await data_tools.validate_ranges(user_id=user_id, db=db, values=values if isinstance(values, dict) else {})
            if isinstance(values, dict) and values:
                await data_tools.update_profile(user_id=user_id, db=db, updates=values)
            return {"agent": "collector", "parsed": parsed, "validations": validations}
        finally:
            if temp_path and temp_path != file_path and temp_path != content and os.path.exists(temp_path):
                os.unlink(temp_path)
    handler = registry.get(tool_name)
    if handler is None:
        return {"error": f"Unknown tool: {tool_name}"}
    return await handler(user_id=user_id, db=db, **tool_input)
