"""AI-ассистент для улучшения промтов."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from db import Database
from models import AIModel, load_model
from network import send_prompt

GOAL_LABELS = {
    "general": "Общее",
    "code": "Код",
    "analysis": "Анализ",
    "creative": "Креатив",
}

SYSTEM_PROMPT = """You are a prompt engineering assistant. Improve user prompts for LLMs.
Respond with ONLY valid JSON (no markdown fences), in this exact schema:
{
  "improved": "single best improved prompt",
  "alternatives": ["alternative 1", "alternative 2"],
  "adaptations": {
    "code": "prompt tuned for coding tasks",
    "analysis": "prompt tuned for analysis tasks",
    "creative": "prompt tuned for creative tasks"
  }
}
Rules:
- Keep the user's language (Russian if input is Russian).
- alternatives: exactly 2 or 3 distinct rephrasings.
- adaptations: all three keys required, even if similar.
- Do not add explanations outside JSON."""


@dataclass
class AssistantResult:
    original: str
    improved: str
    alternatives: list[str] = field(default_factory=list)
    adaptations: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def _goal_instruction(goal: str | None) -> str:
    if not goal or goal == "general":
        return ""
    hints = {
        "code": "Focus improvements on programming, debugging, and code generation.",
        "analysis": "Focus on analytical, structured, data-driven tasks.",
        "creative": "Focus on creative writing, brainstorming, and open-ended tasks.",
    }
    return hints.get(goal, "")


def _extract_json_block(text: str) -> dict | None:
    text = text.strip()
    if not text:
        return None

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()

    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _parse_response(original: str, raw: str) -> AssistantResult:
    if raw.startswith("[Ошибка]"):
        return AssistantResult(
            original=original,
            improved="",
            error=raw,
        )

    data = _extract_json_block(raw)
    if data is None:
        return AssistantResult(
            original=original,
            improved=raw.strip(),
            alternatives=[],
            adaptations={},
        )

    improved = str(data.get("improved", "")).strip() or raw.strip()
    alternatives_raw = data.get("alternatives", [])
    alternatives: list[str] = []
    if isinstance(alternatives_raw, list):
        alternatives = [str(item).strip() for item in alternatives_raw if str(item).strip()][:3]

    adaptations: dict[str, str] = {}
    adaptations_raw = data.get("adaptations", {})
    if isinstance(adaptations_raw, dict):
        for key in ("code", "analysis", "creative"):
            value = adaptations_raw.get(key)
            if value and str(value).strip():
                adaptations[key] = str(value).strip()

    return AssistantResult(
        original=original,
        improved=improved,
        alternatives=alternatives,
        adaptations=adaptations,
    )


def improve_prompt(
    model: AIModel,
    text: str,
    goal: str | None = None,
    timeout: float = 60.0,
    log_enabled: bool = False,
    log_file: str = "chatlist.log",
) -> AssistantResult:
    original = text.strip()
    if not original:
        return AssistantResult(
            original=text,
            improved="",
            error="[Ошибка] Промт пуст",
        )

    goal_hint = _goal_instruction(goal)
    user_message = f"Improve this prompt:\n\n{original}"
    if goal_hint:
        user_message += f"\n\nAdditional focus: {goal_hint}"

    raw = send_prompt(
        model,
        user_message,
        timeout=timeout,
        log_enabled=log_enabled,
        log_file=log_file,
        system_message=SYSTEM_PROMPT,
    )
    return _parse_response(original, raw)


def resolve_assistant_model(db: Database) -> AIModel | None:
    if db.get_setting("assistant_enabled", "1") != "1":
        return None

    model_id_raw = db.get_setting("assistant_model_id", "") or ""
    if model_id_raw.isdigit():
        record = db.get_model(int(model_id_raw))
        if record is not None:
            return load_model(record)

    for record in db.get_active_models():
        if record.name == "GPT-4o Mini":
            return load_model(record)

    active = db.get_active_models()
    if active:
        return load_model(active[0])
    return None


def ensure_assistant_default_model(db: Database) -> None:
    if db.get_setting("assistant_model_id"):
        return
    for record in db.list_models():
        if record.name == "GPT-4o Mini":
            db.set_setting("assistant_model_id", str(record.id))
            return
    active = db.get_active_models()
    if active:
        db.set_setting("assistant_model_id", str(active[0].id))
