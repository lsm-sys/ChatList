# ChatList

Приложение для отправки одного промта в несколько нейросетей и сравнения ответов.

## Требования

- Python 3.11+
- Windows / Linux / macOS

## Установка

```powershell
cd c:\Work\ChatList
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Настройка API-ключей

1. Скопируйте шаблон окружения:

```powershell
Copy-Item .env.example .env
```

2. Откройте `.env` и укажите ключ OpenRouter:

```
OPENROUTER_API_KEY=sk-or-v1-ваш-ключ
```

Ключи хранятся только в `.env`, в базу данных не записываются.

## Первый запуск

```powershell
python main.py
```

При первом запуске создаётся файл `chatlist.db` и добавляются модели OpenRouter по умолчанию:

- GPT-4o Mini
- Claude 3.5 Sonnet
- Gemini 2.0 Flash

## Работа с программой

1. Введите промт или выберите сохранённый из списка.
2. Нажмите **Отправить** — запрос уйдёт во все активные модели.
3. Отметьте нужные ответы и нажмите **Сохранить**.
4. Управляйте моделями через **Данные → Модели**.

### Добавление модели OpenRouter

В **Данные → Модели → Добавить**:

| Поле | Пример |
|------|--------|
| Имя | GPT-4o Mini |
| API URL | `https://openrouter.ai/api/v1` |
| Переменная .env | `OPENROUTER_API_KEY` |
| ID модели API | `openai/gpt-4o-mini` |
| Тип API | `openrouter` |

Список моделей OpenRouter: https://openrouter.ai/models

## Сборка exe

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name ChatList main.py
```

Исполняемый файл: `dist\ChatList.exe`

Положите рядом с exe файлы `.env` и при необходимости `chatlist.db`.

## Структура проекта

| Файл | Назначение |
|------|------------|
| `main.py` | GUI |
| `db.py` | SQLite |
| `models.py` | Конфигурация нейросетей |
| `network.py` | HTTP-запросы к API |
| `workers.py` | Фоновая отправка промтов |
| `dialogs.py` | Диалоги управления |
| `export_utils.py` | Экспорт в Markdown / JSON |

## Дополнительно

- **Файл → Экспорт** — выгрузка выбранных результатов.
- **Настройки → Параметры** — таймаут запросов и логирование в `chatlist.log`.

Подробнее: [PROJECT.md](PROJECT.md), [PLAN.md](PLAN.md), [DATABASE.md](DATABASE.md).
