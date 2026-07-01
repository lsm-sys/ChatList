"""Доступ к SQLite: CRUD для prompts, models, results, settings."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = "chatlist.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS prompts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL,
    text       TEXT    NOT NULL,
    tags       TEXT
);

CREATE TABLE IF NOT EXISTS models (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    api_url     TEXT    NOT NULL,
    api_id_env  TEXT    NOT NULL,
    api_model   TEXT    NOT NULL DEFAULT '',
    model_type  TEXT    NOT NULL DEFAULT 'openai',
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id     INTEGER NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    model_id      INTEGER NOT NULL REFERENCES models(id) ON DELETE RESTRICT,
    response_text TEXT    NOT NULL,
    saved_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_models_is_active ON models(is_active);
CREATE INDEX IF NOT EXISTS idx_results_prompt_id ON results(prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_id ON results(model_id);
CREATE INDEX IF NOT EXISTS idx_results_saved_at ON results(saved_at);
"""

DEFAULT_SETTINGS: dict[str, str] = {
    "db_path": DEFAULT_DB_PATH,
    "request_timeout": "60",
    "log_requests": "0",
    "log_file": "chatlist.log",
}

OPENROUTER_DEFAULT_MODELS: list[dict[str, str | bool]] = [
    {
        "name": "GPT-4o Mini",
        "api_url": "https://openrouter.ai/api/v1",
        "api_id_env": "OPENROUTER_API_KEY",
        "api_model": "openai/gpt-4o-mini",
        "model_type": "openrouter",
        "is_active": True,
    },
    {
        "name": "Claude Sonnet 4.5",
        "api_url": "https://openrouter.ai/api/v1",
        "api_id_env": "OPENROUTER_API_KEY",
        "api_model": "anthropic/claude-sonnet-4.5",
        "model_type": "openrouter",
        "is_active": True,
    },
    {
        "name": "Gemini 2.5 Flash",
        "api_url": "https://openrouter.ai/api/v1",
        "api_id_env": "OPENROUTER_API_KEY",
        "api_model": "google/gemini-2.5-flash",
        "model_type": "openrouter",
        "is_active": True,
    },
]


@dataclass
class Prompt:
    id: int
    created_at: str
    text: str
    tags: str | None


@dataclass
class ModelRecord:
    id: int
    name: str
    api_url: str
    api_id_env: str
    api_model: str
    model_type: str
    is_active: bool


@dataclass
class Result:
    id: int
    prompt_id: int
    model_id: int
    response_text: str
    saved_at: str


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _row_to_prompt(row: sqlite3.Row) -> Prompt:
    return Prompt(
        id=row["id"],
        created_at=row["created_at"],
        text=row["text"],
        tags=row["tags"],
    )


def _row_to_model(row: sqlite3.Row) -> ModelRecord:
    return ModelRecord(
        id=row["id"],
        name=row["name"],
        api_url=row["api_url"],
        api_id_env=row["api_id_env"],
        api_model=row["api_model"] if "api_model" in row.keys() else row["name"],
        model_type=row["model_type"],
        is_active=bool(row["is_active"]),
    )


def _row_to_result(row: sqlite3.Row) -> Result:
    return Result(
        id=row["id"],
        prompt_id=row["prompt_id"],
        model_id=row["model_id"],
        response_text=row["response_text"],
        saved_at=row["saved_at"],
    )


