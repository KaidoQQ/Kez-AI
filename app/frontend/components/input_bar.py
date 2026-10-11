import os
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLineEdit


class InputBarWidget(QWidget):
    """
    Нижняя панель ввода: поле текста, кнопка вложений, микрофон и кнопка отправки.
    """
    message_submitted = pyqtSignal(str)

    def __init__(self, icons_dir: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.icons_dir = icons_dir

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)

        # Кнопка вложений
        self.attach_btn = QPushButton("")
        self.attach_btn.setIcon(QIcon(os.path.join(self.icons_dir, "files.png")))
        self.attach_btn.setIconSize(QSize(38, 38))
        self.attach_btn.setObjectName("action_btn")
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.setFixedSize(45, 45)
        self.layout.addWidget(self.attach_btn)

        # Поле ввода текста
        self.input_field = QLineEdit()
        self.input_field.setObjectName("input_field")
        self.input_field.setPlaceholderText("Message Kez...")
        self.input_field.setFixedHeight(45)
        self.input_field.returnPressed.connect(self._on_submit)
        self.layout.addWidget(self.input_field)

        # Кнопка микрофона
        self.voice_btn = QPushButton("")
        self.voice_btn.setIcon(QIcon(os.path.join(self.icons_dir, "micro.png")))
        self.voice_btn.setIconSize(QSize(38, 38))
        self.voice_btn.setObjectName("action_btn")
        self.voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.voice_btn.setFixedSize(45, 45)
        self.layout.addWidget(self.voice_btn)

        # Кнопка отправки
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFixedHeight(45)
        self.send_btn.clicked.connect(self._on_submit)
        self.layout.addWidget(self.send_btn)

    def _on_submit(self) -> None:
        text: str = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.message_submitted.emit(text)

    def set_focus(self) -> None:
        self.input_field.setFocus()
