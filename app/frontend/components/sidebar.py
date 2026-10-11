from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem
)


class SidebarWidget(QFrame):
    """
    Левая боковая панель с историей диалогов и кнопкой создания нового чата.
    """
    new_chat_requested = pyqtSignal()
    chat_selected = pyqtSignal(int)

    def __init__(self, parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(250)

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 20, 15, 20)

        # Заголовок
        self.sidebar_title = QLabel("Chat History")
        self.layout.addWidget(self.sidebar_title)

        # Кнопка создания нового чата
        self.new_chat_btn = QPushButton("+ New Chat")
        self.new_chat_btn.setObjectName("new_chat_btn")
        self.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_chat_btn.clicked.connect(self.new_chat_requested.emit)
        self.layout.addWidget(self.new_chat_btn)

        # Список чатов
        self.chat_list_widget = QListWidget()
        self.chat_list_widget.setObjectName("chat_list_widget")
        self.chat_list_widget.itemClicked.connect(self._on_item_clicked)
        self.layout.addWidget(self.chat_list_widget, stretch=1)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        chat_id = item.data(Qt.ItemDataRole.UserRole)
        if chat_id is not None:
            self.chat_selected.emit(int(chat_id))

    def update_chats(self, chats: list[dict], current_chat_id: int) -> None:
        """Обновляет элементы списка чатов из БД."""
        self.chat_list_widget.blockSignals(True)
        self.chat_list_widget.clear()

        for chat in chats:
            chat_id: int = int(chat["id"])
            title: str = str(chat["title"])
            item: QListWidgetItem = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, chat_id)
            self.chat_list_widget.addItem(item)

            if chat_id == current_chat_id:
                self.chat_list_widget.setCurrentItem(item)

        self.chat_list_widget.blockSignals(False)

    def get_current_chat_title(self) -> str:
        current_item = self.chat_list_widget.currentItem()
        return current_item.text() if current_item else ""

    def toggle_sidebar(self) -> None:
        """Анимация открытия / закрытия панели."""
        width = self.width()
        target_width = 0 if width > 0 else 250

        self.anim_min = QPropertyAnimation(self, b"minimumWidth")
        self.anim_min.setDuration(350)
        self.anim_min.setStartValue(width)
        self.anim_min.setEndValue(target_width)
        self.anim_min.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.anim_max = QPropertyAnimation(self, b"maximumWidth")
        self.anim_max.setDuration(350)
        self.anim_max.setStartValue(width)
        self.anim_max.setEndValue(target_width)
        self.anim_max.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.anim_min.start()
        self.anim_max.start()