class Database:
    def __init__(self, path: str | Path = DEFAULT_DB_PATH) -> None:
        self.path = Path(path)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def init_db(self) -> None:
        conn = self.connect()
        conn.executescript(SCHEMA_SQL)
        self._migrate(conn)
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        self._seed_default_models(conn)
        conn.commit()

    def _migrate(self, conn: sqlite3.Connection) -> None:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(models)").fetchall()}
        if "api_model" not in columns:
            conn.execute(
                "ALTER TABLE models ADD COLUMN api_model TEXT NOT NULL DEFAULT ''"
            )

    def _seed_default_models(self, conn: sqlite3.Connection) -> None:
        count = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
        if count > 0:
            return
        for item in OPENROUTER_DEFAULT_MODELS:
            conn.execute(
                """
                INSERT INTO models (name, api_url, api_id_env, api_model, model_type, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item["name"],
                    item["api_url"],
                    item["api_id_env"],
                    item["api_model"],
                    item["model_type"],
                    int(item["is_active"]),
                ),
            )

    # --- settings ---

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self.connect().execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return row["value"]

    def set_setting(self, key: str, value: str) -> None:
        self.connect().execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self.connect().commit()

    def get_all_settings(self) -> dict[str, str | None]:
        rows = self.connect().execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: row["value"] for row in rows}

    # --- prompts ---

    def create_prompt(self, text: str, tags: str | None = None) -> Prompt:
        created_at = _utc_now_iso()
        cursor = self.connect().execute(
            "INSERT INTO prompts (created_at, text, tags) VALUES (?, ?, ?)",
            (created_at, text, tags),
        )
        self.connect().commit()
        return Prompt(id=cursor.lastrowid, created_at=created_at, text=text, tags=tags)

    def get_prompt(self, prompt_id: int) -> Prompt | None:
        row = self.connect().execute(
            "SELECT * FROM prompts WHERE id = ?", (prompt_id,)
        ).fetchone()
        return _row_to_prompt(row) if row else None

    def list_prompts(self, order_by: str = "created_at DESC") -> list[Prompt]:
        allowed = {"created_at DESC", "created_at ASC", "text ASC", "text DESC"}
        if order_by not in allowed:
            order_by = "created_at DESC"
        rows = self.connect().execute(
            f"SELECT * FROM prompts ORDER BY {order_by}"
        ).fetchall()
        return [_row_to_prompt(row) for row in rows]

    def search_prompts(self, query: str) -> list[Prompt]:
        pattern = f"%{query}%"
        rows = self.connect().execute(
            """
            SELECT * FROM prompts
            WHERE text LIKE ? OR IFNULL(tags, '') LIKE ?
            ORDER BY created_at DESC
            """,
            (pattern, pattern),
        ).fetchall()
        return [_row_to_prompt(row) for row in rows]

    def update_prompt(
        self, prompt_id: int, text: str, tags: str | None = None
    ) -> Prompt | None:
        conn = self.connect()
        conn.execute(
            "UPDATE prompts SET text = ?, tags = ? WHERE id = ?",
            (text, tags, prompt_id),
        )
        conn.commit()
        return self.get_prompt(prompt_id)

    def delete_prompt(self, prompt_id: int) -> bool:
        cursor = self.connect().execute(
            "DELETE FROM prompts WHERE id = ?", (prompt_id,)
        )
        self.connect().commit()
        return cursor.rowcount > 0

    # --- models ---

    def create_model(
        self,
        name: str,
        api_url: str,
        api_id_env: str,
        model_type: str = "openai",
        api_model: str = "",
        is_active: bool = True,
    ) -> ModelRecord:
        cursor = self.connect().execute(
            """
            INSERT INTO models (name, api_url, api_id_env, api_model, model_type, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, api_url, api_id_env, api_model or name, model_type, int(is_active)),
        )
        self.connect().commit()
        return self.get_model(cursor.lastrowid)  # type: ignore[return-value]

    def get_model(self, model_id: int) -> ModelRecord | None:
        row = self.connect().execute(
            "SELECT * FROM models WHERE id = ?", (model_id,)
        ).fetchone()
        return _row_to_model(row) if row else None

    def list_models(
        self, active_only: bool = False, search: str | None = None
    ) -> list[ModelRecord]:
        sql = "SELECT * FROM models"
        conditions: list[str] = []
        params: list[Any] = []
        if active_only:
            conditions.append("is_active = 1")
        if search:
            pattern = f"%{search}%"
            conditions.append(
                "(name LIKE ? OR api_url LIKE ? OR api_id_env LIKE ? OR api_model LIKE ? OR model_type LIKE ?)"
            )
            params.extend([pattern] * 5)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY name ASC"
        rows = self.connect().execute(sql, params).fetchall()
        return [_row_to_model(row) for row in rows]

    def get_active_models(self) -> list[ModelRecord]:
        return self.list_models(active_only=True)

    def update_model(
        self,
        model_id: int,
        *,
        name: str | None = None,
        api_url: str | None = None,
        api_id_env: str | None = None,
        api_model: str | None = None,
        model_type: str | None = None,
        is_active: bool | None = None,
    ) -> ModelRecord | None:
        current = self.get_model(model_id)
        if current is None:
            return None

        fields: dict[str, Any] = {
            "name": name if name is not None else current.name,
            "api_url": api_url if api_url is not None else current.api_url,
            "api_id_env": api_id_env if api_id_env is not None else current.api_id_env,
            "api_model": api_model if api_model is not None else current.api_model,
            "model_type": model_type if model_type is not None else current.model_type,
            "is_active": int(is_active if is_active is not None else current.is_active),
        }
        self.connect().execute(
            """
            UPDATE models
            SET name = ?, api_url = ?, api_id_env = ?, api_model = ?, model_type = ?, is_active = ?
            WHERE id = ?
            """,
            (
                fields["name"],
                fields["api_url"],
                fields["api_id_env"],
                fields["api_model"],
                fields["model_type"],
                fields["is_active"],
                model_id,
            ),
        )
        self.connect().commit()
        return self.get_model(model_id)

    def set_model_active(self, model_id: int, is_active: bool) -> ModelRecord | None:
        return self.update_model(model_id, is_active=is_active)

    def delete_model(self, model_id: int) -> bool:
        cursor = self.connect().execute(
            "DELETE FROM models WHERE id = ?", (model_id,)
        )
        self.connect().commit()
        return cursor.rowcount > 0

    # --- results ---

    def create_result(
        self, prompt_id: int, model_id: int, response_text: str
    ) -> Result:
        saved_at = _utc_now_iso()
        cursor = self.connect().execute(
            """
            INSERT INTO results (prompt_id, model_id, response_text, saved_at)
            VALUES (?, ?, ?, ?)
            """,
            (prompt_id, model_id, response_text, saved_at),
        )
        self.connect().commit()
        return Result(
            id=cursor.lastrowid,
            prompt_id=prompt_id,
            model_id=model_id,
            response_text=response_text,
            saved_at=saved_at,
        )

    def get_result(self, result_id: int) -> Result | None:
        row = self.connect().execute(
            "SELECT * FROM results WHERE id = ?", (result_id,)
        ).fetchone()
        return _row_to_result(row) if row else None

    def list_results(
        self,
        prompt_id: int | None = None,
        model_id: int | None = None,
        search: str | None = None,
        order_by: str = "saved_at DESC",
    ) -> list[Result]:
        allowed = {"saved_at DESC", "saved_at ASC"}
        if order_by not in allowed:
            order_by = "saved_at DESC"

        conditions: list[str] = []
        params: list[Any] = []
        if prompt_id is not None:
            conditions.append("results.prompt_id = ?")
            params.append(prompt_id)
        if model_id is not None:
            conditions.append("results.model_id = ?")
            params.append(model_id)
        if search:
            pattern = f"%{search}%"
            conditions.append("results.response_text LIKE ?")
            params.append(pattern)

        sql = "SELECT results.* FROM results"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += f" ORDER BY {order_by}"

        rows = self.connect().execute(sql, params).fetchall()
        return [_row_to_result(row) for row in rows]

    def delete_result(self, result_id: int) -> bool:
        cursor = self.connect().execute(
            "DELETE FROM results WHERE id = ?", (result_id,)
        )
        self.connect().commit()
        return cursor.rowcount > 0


def init_database(path: str | Path = DEFAULT_DB_PATH) -> Database:
    db = Database(path)
    db.init_db()
    return db
