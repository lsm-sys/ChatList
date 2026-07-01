"""Диалоги управления данными."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from db import Database, ModelRecord, Prompt, Result
from models import SUPPORTED_MODEL_TYPES


class SearchableTableDialog(QDialog):
    def __init__(
        self,
        title: str,
        headers: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(900, 480)

        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Фильтр по таблице…")
        self.search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._all_rows: list[list[str]] = []

    def set_rows(self, rows: list[list[str]]) -> None:
        self._all_rows = rows
        self._apply_filter()

    def _apply_filter(self) -> None:
        query = self.search_edit.text().strip().lower()
        filtered = self._all_rows
        if query:
            filtered = [
                row
                for row in self._all_rows
                if any(query in cell.lower() for cell in row)
            ]

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(filtered))
        for row_idx, row_data in enumerate(filtered):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(value)
                if col_idx == 0 and value.isdigit():
                    item.setData(Qt.ItemDataRole.EditRole, int(value))
                self.table.setItem(row_idx, col_idx, item)
        self.table.setSortingEnabled(True)


class ModelFormDialog(QDialog):
    def __init__(
        self,
        db: Database,
        record: ModelRecord | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.db = db
        self.record = record
        self.setWindowTitle("Редактировать модель" if record else "Добавить модель")

        form = QFormLayout(self)
        self.name_edit = QLineEdit(record.name if record else "")
        self.api_url_edit = QLineEdit(record.api_url if record else "https://openrouter.ai/api/v1")
        self.api_id_env_edit = QLineEdit(record.api_id_env if record else "OPENROUTER_API_KEY")
        self.api_model_edit = QLineEdit(record.api_model if record else "")
        self.api_model_edit.setPlaceholderText("openai/gpt-4o-mini (для OpenRouter)")
        self.type_combo = QComboBox()
        self.type_combo.addItems(sorted(SUPPORTED_MODEL_TYPES))
        if record:
            index = self.type_combo.findText(record.model_type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
        else:
            self.type_combo.setCurrentText("openrouter")
        self.active_check = QCheckBox("Активна")
        self.active_check.setChecked(record.is_active if record else True)

        form.addRow("Имя:", self.name_edit)
        form.addRow("API URL:", self.api_url_edit)
        form.addRow("Переменная .env:", self.api_id_env_edit)
        form.addRow("ID модели API:", self.api_model_edit)
        form.addRow("Тип API:", self.type_combo)
        form.addRow("", self.active_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        api_url = self.api_url_edit.text().strip()
        api_id_env = self.api_id_env_edit.text().strip()
        api_model = self.api_model_edit.text().strip()
        model_type = self.type_combo.currentText()
        is_active = self.active_check.isChecked()

        if not name or not api_url or not api_id_env:
            QMessageBox.warning(self, "Ошибка", "Заполните имя, API URL и переменную .env.")
            return

        try:
            if self.record:
                self.db.update_model(
                    self.record.id,
                    name=name,
                    api_url=api_url,
                    api_id_env=api_id_env,
                    api_model=api_model,
                    model_type=model_type,
                    is_active=is_active,
                )
            else:
                self.db.create_model(
                    name=name,
                    api_url=api_url,
                    api_id_env=api_id_env,
                    api_model=api_model,
                    model_type=model_type,
                    is_active=is_active,
                )
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить модель:\n{exc}")
            return

        self.accept()


class ModelsManagerDialog(QDialog):
    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Модели")
        self.resize(960, 520)

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск моделей…")
        self.search_edit.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search_edit)

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self._add_model)
        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self._edit_model)
        toggle_btn = QPushButton("Вкл/Выкл")
        toggle_btn.clicked.connect(self._toggle_active)
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self._delete_model)
        for btn in (add_btn, edit_btn, toggle_btn, delete_btn):
            toolbar.addWidget(btn)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Имя", "API URL", "Переменная .env", "ID модели API", "Тип", "Активна"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self._edit_model)
        layout.addWidget(self.table)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        layout.addWidget(close_box)

        self.refresh()

    def _selected_id(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return int(item.text()) if item else None

    def refresh(self) -> None:
        search = self.search_edit.text().strip() or None
        models = self.db.list_models(search=search)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(models))
        for row_idx, model in enumerate(models):
            values = [
                str(model.id),
                model.name,
                model.api_url,
                model.api_id_env,
                model.api_model,
                model.model_type,
                "Да" if model.is_active else "Нет",
            ]
            for col_idx, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col_idx == 0:
                    item.setData(Qt.ItemDataRole.EditRole, model.id)
                self.table.setItem(row_idx, col_idx, item)
        self.table.setSortingEnabled(True)

    def _add_model(self) -> None:
        dialog = ModelFormDialog(self.db, parent=self)
        if dialog.exec():
            self.refresh()

    def _edit_model(self) -> None:
        model_id = self._selected_id()
        if model_id is None:
            QMessageBox.information(self, "Модели", "Выберите модель в таблице.")
            return
        record = self.db.get_model(model_id)
        if record is None:
            return
        dialog = ModelFormDialog(self.db, record=record, parent=self)
        if dialog.exec():
            self.refresh()

    def _toggle_active(self) -> None:
        model_id = self._selected_id()
        if model_id is None:
            QMessageBox.information(self, "Модели", "Выберите модель в таблице.")
            return
        record = self.db.get_model(model_id)
        if record is None:
            return
        self.db.set_model_active(model_id, not record.is_active)
        self.refresh()

    def _delete_model(self) -> None:
        model_id = self._selected_id()
        if model_id is None:
            QMessageBox.information(self, "Модели", "Выберите модель в таблице.")
            return
        answer = QMessageBox.question(
            self,
            "Удаление",
            "Удалить выбранную модель?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.delete_model(model_id)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось удалить модель (возможно, есть сохранённые результаты):\n{exc}",
            )
            return
        self.refresh()


class SettingsDialog(QDialog):
    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Настройки")

        form = QFormLayout(self)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 600)
        self.timeout_spin.setSuffix(" с")
        self.timeout_spin.setValue(int(db.get_setting("request_timeout", "60") or "60"))

        self.log_check = QCheckBox("Записывать логи запросов")
        self.log_check.setChecked(db.get_setting("log_requests", "0") == "1")

        self.log_file_edit = QLineEdit(db.get_setting("log_file", "chatlist.log") or "chatlist.log")
        self.db_path_edit = QLineEdit(db.get_setting("db_path", "chatlist.db") or "chatlist.db")
        self.db_path_edit.setReadOnly(True)

        form.addRow("Таймаут запросов:", self.timeout_spin)
        form.addRow("", self.log_check)
        form.addRow("Файл логов:", self.log_file_edit)
        form.addRow("Файл БД:", self.db_path_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self) -> None:
        self.db.set_setting("request_timeout", str(self.timeout_spin.value()))
        self.db.set_setting("log_requests", "1" if self.log_check.isChecked() else "0")
        self.db.set_setting("log_file", self.log_file_edit.text().strip() or "chatlist.log")
        self.accept()


class PromptsDialog(SearchableTableDialog):
    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__("Сохранённые промты", ["ID", "Дата", "Текст", "Теги"], parent)
        self.db = db
        self.table.doubleClicked.connect(self._use_prompt)
        self._prompts: list[Prompt] = []
        self.selected_prompt: Prompt | None = None

        use_btn = QPushButton("Использовать")
        use_btn.clicked.connect(self._use_prompt)
        self.layout().insertWidget(2, use_btn)
        self.refresh()

    def refresh(self) -> None:
        query = self.search_edit.text().strip()
        prompts = self.db.search_prompts(query) if query else self.db.list_prompts()
        self._prompts = prompts
        self.set_rows(
            [[str(p.id), p.created_at, p.text, p.tags or ""] for p in prompts]
        )

    def _apply_filter(self) -> None:
        self.refresh()

    def _use_prompt(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        item = self.table.item(rows[0].row(), 0)
        if item is None:
            return
        prompt_id = int(item.text())
        for prompt in self._prompts:
            if prompt.id == prompt_id:
                self.selected_prompt = prompt
                self.accept()
                return


class ResultsDialog(QDialog):
    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Сохранённые результаты")
        self.resize(960, 520)

        layout = QVBoxLayout(self)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Текст ответа…")
        filters.addWidget(self.search_edit)

        filters.addWidget(QLabel("Модель:"))
        self.model_combo = QComboBox()
        self.model_combo.addItem("Все", None)
        for model in db.list_models():
            self.model_combo.addItem(model.name, model.id)
        filters.addWidget(self.model_combo)

        filters.addWidget(QLabel("Сортировка:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Сначала новые", "saved_at DESC")
        self.sort_combo.addItem("Сначала старые", "saved_at ASC")
        filters.addWidget(self.sort_combo)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.refresh)
        filters.addWidget(refresh_btn)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Дата", "Модель", "Промт", "Ответ"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self.table)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        layout.addWidget(close_box)

        self.search_edit.returnPressed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        model_id = self.model_combo.currentData()
        search = self.search_edit.text().strip() or None
        order_by = self.sort_combo.currentData()
        results = self.db.list_results(
            model_id=model_id,
            search=search,
            order_by=order_by,
        )
        model_names = {m.id: m.name for m in self.db.list_models()}
        prompt_texts = {p.id: p.text[:100] for p in self.db.list_prompts()}
        self._fill_table(results, model_names, prompt_texts)

    def _fill_table(
        self,
        results: list[Result],
        model_names: dict[int, str],
        prompt_texts: dict[int, str],
    ) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(results))
        for row_idx, result in enumerate(results):
            values = [
                str(result.id),
                result.saved_at,
                model_names.get(result.model_id, str(result.model_id)),
                prompt_texts.get(result.prompt_id, str(result.prompt_id)),
                result.response_text,
            ]
            for col_idx, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col_idx == 0:
                    item.setData(Qt.ItemDataRole.EditRole, result.id)
                if col_idx == 4:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                    )
                self.table.setItem(row_idx, col_idx, item)

        min_row_height = 88
        for row_idx in range(len(results)):
            self.table.resizeRowToContents(row_idx)
            if self.table.rowHeight(row_idx) < min_row_height:
                self.table.setRowHeight(row_idx, min_row_height)
        self.table.setSortingEnabled(True)
