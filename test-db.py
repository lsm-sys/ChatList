"""Тестовый просмотр SQLite: список таблиц, пагинация, CRUD."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

DEFAULT_DB = "chatlist.db"
PAGE_SIZE = 25


class RowEditDialog(QDialog):
    def __init__(
        self,
        columns: list[str],
        values: dict[str, str | None] | None = None,
        title: str = "Запись",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._columns = columns
        self._fields: dict[str, QLineEdit] = {}

        layout = QFormLayout(self)
        for column in columns:
            field = QLineEdit()
            if values and values.get(column) is not None:
                field.setText(str(values[column]))
            self._fields[column] = field
            layout.addRow(f"{column}:", field)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> dict[str, str]:
        return {column: field.text() for column, field in self._fields.items()}


class TableViewWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._conn: sqlite3.Connection | None = None
        self._table_name = ""
        self._columns: list[str] = []
        self._page = 0
        self._page_size = PAGE_SIZE
        self._total_rows = 0

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.title_label = QLabel("Таблица не выбрана")
        header.addWidget(self.title_label)
        header.addStretch()
        layout.addLayout(header)

        self.table = QTableWidget(0, 0)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        pagination = QHBoxLayout()
        self.prev_button = QPushButton("← Назад")
        self.prev_button.clicked.connect(self._prev_page)
        pagination.addWidget(self.prev_button)

        self.page_label = QLabel("Страница 0 из 0")
        pagination.addWidget(self.page_label)

        self.next_button = QPushButton("Вперёд →")
        self.next_button.clicked.connect(self._next_page)
        pagination.addWidget(self.next_button)

        pagination.addWidget(QLabel("Строк на странице:"))
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(5, 500)
        self.page_size_spin.setValue(PAGE_SIZE)
        self.page_size_spin.valueChanged.connect(self._page_size_changed)
        pagination.addWidget(self.page_size_spin)

        pagination.addStretch()
        layout.addLayout(pagination)

        crud = QHBoxLayout()
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.clicked.connect(self.refresh)
        self.add_button = QPushButton("Добавить")
        self.add_button.clicked.connect(self._add_row)
        self.edit_button = QPushButton("Изменить")
        self.edit_button.clicked.connect(self._edit_row)
        self.delete_button = QPushButton("Удалить")
        self.delete_button.clicked.connect(self._delete_row)
        for btn in (
            self.refresh_button,
            self.add_button,
            self.edit_button,
            self.delete_button,
        ):
            crud.addWidget(btn)
        crud.addStretch()
        layout.addLayout(crud)

        self._set_enabled(False)

    def _set_enabled(self, enabled: bool) -> None:
        self.table.setEnabled(enabled)
        self.prev_button.setEnabled(enabled)
        self.next_button.setEnabled(enabled)
        self.page_size_spin.setEnabled(enabled)
        self.refresh_button.setEnabled(enabled)
        self.add_button.setEnabled(enabled)
        self.edit_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)

    def open_table(self, conn: sqlite3.Connection, table_name: str) -> None:
        self._conn = conn
        self._table_name = table_name
        self._columns = self._load_columns(table_name)
        self._page = 0
        self.title_label.setText(f"Таблица: {table_name}")
        self._set_enabled(True)
        self.refresh()

    def close_table(self) -> None:
        self._conn = None
        self._table_name = ""
        self._columns = []
        self._page = 0
        self._total_rows = 0
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.title_label.setText("Таблица не выбрана")
        self.page_label.setText("Страница 0 из 0")
        self._set_enabled(False)

    def _load_columns(self, table_name: str) -> list[str]:
        assert self._conn is not None
        quoted = '"' + table_name.replace('"', '""') + '"'
        rows = self._conn.execute(f"PRAGMA table_info({quoted})").fetchall()
        return [row[1] for row in rows]

    def _quoted_table(self) -> str:
        escaped = self._table_name.replace('"', '""')
        return f'"{escaped}"'

    def _total_pages(self) -> int:
        if self._total_rows == 0:
            return 0
        return (self._total_rows + self._page_size - 1) // self._page_size

    def refresh(self) -> None:
        if self._conn is None or not self._table_name:
            return

        count_row = self._conn.execute(
            f"SELECT COUNT(*) FROM {self._quoted_table()}"
        ).fetchone()
        self._total_rows = int(count_row[0]) if count_row else 0

        total_pages = self._total_pages()
        if total_pages == 0:
            self._page = 0
        elif self._page >= total_pages:
            self._page = total_pages - 1

        offset = self._page * self._page_size
        rows = self._conn.execute(
            f"SELECT rowid, * FROM {self._quoted_table()} LIMIT ? OFFSET ?",
            (self._page_size, offset),
        ).fetchall()

        self.table.setColumnCount(len(self._columns) + 1)
        self.table.setHorizontalHeaderLabels(["rowid", *self._columns])
        self.table.setRowCount(len(rows))

        for row_idx, row in enumerate(rows):
            rowid = row[0]
            values = row[1:]
            id_item = QTableWidgetItem(str(rowid))
            id_item.setData(Qt.ItemDataRole.UserRole, rowid)
            self.table.setItem(row_idx, 0, id_item)
            for col_idx, value in enumerate(values, start=1):
                text = "" if value is None else str(value)
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(text))

        current_page = self._page + 1 if total_pages else 0
        self.page_label.setText(
            f"Страница {current_page} из {total_pages} "
            f"(всего записей: {self._total_rows})"
        )
        self.prev_button.setEnabled(self._page > 0)
        self.next_button.setEnabled(total_pages > 0 and self._page < total_pages - 1)

    def _prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self.refresh()

    def _next_page(self) -> None:
        if self._page < self._total_pages() - 1:
            self._page += 1
            self.refresh()

    def _page_size_changed(self, value: int) -> None:
        self._page_size = value
        self._page = 0
        self.refresh()

    def _selected_rowid(self) -> int | None:
        selected = self.table.selectionModel().selectedRows()
        row = selected[0].row() if selected else self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        rowid = item.data(Qt.ItemDataRole.UserRole)
        return int(rowid) if rowid is not None else None

    def _selected_values(self) -> dict[str, str | None]:
        selected = self.table.selectionModel().selectedRows()
        row = selected[0].row() if selected else self.table.currentRow()
        values: dict[str, str | None] = {}
        if row < 0:
            return values
        for col_idx, column in enumerate(self._columns, start=1):
            item = self.table.item(row, col_idx)
            values[column] = item.text() if item else None
        return values

    def _add_row(self) -> None:
        if self._conn is None:
            return
        dialog = RowEditDialog(self._columns, title="Добавить запись", parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.values()
        columns = [c for c in self._columns if c in values]
        placeholders = ", ".join("?" for _ in columns)
        col_names = ", ".join(f'"{c}"' for c in columns)
        sql = f"INSERT INTO {self._quoted_table()} ({col_names}) VALUES ({placeholders})"
        try:
            self._conn.execute(sql, [values[c] for c in columns])
            self._conn.commit()
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить запись:\n{exc}")
            return
        self.refresh()

    def _edit_row(self) -> None:
        if self._conn is None:
            return
        rowid = self._selected_rowid()
        if rowid is None:
            QMessageBox.information(self, "Изменить", "Выберите строку в таблице.")
            return

        dialog = RowEditDialog(
            self._columns,
            values=self._selected_values(),
            title="Изменить запись",
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.values()
        assignments = ", ".join(f'"{c}" = ?' for c in self._columns)
        sql = f"UPDATE {self._quoted_table()} SET {assignments} WHERE rowid = ?"
        try:
            self._conn.execute(sql, [values[c] for c in self._columns] + [rowid])
            self._conn.commit()
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось изменить запись:\n{exc}")
            return
        self.refresh()

    def _delete_row(self) -> None:
        if self._conn is None:
            return
        rowid = self._selected_rowid()
        if rowid is None:
            QMessageBox.information(self, "Удалить", "Выберите строку в таблице.")
            return

        answer = QMessageBox.question(
            self,
            "Удалить",
            f"Удалить запись rowid={rowid}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self._conn.execute(
                f"DELETE FROM {self._quoted_table()} WHERE rowid = ?", (rowid,)
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить запись:\n{exc}")
            return
        self.refresh()


class MainWindow(QMainWindow):
    def __init__(self, db_path: str | Path = DEFAULT_DB) -> None:
        super().__init__()
        self.setWindowTitle("SQLite Test DB")
        self.setMinimumSize(1000, 640)
        self._conn: sqlite3.Connection | None = None
        self._db_path = Path(db_path)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Файл SQLite:"))
        self.path_edit = QLineEdit(str(self._db_path))
        file_row.addWidget(self.path_edit, stretch=1)
        browse_btn = QPushButton("Обзор…")
        browse_btn.clicked.connect(self._browse_db)
        file_row.addWidget(browse_btn)
        connect_btn = QPushButton("Подключить")
        connect_btn.clicked.connect(self._connect_db)
        file_row.addWidget(connect_btn)
        root.addLayout(file_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QGroupBox("Таблицы")
        left_layout = QVBoxLayout(left)
        self.tables_list = QListWidget()
        self.tables_list.itemDoubleClicked.connect(self._open_selected_table)
        left_layout.addWidget(self.tables_list)

        open_btn = QPushButton("Открыть")
        open_btn.clicked.connect(self._open_selected_table)
        left_layout.addWidget(open_btn)
        splitter.addWidget(left)

        self.table_view = TableViewWidget()
        splitter.addWidget(self.table_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        root.addWidget(splitter)

        self._connect_db()

    def _browse_db(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл SQLite",
            str(self._db_path.parent),
            "SQLite (*.db *.sqlite *.sqlite3);;Все файлы (*.*)",
        )
        if path:
            self.path_edit.setText(path)

    def _connect_db(self) -> None:
        path = Path(self.path_edit.text().strip())
        if not path.exists():
            QMessageBox.warning(self, "Ошибка", f"Файл не найден:\n{path}")
            return

        if self._conn is not None:
            self.table_view.close_table()
            self._conn.close()
            self._conn = None

        try:
            self._conn = sqlite3.connect(path)
            self._db_path = path
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть БД:\n{exc}")
            return

        self._load_tables()
        self.statusBar().showMessage(f"Подключено: {path}")

    def _load_tables(self) -> None:
        self.tables_list.clear()
        if self._conn is None:
            return
        rows = self._conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        for (name,) in rows:
            self.tables_list.addItem(name)

    def _open_selected_table(self) -> None:
        if self._conn is None:
            QMessageBox.warning(self, "Ошибка", "Сначала подключите файл SQLite.")
            return
        item = self.tables_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Открыть", "Выберите таблицу в списке.")
            return
        self.table_view.open_table(self._conn, item.text())

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._conn is not None:
            self.table_view.close_table()
            self._conn.close()
        super().closeEvent(event)


def main() -> None:
    db_path = DEFAULT_DB
    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    app = QApplication(sys.argv)
    window = MainWindow(db_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
