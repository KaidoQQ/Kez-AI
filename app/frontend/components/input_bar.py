import os
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit


class InputBarWidget(QWidget):
    """
    Нижняя панель ввода: опциональная кнопка знакомства с Kez,
    поле текста, кнопка вложений, микрофон и кнопка отправки.
    """
    message_submitted = pyqtSignal(str)
    meet_kez_clicked = pyqtSignal()

    def __init__(self, icons_dir: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.icons_dir: str = icons_dir
        self._glow_step: int = 0
        self._glow_timer: QTimer | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.main_container_layout = QVBoxLayout(self)
        self.main_container_layout.setContentsMargins(0, 0, 0, 0)
        self.main_container_layout.setSpacing(8)

        # Контейнер для кнопки знакомства (по центру над полем ввода)
        self.banner_layout = QHBoxLayout()
        self.banner_layout.setContentsMargins(0, 0, 0, 0)
        self.banner_layout.addStretch()

        self.meet_btn = QPushButton("Get to know Kez ✨")
        self.meet_btn.setObjectName("meet_kez_btn")
        self.meet_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.meet_btn.setFixedHeight(34)
        self.meet_btn.clicked.connect(self._on_meet_clicked)
        self.meet_btn.hide()  # По умолчанию скрыта, отображается только при проверке условий
        self.banner_layout.addWidget(self.meet_btn)

        self.banner_layout.addStretch()
        self.main_container_layout.addLayout(self.banner_layout)

        # Нижняя панель ввода
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_layout.setSpacing(10)

        # Кнопка вложений
        self.attach_btn = QPushButton("")
        self.attach_btn.setIcon(QIcon(os.path.join(self.icons_dir, "files.png")))
        self.attach_btn.setIconSize(QSize(38, 38))
        self.attach_btn.setObjectName("action_btn")
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.setFixedSize(45, 45)
        self.controls_layout.addWidget(self.attach_btn)

        # Поле ввода текста
        self.input_field = QLineEdit()
        self.input_field.setObjectName("input_field")
        self.input_field.setPlaceholderText("Message Kez...")
        self.input_field.setFixedHeight(45)
        self.input_field.returnPressed.connect(self._on_submit)
        self.controls_layout.addWidget(self.input_field)

        # Кнопка микрофона
        self.voice_btn = QPushButton("")
        self.voice_btn.setIcon(QIcon(os.path.join(self.icons_dir, "micro.png")))
        self.voice_btn.setIconSize(QSize(38, 38))
        self.voice_btn.setObjectName("action_btn")
        self.voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.voice_btn.setFixedSize(45, 45)
        self.controls_layout.addWidget(self.voice_btn)

        # Кнопка отправки
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFixedHeight(45)
        self.send_btn.clicked.connect(self._on_submit)
        self.controls_layout.addWidget(self.send_btn)

        self.main_container_layout.addLayout(self.controls_layout)

    def show_meet_button(self) -> None:
        """Показывает кнопку знакомства и запускает неяркую пульсацию темными тонами."""
        self.meet_btn.show()
        if self._glow_timer is None:
            self._glow_timer = QTimer(self)
            self._glow_timer.setInterval(120)
            self._glow_timer.timeout.connect(self._pulse_glow)
        self._glow_timer.start()

    def hide_meet_button(self) -> None:
        """Скрывает кнопку знакомства и останавливает таймер."""
        if self._glow_timer and self._glow_timer.isActive():
            self._glow_timer.stop()
        self.meet_btn.hide()

    def _pulse_glow(self) -> None:
        """Плавно меняет темные цвета фона кнопки для создания ненавязчивого мерцания."""
        # Колебание синей составляющей в диапазоне темных цветов (RGB: 18..35, 26..48, 45..75)
        self._glow_step = (self._glow_step + 1) % 40
        factor = self._glow_step if self._glow_step <= 20 else (40 - self._glow_step)
        
        r = 18 + int(factor * 0.7)
        g = 26 + int(factor * 1.0)
        b = 48 + int(factor * 1.3)
        border_alpha = 40 + int(factor * 4.0)
        
        style = f"""
            QPushButton#meet_kez_btn {{
                background-color: rgb({r}, {g}, {b});
                color: #F0EADA;
                border: 1px solid rgba(240, 234, 218, {border_alpha});
                border-radius: 17px;
                padding: 6px 18px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton#meet_kez_btn:hover {{
                background-color: rgb({r + 15}, {g + 20}, {b + 30});
                border: 1px solid rgba(240, 234, 218, 180);
            }}
        """
        self.meet_btn.setStyleSheet(style)

    def _on_meet_clicked(self) -> None:
        self.hide_meet_button()
        self.meet_kez_clicked.emit()

    def _on_submit(self) -> None:
        text: str = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.message_submitted.emit(text)

    def set_placeholder(self, text: str) -> None:
        """Устанавливает подсказку в поле ввода."""
        self.input_field.setPlaceholderText(text)

    def set_focus(self) -> None:
        self.input_field.setFocus()

