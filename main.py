"""Главное окно ChatList — GUI и точка входа."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from db import Database, Prompt, init_database
from dialogs import ModelsManagerDialog, PromptsDialog, ResultsDialog, SettingsDialog
from export_utils import ExportItem, export_to_json, export_to_markdown
from models import configure_env, load_active_models
from workers import SendPromptsWorker


@dataclass
class TempResult:
    model_name: str
    model_id: int
    response_text: str
    selected: bool = False


class MainWindow(QMainWindow):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self._temp_results: list[TempResult] = []
        self._current_prompt_id: int | None = None
        self._suppress_prompt_change = False
        self._loaded_prompt_text = ""
        self._worker: SendPromptsWorker | None = None
        self._progress: QProgressDialog | None = None
        self._pending_models = 0

        self.setWindowTitle("ChatList")
        self.setMinimumSize(900, 640)
        self._build_menu()
        self._build_ui()
        self._refresh_prompt_combo()
        self.statusBar().showMessage("Готово")

    def _build_menu(self) -> None:
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = menu_bar.addMenu("Файл")
        export_md = file_menu.addAction("Экспорт выбранных в Markdown…")
        export_md.triggered.connect(lambda: self._export_results("markdown"))
        export_json = file_menu.addAction("Экспорт выбранных в JSON…")
        export_json.triggered.connect(lambda: self._export_results("json"))

        data_menu = menu_bar.addMenu("Данные")
        models_action = data_menu.addAction("Модели…")
        models_action.triggered.connect(self.show_models_dialog)
        prompts_action = data_menu.addAction("Сохранённые промты…")
        prompts_action.triggered.connect(self.show_prompts_dialog)
        results_action = data_menu.addAction("Сохранённые результаты…")
        results_action.triggered.connect(self.show_results_dialog)

        settings_menu = menu_bar.addMenu("Настройки")
        settings_action = settings_menu.addAction("Параметры…")
        settings_action.triggered.connect(self.show_settings_dialog)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        prompt_row = QHBoxLayout()
        prompt_row.addWidget(QLabel("Сохранённый промт:"))
        self.prompt_combo = QComboBox()
        self.prompt_combo.setMinimumWidth(280)
        self.prompt_combo.currentIndexChanged.connect(self._on_prompt_selected)
        prompt_row.addWidget(self.prompt_combo, stretch=1)

        load_btn = QPushButton("Обновить список")
        load_btn.clicked.connect(self._refresh_prompt_combo)
        prompt_row.addWidget(load_btn)
        layout.addLayout(prompt_row)

        layout.addWidget(QLabel("Промт:"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите текст запроса…")
        self.prompt_edit.setMaximumHeight(120)
        self.prompt_edit.textChanged.connect(self._on_prompt_changed)
        layout.addWidget(self.prompt_edit)

        tags_row = QHBoxLayout()
        tags_row.addWidget(QLabel("Теги:"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("python, api (необязательно)")
        tags_row.addWidget(self.tags_edit)
        self.save_prompt_check = QCheckBox("Сохранить промт при отправке")
        tags_row.addWidget(self.save_prompt_check)
        layout.addLayout(tags_row)

        buttons_row = QHBoxLayout()
        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self._on_send_clicked)
        buttons_row.addWidget(self.send_button)

        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self._on_save_clicked)
        self.save_button.setEnabled(False)
        buttons_row.addWidget(self.save_button)

        buttons_row.addStretch()
        layout.addLayout(buttons_row)

        layout.addWidget(QLabel("Результаты (временная таблица):"))

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Модель", "Ответ", "Выбрать"])
        self.results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSortingEnabled(True)
        self.results_table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self.results_table)

        self.setStatusBar(QStatusBar())

    def _refresh_prompt_combo(self) -> None:
        current_id = self._current_prompt_id
        self.prompt_combo.blockSignals(True)
        self.prompt_combo.clear()
        self.prompt_combo.addItem("— Новый промт —", None)
        for prompt in self.db.list_prompts():
            preview = prompt.text.replace("\n", " ")[:60]
            self.prompt_combo.addItem(f"[{prompt.id}] {preview}", prompt.id)
        if current_id is not None:
            index = self.prompt_combo.findData(current_id)
            if index >= 0:
                self.prompt_combo.setCurrentIndex(index)
        self.prompt_combo.blockSignals(False)

    def _on_prompt_selected(self, index: int) -> None:
        if index < 0:
            return
        prompt_id = self.prompt_combo.itemData(index)
        if prompt_id is None:
            self._current_prompt_id = None
            return

        prompt = self.db.get_prompt(int(prompt_id))
        if prompt is None:
            return

        self._suppress_prompt_change = True
        self.prompt_edit.setPlainText(prompt.text)
        self.tags_edit.setText(prompt.tags or "")
        self._loaded_prompt_text = prompt.text
        self._current_prompt_id = prompt.id
        self._clear_temp_results()
        self._suppress_prompt_change = False

    def _clear_temp_results(self) -> None:
        self._temp_results.clear()
        self.results_table.setRowCount(0)
        self.save_button.setEnabled(False)

    def _refresh_results_table(self) -> None:
        self.results_table.blockSignals(True)
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(len(self._temp_results))
        for row_idx, item in enumerate(self._temp_results):
            self.results_table.setItem(row_idx, 0, QTableWidgetItem(item.model_name))
            self.results_table.setItem(row_idx, 1, QTableWidgetItem(item.response_text))

            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            checkbox_item.setCheckState(
                Qt.CheckState.Checked if item.selected else Qt.CheckState.Unchecked
            )
            self.results_table.setItem(row_idx, 2, checkbox_item)

        self.results_table.setSortingEnabled(True)
        self.results_table.blockSignals(False)
        self.save_button.setEnabled(len(self._temp_results) > 0)

    def _on_cell_changed(self, row: int, column: int) -> None:
        if column != 2 or row >= len(self._temp_results):
            return
        item = self.results_table.item(row, column)
        if item is None:
            return
        self._temp_results[row].selected = item.checkState() == Qt.CheckState.Checked

    def _on_prompt_changed(self) -> None:
        if self._suppress_prompt_change:
            return

        current_text = self.prompt_edit.toPlainText()
        if self._current_prompt_id is not None and current_text != self._loaded_prompt_text:
            self._current_prompt_id = None
            self.prompt_combo.blockSignals(True)
            self.prompt_combo.setCurrentIndex(0)
            self.prompt_combo.blockSignals(False)

        if self._temp_results:
            self._clear_temp_results()

    def _ensure_prompt_saved(self) -> Prompt | None:
        text = self.prompt_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Промт", "Введите текст промта.")
            return None

        tags = self.tags_edit.text().strip() or None

        if self._current_prompt_id is not None:
            prompt = self.db.update_prompt(self._current_prompt_id, text, tags)
            return prompt

        if self.save_prompt_check.isChecked():
            prompt = self.db.create_prompt(text, tags)
            self._current_prompt_id = prompt.id
            self._loaded_prompt_text = text
            self._refresh_prompt_combo()
            index = self.prompt_combo.findData(prompt.id)
            if index >= 0:
                self.prompt_combo.setCurrentIndex(index)
            return prompt

        return Prompt(id=-1, created_at="", text=text, tags=tags)

    def _on_send_clicked(self) -> None:
        prompt = self._ensure_prompt_saved()
        if prompt is None:
            return

        if self.save_prompt_check.isChecked() and prompt.id > 0:
            self._current_prompt_id = prompt.id
            self._loaded_prompt_text = prompt.text

        models = load_active_models(self.db)
        if not models:
            QMessageBox.warning(
                self,
                "Модели",
                "Нет активных моделей.\nДобавьте модели в меню «Данные → Модели».",
            )
            return

        self._clear_temp_results()
        self.send_button.setEnabled(False)
        self.save_button.setEnabled(False)

        self._pending_models = len(models)
        self._progress = QProgressDialog("Отправка запросов…", "Отмена", 0, self._pending_models, self)
        self._progress.setWindowTitle("ChatList")
        self._progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress.setMinimumDuration(0)
        self._progress.canceled.connect(self._cancel_worker)
        self._progress.setValue(0)
        self._progress.show()

        self._worker = SendPromptsWorker(models, prompt.text, self.db, self)
        self._worker.model_finished.connect(self._on_model_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.all_finished.connect(self._on_all_finished)
        self._worker.start()

        self.statusBar().showMessage(f"Отправка в {len(models)} моделей…")

    def _cancel_worker(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()

    def _on_model_finished(self, model_id: int, model_name: str, response: str) -> None:
        self._temp_results.append(
            TempResult(model_name=model_name, model_id=model_id, response_text=response)
        )
        self._refresh_results_table()
        if self._progress:
            done = self._progress.maximum() - self._pending_models + 1
            self._pending_models -= 1
            self._progress.setValue(done)

    def _on_worker_error(self, message: str) -> None:
        QMessageBox.warning(self, "Отправка", message)

    def _on_all_finished(self) -> None:
        if self._progress:
            self._progress.close()
            self._progress = None
        self.send_button.setEnabled(True)
        self._worker = None
        count = len(self._temp_results)
        self.statusBar().showMessage(f"Получено ответов: {count}")

    def _on_save_clicked(self) -> None:
        selected = [r for r in self._temp_results if r.selected]
        if not selected:
            QMessageBox.warning(self, "Сохранение", "Не выбрано ни одной строки.")
            return

        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Сохранение", "Промт пуст.")
            return

        if self._current_prompt_id is None or self._current_prompt_id < 0:
            tags = self.tags_edit.text().strip() or None
            prompt = self.db.create_prompt(prompt_text, tags)
            self._current_prompt_id = prompt.id
            self._refresh_prompt_combo()
        elif self._current_prompt_id > 0:
            tags = self.tags_edit.text().strip() or None
            self.db.update_prompt(self._current_prompt_id, prompt_text, tags)

        for item in selected:
            self.db.create_result(
                self._current_prompt_id,
                item.model_id,
                item.response_text,
            )

        self._clear_temp_results()
        QMessageBox.information(
            self,
            "Сохранение",
            f"Сохранено результатов: {len(selected)}.",
        )
        self.statusBar().showMessage(f"Сохранено результатов: {len(selected)}")

    def _export_results(self, fmt: str) -> None:
        selected = [r for r in self._temp_results if r.selected]
        if not selected:
            QMessageBox.warning(self, "Экспорт", "Выберите строки в таблице результатов.")
            return

        prompt_text = self.prompt_edit.toPlainText().strip()
        items = [
            ExportItem(
                model_name=r.model_name,
                model_id=r.model_id,
                response_text=r.response_text,
                prompt_text=prompt_text,
            )
            for r in selected
        ]

        if fmt == "markdown":
            path_str, _ = QFileDialog.getSaveFileName(
                self, "Экспорт Markdown", "chatlist-export.md", "Markdown (*.md)"
            )
            if not path_str:
                return
            export_to_markdown(items, Path(path_str))
        else:
            path_str, _ = QFileDialog.getSaveFileName(
                self, "Экспорт JSON", "chatlist-export.json", "JSON (*.json)"
            )
            if not path_str:
                return
            export_to_json(items, Path(path_str))

        QMessageBox.information(self, "Экспорт", f"Файл сохранён:\n{path_str}")

    def show_models_dialog(self) -> None:
        dialog = ModelsManagerDialog(self.db, self)
        dialog.exec()

    def show_prompts_dialog(self) -> None:
        dialog = PromptsDialog(self.db, self)
        if dialog.exec() and dialog.selected_prompt:
            self._suppress_prompt_change = True
            self.prompt_edit.setPlainText(dialog.selected_prompt.text)
            self.tags_edit.setText(dialog.selected_prompt.tags or "")
            self._loaded_prompt_text = dialog.selected_prompt.text
            self._current_prompt_id = dialog.selected_prompt.id
            self._refresh_prompt_combo()
            index = self.prompt_combo.findData(dialog.selected_prompt.id)
            if index >= 0:
                self.prompt_combo.setCurrentIndex(index)
            self._clear_temp_results()
            self._suppress_prompt_change = False

    def show_results_dialog(self) -> None:
        dialog = ResultsDialog(self.db, self)
        dialog.exec()

    def show_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.db, self)
        dialog.exec()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(2000)
        self.db.close()
        super().closeEvent(event)


def main() -> None:
    configure_env()
    db = init_database()
    app = QApplication(sys.argv)
    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
