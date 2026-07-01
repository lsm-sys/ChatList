"""Конфигурация и логика нейросетей."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from db import Database, ModelRecord

SUPPORTED_MODEL_TYPES = frozenset({"openai", "deepseek", "groq"})


@dataclass
class AIModel:
    id: int
    name: str
    api_url: str
    api_id_env: str
    model_type: str
    is_active: bool
    api_key: str | None = None

    @classmethod
    def from_record(cls, record: ModelRecord, api_key: str | None = None) -> AIModel:
        return cls(
            id=record.id,
            name=record.name,
            api_url=record.api_url,
            api_id_env=record.api_id_env,
            model_type=record.model_type,
            is_active=record.is_active,
            api_key=api_key,
        )


def get_api_key(env_var_name: str) -> str | None:
    value = os.getenv(env_var_name)
    if value is None or not value.strip():
        return None
    return value.strip()


def validate_model(model: AIModel) -> list[str]:
    errors: list[str] = []
    if not model.is_active:
        errors.append(f"Модель «{model.name}» неактивна")
    if not model.api_url.strip():
        errors.append(f"Модель «{model.name}»: не задан API URL")
    if not model.api_id_env.strip():
        errors.append(f"Модель «{model.name}»: не задано имя переменной окружения")
    elif model.api_key is None:
        errors.append(
            f"Модель «{model.name}»: ключ не найден в .env (переменная {model.api_id_env})"
        )
    if model.model_type not in SUPPORTED_MODEL_TYPES:
        errors.append(
            f"Модель «{model.name}»: неподдерживаемый тип API «{model.model_type}»"
        )
    return errors


def load_model(record: ModelRecord) -> AIModel:
    api_key = get_api_key(record.api_id_env)
    return AIModel.from_record(record, api_key)


def load_models(db: Database, active_only: bool = False) -> list[AIModel]:
    records = db.list_models(active_only=active_only)
    return [load_model(record) for record in records]


def load_active_models(db: Database) -> list[AIModel]:
    return load_models(db, active_only=True)


def get_adapter_type(model_type: str) -> str:
    """Возвращает имя адаптера сети для типа модели."""
    if model_type in SUPPORTED_MODEL_TYPES:
        return "openai_compatible"
    raise ValueError(f"Неподдерживаемый тип модели: {model_type}")


def configure_env(env_path: str | None = None) -> None:
    load_dotenv(env_path)
