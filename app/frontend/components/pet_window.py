import os
from PyQt6.QtCore import Qt, QUrl, QTimer, QPoint, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QGuiApplication
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame

PET_STYLE: str = """
    QFrame#pet_card {
        background-color: rgba(11, 17, 32, 235);
        border: 1px solid rgba(240, 234, 218, 70);
        border-radius: 16px;
    }
    QLabel#pet_bubble {
        background-color: #F0EADA;
        color: #1D2B53;
        border-radius: 12px;
        padding: 8px 10px;
        font-size: 12px;
    }
    QLineEdit#pet_input {
        background-color: rgba(23, 32, 51, 220);
        color: #F0EADA;
        border: 1px solid rgba(240, 234, 218, 60);
        border-radius: 12px;
        padding: 5px 10px;
        font-size: 12px;
    }
    QPushButton#pet_control {
        background: transparent;
        color: #F0EADA;
        border: none;
        font-size: 14px;
        font-weight: bold;
    }
    QPushButton#pet_control:hover { color: #FFFFFF; background-color: rgba(240, 234, 218, 30); border-radius: 10px; }
"""


class PetWindow(QWidget):
    """
    Режим «питомца»: маленькое окно поверх всех окон, где Kez сидит в углу экрана.
    - Перетаскивается мышью за любое место карточки
    - Мини-поле ввода для быстрых вопросов, ответы — в облачке над Kez
    - Кнопка ⤢ возвращает в полное окно
    """
    message_submitted = pyqtSignal(str)
    restore_requested = pyqtSignal()

    def __init__(self, idle_video_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(PET_STYLE)
        self.idle_video_path: str = idle_video_path
        self._drag_offset: QPoint | None = None
        self._bubble_timer = QTimer(self)
        self._bubble_timer.setSingleShot(True)
        self._bubble_timer.timeout.connect(self.hide_bubble)
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        self.bubble = QLabel("")
        self.bubble.setObjectName("pet_bubble")
        self.bubble.setWordWrap(True)
        self.bubble.setMaximumWidth(240)
        self.bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.bubble.hide()
        outer.addWidget(self.bubble)

        card = QFrame()
        card.setObjectName("pet_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 6, 8, 8)
        card_layout.setSpacing(6)

        controls = QHBoxLayout()
        controls.addStretch()
        restore_btn = QPushButton("⤢")
        restore_btn.setObjectName("pet_control")
        restore_btn.setToolTip("Вернуться в полное окно")
        restore_btn.setFixedSize(24, 24)
        restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restore_btn.clicked.connect(self.restore_requested.emit)
        controls.addWidget(restore_btn)
        card_layout.addLayout(controls)

        self.video_widget = QVideoWidget()
        self.video_widget.setFixedSize(220, 160)
        card_layout.addWidget(self.video_widget)

        self.player = QMediaPlayer(self)
        self.player.setVideoOutput(self.video_widget)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        if self.idle_video_path and os.path.exists(self.idle_video_path):
            self.player.setSource(QUrl.fromLocalFile(self.idle_video_path))

        self.input = QLineEdit()
        self.input.setObjectName("pet_input")
        self.input.setPlaceholderText("Спроси Kez...")
        self.input.returnPressed.connect(self._on_submit)
        card_layout.addWidget(self.input)

        outer.addWidget(card)
        self.adjustSize()

    def show_pet(self) -> None:
        """Показывает питомца в правом нижнем углу основного экрана."""
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(screen.right() - self.width() - 24, screen.bottom() - self.height() - 24)
        self.show()
        self.player.play()

    def hide_pet(self) -> None:
        self.player.pause()
        self.hide()

    def show_bubble(self, text: str, timeout_ms: int = 12000) -> None:
        """Показывает реплику Kez в облачке (обрезается до ~280 символов)."""
        short: str = text if len(text) <= 280 else text[:277].rstrip() + "..."
        bottom_before: int = self.geometry().bottom()
        self.bubble.setText(short)
        self.bubble.show()
        self.adjustSize()
        # Облачко растёт вверх, сам Kez остаётся на месте
        self.move(self.x(), bottom_before - self.height() + 1)
        self._bubble_timer.start(timeout_ms)

    def hide_bubble(self) -> None:
        bottom_before: int = self.geometry().bottom()
        self.bubble.hide()
        self.adjustSize()
        self.move(self.x(), bottom_before - self.height() + 1)

    def _on_submit(self) -> None:
        text: str = self.input.text().strip()
        if text:
            self.input.clear()
            self.show_bubble("Чирик... думаю! 🐦", timeout_ms=60000)
            self.message_submitted.emit(text)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = None

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.restore_requested.emit()
