"""HTTP-запросы к API нейросетей."""

from __future__ import annotations

import httpx

from db import Database
from models import AIModel, get_adapter_type, validate_model

OPENAI_COMPATIBLE_TYPES = frozenset({"openai", "deepseek", "groq"})


def _normalize_base_url(api_url: str) -> str:
    return api_url.rstrip("/")


def _send_openai_compatible(
    model: AIModel, prompt_text: str, timeout: float
) -> str:
    url = f"{_normalize_base_url(model.api_url)}/chat/completions"
    headers = {
        "Authorization": f"Bearer {model.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model.name,
        "messages": [{"role": "user", "content": prompt_text}],
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)

    if response.status_code == 401:
        return f"[Ошибка] Неверный API-ключ (401) для модели «{model.name}»"
    if response.status_code >= 400:
        detail = response.text.strip()
        if len(detail) > 500:
            detail = detail[:500] + "…"
        return f"[Ошибка] HTTP {response.status_code}: {detail}"

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return f"[Ошибка] Неожиданный формат ответа API: {response.text[:300]}"


def send_prompt(
    model: AIModel,
    prompt_text: str,
    timeout: float = 60.0,
) -> str:
    errors = validate_model(model)
    if errors:
        return f"[Ошибка] {'; '.join(errors)}"

    if not prompt_text.strip():
        return "[Ошибка] Промт пуст"

    adapter = get_adapter_type(model.model_type)
    if adapter == "openai_compatible" or model.model_type in OPENAI_COMPATIBLE_TYPES:
        try:
            return _send_openai_compatible(model, prompt_text, timeout)
        except httpx.TimeoutException:
            return f"[Ошибка] Превышено время ожидания ({timeout} с) для «{model.name}»"
        except httpx.RequestError as exc:
            return f"[Ошибка] Сетевая ошибка для «{model.name}»: {exc}"

    return f"[Ошибка] Адаптер для типа «{model.model_type}» не реализован"


def get_request_timeout(db: Database, default: float = 60.0) -> float:
    raw = db.get_setting("request_timeout", str(int(default)))
    try:
        return float(raw) if raw else default
    except ValueError:
        return default
