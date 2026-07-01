# Схема базы данных ChatList

База данных: **SQLite**, файл по умолчанию — `chatlist.db` в каталоге приложения (путь можно переопределить в `settings`).

Доступ к БД инкапсулирован в модуле `db.py`. API-ключи **не хранятся** в базе — только имя переменной окружения из `.env`.

---

## ER-диаграмма (логическая)

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   prompts   │       │   results   │       │   models    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │───┐   │ id (PK)     │   ┌──│ id (PK)     │
│ created_at  │   └──►│ prompt_id   │   │  │ name        │
│ text        │       │ model_id    │◄──┘  │ api_url     │
│ tags        │       │ response    │      │ api_id_env  │
└─────────────┘       │ saved_at    │      │ model_type  │
                      └─────────────┘      │ is_active   │
                                           └─────────────┘

┌─────────────┐
│  settings   │
├─────────────┤
│ key (PK)    │
│ value       │
└─────────────┘
```

---

## Таблица `prompts`

Хранит сохранённые пользователем запросы (промты).

| Поле         | Тип          | Ограничения              | Описание                                      |
|--------------|--------------|--------------------------|-----------------------------------------------|
| `id`         | INTEGER      | PRIMARY KEY AUTOINCREMENT| Уникальный идентификатор                      |
| `created_at` | TEXT         | NOT NULL                 | Дата и время создания (ISO 8601, UTC)         |
| `text`       | TEXT         | NOT NULL                 | Текст промта                                  |
| `tags`       | TEXT         | NULL                     | Теги через запятую, например: `python, api`   |

**Индексы:**
- `idx_prompts_created_at` — сортировка по дате
- `idx_prompts_text` — полнотекстовый или LIKE-поиск (опционально)

**Пример строки:**

| id | created_at           | text                         | tags        |
|----|----------------------|------------------------------|-------------|
| 1  | 2026-06-30T12:00:00Z | Объясни разницу между async и sync | python |

---

## Таблица `models`

Список нейросетей, доступных для отправки промтов.

| Поле          | Тип     | Ограничения              | Описание                                                |
|---------------|---------|--------------------------|---------------------------------------------------------|
| `id`          | INTEGER | PRIMARY KEY AUTOINCREMENT| Уникальный идентификатор                                |
| `name`        | TEXT    | NOT NULL UNIQUE          | Отображаемое имя модели                                 |
| `api_url`     | TEXT    | NOT NULL                 | Базовый URL API, напр. `https://api.openai.com/v1`      |
| `api_id_env`  | TEXT    | NOT NULL                 | Имя переменной в `.env`, напр. `OPENAI_API_KEY`         |
| `model_type`  | TEXT    | NOT NULL DEFAULT `'openai'` | Тип адаптера: `openai`, `deepseek`, `groq` и т.д.   |
| `is_active`   | INTEGER | NOT NULL DEFAULT 1       | `1` — участвует в отправке, `0` — отключена           |

**Индексы:**
- `idx_models_is_active` — быстрая выборка активных моделей

**Пример строки:**

| id | name       | api_url                          | api_id_env      | model_type | is_active |
|----|------------|----------------------------------|-----------------|------------|-----------|
| 1  | GPT-4o     | https://api.openai.com/v1        | OPENAI_API_KEY  | openai     | 1         |
| 2  | DeepSeek   | https://api.deepseek.com/v1      | DEEPSEEK_API_KEY| deepseek   | 0         |

> **Безопасность:** значение ключа читается из `.env` по имени `api_id_env`. В БД хранится только имя переменной.

---

## Таблица `results`

Постоянное хранение ответов, которые пользователь отметил и сохранил.

| Поле            | Тип     | Ограничения                        | Описание                                      |
|-----------------|---------|------------------------------------|-----------------------------------------------|
| `id`            | INTEGER | PRIMARY KEY AUTOINCREMENT          | Уникальный идентификатор                      |
| `prompt_id`     | INTEGER | NOT NULL, FK → `prompts(id)`       | Связь с промтом                               |
| `model_id`      | INTEGER | NOT NULL, FK → `models(id)`        | Связь с моделью                               |
| `response_text` | TEXT    | NOT NULL                           | Текст ответа нейросети                        |
| `saved_at`      | TEXT    | NOT NULL                           | Дата и время сохранения (ISO 8601, UTC)       |

**Индексы:**
- `idx_results_prompt_id` — выборка результатов по промту
- `idx_results_model_id` — выборка по модели
- `idx_results_saved_at` — сортировка по дате сохранения

**Пример строки:**

| id | prompt_id | model_id | response_text              | saved_at             |
|----|-----------|----------|----------------------------|----------------------|
| 1  | 1         | 1        | Async/await позволяет…     | 2026-06-30T12:05:00Z |

**Поведение при удалении:**
- При удалении промта — каскадное удаление результатов (`ON DELETE CASCADE`) или запрет удаления при наличии результатов (на выбор при реализации).
- При удалении модели — аналогично.

---

## Таблица `settings`

Key-value хранилище настроек приложения.

| Поле    | Тип  | Ограничения | Описание              |
|---------|------|-------------|-----------------------|
| `key`   | TEXT | PRIMARY KEY | Уникальный ключ       |
| `value` | TEXT | NULL        | Значение настройки    |

**Примеры записей:**

| key              | value                          |
|------------------|--------------------------------|
| `db_path`        | `chatlist.db`                  |
| `request_timeout`| `60`                           |
| `default_tags`   | ``                             |
| `log_requests`   | `1`                            |

---

## Временная таблица результатов (не в SQLite)

При отправке промта программа формирует **в памяти** список объектов (не персистентный):

| Поле            | Тип     | Описание                                      |
|-----------------|---------|-----------------------------------------------|
| `model_name`    | str     | Название модели (для отображения)             |
| `model_id`      | int     | ID модели из `models`                         |
| `response_text` | str     | Ответ или текст ошибки                        |
| `selected`      | bool    | Отмечен ли чекбокс пользователем              |

Жизненный цикл:
1. Создаётся после получения ответов от всех активных моделей.
2. Очищается при вводе нового промта или после нажатия «Сохранить».
3. Строки с `selected = True` переносятся в таблицу `results`.

---

## SQL: создание таблиц

```sql
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
```

---

## Начальные данные (seed)

При первом запуске можно добавить настройки по умолчанию:

```sql
INSERT OR IGNORE INTO settings (key, value) VALUES
    ('db_path', 'chatlist.db'),
    ('request_timeout', '60'),
    ('log_requests', '0');
```

Модели пользователь добавляет сам через интерфейс; предзаполнение не обязательно.

---

## Связь с модулями приложения

| Модуль       | Таблицы                          |
|--------------|----------------------------------|
| `db.py`      | все таблицы (CRUD, миграции)     |
| `models.py`  | `models`, чтение `settings`      |
| `network.py` | не обращается к БД напрямую      |
| `main.py`    | через `db.py`: prompts, results  |
