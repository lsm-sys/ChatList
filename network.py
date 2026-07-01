"""HTTP-запросы к API нейросетей."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx

from db import Database
from models import AIModel, get_adapter_type, validate_model

OPENAI_COMPATIBLE_TYPES = frozenset({"openai", "deepseek", "groq", "openrouter"})

logger = logging.getLogger("chatlist.network")


def _normalize_base_url(api_url: str) -> str:
    return api_url.rstrip("/")


def _build_headers(model: AIModel) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {model.api_key}",
        "Content-Type": "application/json",
    }
    if model.model_type == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/ChatList"
        headers["X-Title"] = "ChatList"
    return headers


def _send_openai_compatible(
    model: AIModel, prompt_text: str, timeout: float
) -> tuple[str, bool]:
    url = f"{_normalize_base_url(model.api_url)}/chat/completions"
    headers = _build_headers(model)
    payload = {
        "model": model.request_model_id,
        "messages": [{"role": "user", "content": prompt_text}],
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)

    if response.status_code == 401:
        return f"[Ошибка] Неверный API-ключ (401) для модели «{model.name}»", False
    if response.status_code >= 400:
        detail = response.text.strip()
        if len(detail) > 500:
            detail = detail[:500] + "…"
        return f"[Ошибка] HTTP {response.status_code}: {detail}", False

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"], True
    except (KeyError, IndexError, TypeError):
        return f"[Ошибка] Неожиданный формат ответа API: {response.text[:300]}", False


def _should_log(db: Database | None) -> bool:
    if db is None:
        return False
    return db.get_setting("log_requests", "0") == "1"


def _write_log(
    db: Database | None,
    model: AIModel,
    prompt_text: str,
    status: str,
    detail: str,
) -> None:
    if not _should_log(db):
        return

    log_file = "chatlist.log"
    if db is not None:
        log_file = db.get_setting("log_file", log_file) or log_file

    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    prompt_preview = prompt_text.replace("\n", " ")[:120]
    line = (
        f"{timestamp}\t{model.name}\t{status}\t{prompt_preview}\t{detail[:200]}\n"
    )
    Path(log_file).open("a", encoding="utf-8").write(line)


def send_prompt(
    model: AIModel,
    prompt_text: str,
    timeout: float = 60.0,
    db: Database | None = None,
) -> str:
    errors = validate_model(model)
    if errors:
        message = f"[Ошибка] {'; '.join(errors)}"
        _write_log(db, model, prompt_text, "validation_error", message)
        return message

    if not prompt_text.strip():
        message = "[Ошибка] Промт пуст"
        _write_log(db, model, prompt_text, "empty_prompt", message)
        return message

    adapter = get_adapter_type(model.model_type)
    if adapter == "openai_compatible" or model.model_type in OPENAI_COMPATIBLE_TYPES:
        try:
            response, ok = _send_openai_compatible(model, prompt_text, timeout)
            _write_log(
                db,
                model,
                prompt_text,
                "ok" if ok else "api_error",
                response if ok else response[:200],
            )
            return response
        except httpx.TimeoutException:
            message = f"[Ошибка] Превышено время ожидания ({timeout} с) для «{model.name}»"
            _write_log(db, model, prompt_text, "timeout", message)
            return message
        except httpx.RequestError as exc:
            message = f"[Ошибка] Сетевая ошибка для «{model.name}»: {exc}"
            _write_log(db, model, prompt_text, "network_error", str(exc))
            return message

    message = f"[Ошибка] Адаптер для типа «{model.model_type}» не реализован"
    _write_log(db, model, prompt_text, "unsupported", message)
    return message


def get_request_timeout(db: Database, default: float = 60.0) -> float:
    raw = db.get_setting("request_timeout", str(int(default)))
    try:
        return float(raw) if raw else default
    except ValueError:
        return default
