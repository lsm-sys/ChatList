# ChatList vX.Y.Z

Краткое описание релиза в 1–2 предложения.

## Что нового

- Пункт изменения 1
- Пункт изменения 2
- Пункт изменения 3

## Исправления

- Исправление 1
- Исправление 2

## Установка (Windows)

1. Скачайте **ChatList-Setup-X.Y.Z.exe** (установщик) или **ChatList-X.Y.Z.exe** (portable).
2. Запустите установщик или portable-файл.
3. Скопируйте `.env.example` в `.env` в папке программы и укажите `OPENROUTER_API_KEY`.

## Системные требования

- Windows 10/11 (64-bit)
- API-ключ [OpenRouter](https://openrouter.ai/)

## Контрольные суммы

Заполните после сборки:

```
ChatList-Setup-X.Y.Z.exe  SHA256: <вставьте хеш>
ChatList-X.Y.Z.exe        SHA256: <вставьте хеш>
```

PowerShell:

```powershell
Get-FileHash "dist\ChatList-Setup-X.Y.Z.exe" -Algorithm SHA256
Get-FileHash "dist\ChatList-X.Y.Z.exe" -Algorithm SHA256
```
