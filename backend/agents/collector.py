from __future__ import annotations

NAME: str = "collector"

SYSTEM_PROMPT: str = """You operate in a ReAct loop. For each user request:

**Thought:** State what you know, what context you need, and your initial assessment.
**Action:** Call a tool to get the data you need.
**Observation:** Note what the result tells you. Identify what is concerning, what is good, and what is missing.
...repeat Thought/Action/Observation as needed (usually 2-4 cycles)...

---
**Answer:** Deliver your final response to the user. Ground EVERY claim in an observation you made. Never assert a number you did not receive from a tool. Be specific — reference exact values.

You parse and validate health data from various sources for EirView.

Parse uploads, validate extracted values, update the profile, and note anomalies or cross-domain concerns."""

TOOLS: list[dict] = [
    {"name": "parse_blood_pdf", "description": "Extract blood report lab values.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
    {"name": "parse_cultfit_image", "description": "Extract body composition from Cult.fit screenshots.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
    {"name": "parse_apple_health_xml", "description": "Extract Apple Health metrics from export.xml.", "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
    {"name": "validate_ranges", "description": "Validate values against reference ranges.", "input_schema": {"type": "object", "properties": {"values": {"type": "object"}}, "required": ["values"]}},
    {"name": "update_profile", "description": "Update the user's profile with extracted values.", "input_schema": {"type": "object", "properties": {"updates": {"type": "object"}}, "required": ["updates"]}},
]
