"""Фоновая отправка промтов в нейросети."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from models import AIModel
from network import send_prompt


class SendPromptsWorker(QThread):
    model_finished = pyqtSignal(int, str, str)
    all_finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(
        self,
        models: list[AIModel],
        prompt_text: str,
        timeout: float,
        log_enabled: bool = False,
        log_file: str = "chatlist.log",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._models = models
        self._prompt_text = prompt_text
        self._timeout = timeout
        self._log_enabled = log_enabled
        self._log_file = log_file

    def run(self) -> None:
        if not self._models:
            self.error.emit("Нет активных моделей. Добавьте модели в меню «Данные → Модели».")
            self.all_finished.emit()
            return

        try:
            for model in self._models:
                if self.isInterruptionRequested():
                    break
                response = send_prompt(
                    model,
                    self._prompt_text,
                    timeout=self._timeout,
                    log_enabled=self._log_enabled,
                    log_file=self._log_file,
                )
                self.model_finished.emit(model.id, model.name, response)
        except Exception as exc:
            self.error.emit(f"Ошибка отправки: {exc}")
        finally:
            self.all_finished.emit()
