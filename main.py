import sys

from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ChatList")
        self.setMinimumSize(320, 160)

        self.phrase_label = QLabel()
        self.phrase_label.setWordWrap(True)

        click_button = QPushButton("Нажми меня")
        click_button.clicked.connect(self.show_phrase)

        layout = QVBoxLayout()
        layout.addWidget(self.phrase_label)
        layout.addWidget(click_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def show_phrase(self) -> None:
        self.phrase_label.setText("Минимальная программа на Python")


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
