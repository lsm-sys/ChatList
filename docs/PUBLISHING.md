# Публикация ChatList на GitHub Release и GitHub Pages

Пошаговая инструкция для выпуска новой версии приложения.

Репозиторий: **https://github.com/lsm-sys/ChatList**  
Сайт (Pages): **https://lsm-sys.github.io/ChatList/**

---

## Что уже подготовлено в репозитории

| Файл / папка | Назначение |
|--------------|------------|
| `version.py` | Единый номер версии (`__version__`) |
| `build.ps1` | Сборка exe и установщика |
| `publish-release.ps1` | Автоматическая публикация релиза |
| `docs/index.html` | HTML-лендинг для GitHub Pages |
| `docs/release-notes/TEMPLATE.md` | Шаблон заметок к релизу |
| `docs/release-notes/v1.0.1.md` | Заметки к текущему релизу |
| `.github/workflows/pages.yml` | Автодеплой лендинга при push в `main` |

---

## Предварительные требования

Установите один раз:

```powershell
winget install GitHub.cli
winget install JRSoftware.InnoSetup
pip install pyinstaller
gh auth login
```

Проверка:

```powershell
gh auth status
python --version
```

---

## Часть 1. Подготовка новой версии

### Шаг 1. Обновите номер версии

Откройте `version.py` и измените `__version__`:

```python
__version__ = "1.0.0"
```

Версия автоматически попадёт в exe, установщик, интерфейс и логи.

### Шаг 2. Создайте заметки к релизу

Скопируйте шаблон:

```powershell
Copy-Item docs\release-notes\TEMPLATE.md docs\release-notes\v1.0.0.md
```

Замените `X.Y.Z` на актуальную версию и опишите изменения.

### Шаг 3. Соберите артефакты

```powershell
.\build.ps1
```

Проверьте результат:

```powershell
Get-ChildItem dist\ChatList*
```

Ожидаемые файлы:

- `dist\ChatList-1.0.0.exe` — portable
- `dist\ChatList-Setup-1.0.0.exe` — установщик

### Шаг 4. Проверьте установщик локально

```powershell
Start-Process dist\ChatList-Setup-1.0.0.exe
```

Убедитесь, что программа запускается и удаляется через «Удалить ChatList».

---

## Часть 2. GitHub Release (ручной способ)

### Шаг 1. Закоммитьте и отправьте код

```powershell
git add version.py docs\release-notes\v1.0.0.md
git commit -m "Версия 1.0.0"
git push origin main
```

### Шаг 2. Создайте тег

```powershell
git tag -a v1.0.0 -m "ChatList 1.0.0"
git push origin v1.0.0
```

### Шаг 3. Создайте Release на GitHub

**Через веб-интерфейс:**

1. Откройте https://github.com/lsm-sys/ChatList/releases
2. Нажмите **Draft a new release**
3. Выберите тег `v1.0.0`
4. Заголовок: `ChatList 1.0.0`
5. Вставьте текст из `docs\release-notes\v1.0.0.md`
6. Прикрепите файлы:
   - `dist\ChatList-Setup-1.0.0.exe`
   - `dist\ChatList-1.0.0.exe`
7. Нажмите **Publish release**

**Через GitHub CLI:**

```powershell
gh release create v1.0.0 `
  --title "ChatList 1.0.0" `
  --notes-file docs\release-notes\v1.0.0.md `
  dist\ChatList-Setup-1.0.0.exe `
  dist\ChatList-1.0.0.exe
```

### Шаг 4. Добавьте контрольные суммы (рекомендуется)

```powershell
Get-FileHash dist\ChatList-Setup-1.0.0.exe -Algorithm SHA256
Get-FileHash dist\ChatList-1.0.0.exe -Algorithm SHA256
```

Вставьте хеши в описание релиза в блок «Контрольные суммы».

---

## Часть 2 (альтернатива). Автоматическая публикация

Один скрипт выполняет сборку, тег, push тега и Release:

```powershell
.\publish-release.ps1
```

Скрипт сам возьмёт версию из `version.py` и отправит тег `vX.Y.Z` на GitHub.
Отдельный `git push origin v...` нужен только если вы создавали тег вручную.

---

## Часть 3. GitHub Pages (лендинг)

### Шаг 1. Включите Pages в настройках репозитория

1. Откройте https://github.com/lsm-sys/ChatList/settings/pages
2. **Source:** Deploy from a branch → **GitHub Actions**  
   *(workflow `.github/workflows/pages.yml` уже настроен)*

Если Actions недоступны, выберите:

- Branch: `main`
- Folder: `/docs`

### Шаг 2. Отправьте лендинг в репозиторий

```powershell
git add docs\index.html docs\assets docs\.nojekyll docs\PUBLISHING.md .github\workflows\pages.yml
git commit -m "Добавить лендинг и инструкцию публикации"
git push origin main
```

### Шаг 3. Проверьте деплой

1. Откройте вкладку **Actions** в репозитории
2. Дождитесь успешного workflow **Deploy GitHub Pages**
3. Откройте https://lsm-sys.github.io/ChatList/

Лендинг автоматически подтягивает последний релиз через GitHub API (кнопки «Скачать»).

### Шаг 4. Обновите лендинг при новой версии

При смене версии достаточно опубликовать Release — скрипт на странице сам обновит ссылки.  
При изменении дизайна или текста — отредактируйте `docs/index.html` и сделайте push.

---

## Чеклист перед каждым релизом

- [ ] `__version__` обновлён в `version.py`
- [ ] Создан `docs/release-notes/vX.Y.Z.md`
- [ ] `.\build.ps1` завершился без ошибок
- [ ] Установщик и portable протестированы на Windows
- [ ] Код закоммичен и запушен в `main`
- [ ] Создан тег `vX.Y.Z`
- [ ] GitHub Release опубликован с обоими `.exe`
- [ ] SHA256-хеши добавлены в описание релиза
- [ ] GitHub Pages отображает актуальную версию

---

## Именование файлов релиза

Имена формируются из `version.py` — **не меняйте вручную**:

| Файл | Пример |
|------|--------|
| Portable | `ChatList-1.0.0.exe` |
| Установщик | `ChatList-Setup-1.0.0.exe` |
| Тег Git | `v1.0.0` |

Ссылки для лендинга (после публикации):

```
https://github.com/lsm-sys/ChatList/releases/latest/download/ChatList-Setup-1.0.0.exe
https://github.com/lsm-sys/ChatList/releases/latest/download/ChatList-1.0.0.exe
```

---

## Частые проблемы

| Проблема | Решение |
|----------|---------|
| `ISCC.exe not found` | `winget install JRSoftware.InnoSetup` |
| Pages не открывается | Проверьте Settings → Pages, подождите 1–2 мин после Actions |
| 404 на скачивание | Убедитесь, что Release опубликован (не Draft) и имена файлов совпадают |
| `gh: not authenticated` | `gh auth login` |
| Кириллица в `build.ps1` ломается | Используйте ASCII-сообщения в скрипте (уже исправлено) |

---

## Полезные ссылки

- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [GitHub Pages](https://docs.github.com/en/pages)
- [Inno Setup](https://jrsoftware.org/isinfo.php)
- [PyInstaller](https://pyinstaller.org/)
