from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsOpacityEffect
)


class ChatAreaWidget(QScrollArea):
    """
    Область отображения сообщений чата, скролла и индикатора 'Kez думает...'.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("chat_area")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._typing_widget: QWidget | None = None
        self._typing_timer: QTimer | None = None
        self._typing_dots_count: int = 1

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.content_widget = QWidget()
        self.content_widget.setObjectName("chat_content")
        self.chat_layout = QVBoxLayout(self.content_widget)
        self.chat_layout.addStretch()
        self.setWidget(self.content_widget)

    def add_message(self, text: str, msg_type: str, animate: bool = True) -> None:
        """Добавляет пузырь сообщения в чат."""
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setProperty("msg_type", msg_type)
        lbl.setMaximumWidth(600)
        lbl.setStyleSheet("/* update */")

        layout = QHBoxLayout()
        if msg_type == "user":
            layout.addStretch()
            layout.addWidget(lbl)
        else:
            layout.addWidget(lbl)
            layout.addStretch()

        self.chat_layout.insertLayout(self.chat_layout.count() - 1, layout)

        if animate:
            opacity_effect = QGraphicsOpacityEffect(lbl)
            lbl.setGraphicsEffect(opacity_effect)
            anim = QPropertyAnimation(opacity_effect, b"opacity", lbl)
            anim.setDuration(350)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            anim.start()

        QTimer.singleShot(40, self.scroll_to_bottom)

    def show_typing_indicator(self) -> None:
        """Отображает анимированный индикатор набора текста."""
        if self._typing_widget is not None:
            return

        lbl = QLabel("Kez думает •")
        lbl.setProperty("msg_type", "typing")
        lbl.setStyleSheet("/* update */")

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(lbl)
        layout.addStretch()

        self.chat_layout.insertWidget(self.chat_layout.count() - 1, container)
        self._typing_widget = container
        self._typing_dots_count = 1

        def _update_dots() -> None:
            self._typing_dots_count = (self._typing_dots_count % 3) + 1
            dots: str = "• " * self._typing_dots_count
            lbl.setText(f"Kez думает {dots.strip()}")

        self._typing_timer = QTimer(self)
        self._typing_timer.timeout.connect(_update_dots)
        self._typing_timer.start(350)

        QTimer.singleShot(30, self.scroll_to_bottom)

    def hide_typing_indicator(self) -> None:
        """Скрывает индикатор набора текста."""
        if self._typing_timer is not None:
            self._typing_timer.stop()
            self._typing_timer = None

        if self._typing_widget is not None:
            self.chat_layout.removeWidget(self._typing_widget)
            self._typing_widget.deleteLater()
            self._typing_widget = None

    def clear_messages(self) -> None:
        """Очищает все сообщения в чате."""
        self.hide_typing_indicator()
        while self.chat_layout.count() > 1:
            child = self.chat_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                while child.layout().count():
                    sub = child.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
                child.layout().deleteLater()

    def scroll_to_bottom(self) -> None:
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
