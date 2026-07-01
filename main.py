"""Главное окно ChatList — GUI и точка входа."""

from __future__ import annotations

import sys
from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from db import Database, init_database
from models import configure_env


@dataclass
class TempResult:
    """Временная строка результатов в памяти (не в SQLite)."""

    model_name: str
    model_id: int
    response_text: str
    selected: bool = False


class ListDialog(QDialog):
    def __init__(
        self,
        title: str,
        headers: list[str],
        rows: list[list[str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 400)

        layout = QVBoxLayout(self)
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        for row_idx, row_data in enumerate(rows):
            for col_idx, value in enumerate(row_data):
                table.setItem(row_idx, col_idx, QTableWidgetItem(value))

        layout.addWidget(table)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self._temp_results: list[TempResult] = []

        self.setWindowTitle("ChatList")
        self.setMinimumSize(800, 600)
        self._build_menu()
        self._build_ui()

    def _build_menu(self) -> None:
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        data_menu = menu_bar.addMenu("Данные")
        models_action = data_menu.addAction("Модели")
        models_action.triggered.connect(self.show_models_dialog)

        prompts_action = data_menu.addAction("Сохранённые промты")
        prompts_action.triggered.connect(self.show_prompts_dialog)

        results_action = data_menu.addAction("Сохранённые результаты")
        results_action.triggered.connect(self.show_results_dialog)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        prompt_label = QLabel("Промт:")
        layout.addWidget(prompt_label)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите текст запроса…")
        self.prompt_edit.setMaximumHeight(120)
        self.prompt_edit.textChanged.connect(self._on_prompt_changed)
        layout.addWidget(self.prompt_edit)

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

        results_label = QLabel("Результаты (временная таблица):")
        layout.addWidget(results_label)

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
        self.results_table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self.results_table)

    def _clear_temp_results(self) -> None:
        self._temp_results.clear()
        self.results_table.setRowCount(0)
        self.save_button.setEnabled(False)

    def _refresh_results_table(self) -> None:
        self.results_table.blockSignals(True)
        self.results_table.setRowCount(len(self._temp_results))
        for row_idx, item in enumerate(self._temp_results):
            self.results_table.setItem(
                row_idx, 0, QTableWidgetItem(item.model_name)
            )
            self.results_table.setItem(
                row_idx, 1, QTableWidgetItem(item.response_text)
            )

            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            checkbox_item.setCheckState(
                Qt.CheckState.Checked if item.selected else Qt.CheckState.Unchecked
            )
            self.results_table.setItem(row_idx, 2, checkbox_item)

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
        pass

    def _on_send_clicked(self) -> None:
        QMessageBox.information(
            self,
            "Отправка",
            "Отправка запросов будет реализована на этапе 7.",
        )

    def _on_save_clicked(self) -> None:
        selected = [r for r in self._temp_results if r.selected]
        if not selected:
            QMessageBox.warning(self, "Сохранение", "Не выбрано ни одной строки.")
            return
        QMessageBox.information(
            self,
            "Сохранение",
            "Сохранение результатов будет реализовано на этапе 8.",
        )

    def show_models_dialog(self) -> None:
        models = self.db.list_models()
        rows = [
            [
                str(m.id),
                m.name,
                m.api_url,
                m.api_id_env,
                m.model_type,
                "Да" if m.is_active else "Нет",
            ]
            for m in models
        ]
        dialog = ListDialog(
            "Модели",
            ["ID", "Имя", "API URL", "Переменная .env", "Тип", "Активна"],
            rows,
            self,
        )
        dialog.exec()

    def show_prompts_dialog(self) -> None:
        prompts = self.db.list_prompts()
        rows = [
            [str(p.id), p.created_at, p.text, p.tags or ""]
            for p in prompts
        ]
        dialog = ListDialog(
            "Сохранённые промты",
            ["ID", "Дата", "Текст", "Теги"],
            rows,
            self,
        )
        dialog.exec()

    def show_results_dialog(self) -> None:
        results = self.db.list_results()
        model_names = {m.id: m.name for m in self.db.list_models()}
        prompt_texts = {p.id: p.text[:80] for p in self.db.list_prompts()}
        rows = [
            [
                str(r.id),
                r.saved_at,
                model_names.get(r.model_id, str(r.model_id)),
                prompt_texts.get(r.prompt_id, str(r.prompt_id)),
                r.response_text[:200],
            ]
            for r in results
        ]
        dialog = ListDialog(
            "Сохранённые результаты",
            ["ID", "Дата", "Модель", "Промт", "Ответ"],
            rows,
            self,
        )
        dialog.exec()

    def closeEvent(self, event) -> None:  # type: ignore[override]
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
