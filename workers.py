"""Фоновая отправка промтов в нейросети."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from db import Database
from models import AIModel
from network import get_request_timeout, send_prompt


class SendPromptsWorker(QThread):
    model_finished = pyqtSignal(int, str, str)
    all_finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(
        self,
        models: list[AIModel],
        prompt_text: str,
        db: Database,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._models = models
        self._prompt_text = prompt_text
        self._db = db
        self._timeout = get_request_timeout(db)

    def run(self) -> None:
        if not self._models:
            self.error.emit("Нет активных моделей. Добавьте модели в меню «Данные → Модели».")
            self.all_finished.emit()
            return

        for model in self._models:
            if self.isInterruptionRequested():
                break
            response = send_prompt(
                model,
                self._prompt_text,
                timeout=self._timeout,
                db=self._db,
            )
            self.model_finished.emit(model.id, model.name, response)

        self.all_finished.emit()
