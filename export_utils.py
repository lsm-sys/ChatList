"""Экспорт выбранных результатов."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class ExportItem:
    model_name: str
    model_id: int
    response_text: str
    prompt_text: str


def export_to_markdown(items: list[ExportItem], path: Path) -> None:
    lines = [f"# ChatList export — {datetime.now(UTC).date().isoformat()}", ""]
    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                f"## {index}. {item.model_name}",
                "",
                "### Промт",
                "",
                item.prompt_text,
                "",
                "### Ответ",
                "",
                item.response_text,
                "",
                "---",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def export_to_json(items: list[ExportItem], path: Path) -> None:
    payload = {
        "exported_at": datetime.now(UTC).replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "items": [asdict(item) for item in items],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
