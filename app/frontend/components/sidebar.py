from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QPoint
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QMenu, QInputDialog, QMessageBox
)


class SidebarWidget(QFrame):
    """
    Левая боковая панель с историей диалогов и кнопкой создания нового чата.
    Поддерживает контекстное меню (Delete / Rename) по правому клику на чат.
    """
    new_chat_requested = pyqtSignal()
    chat_selected = pyqtSignal(int)
    chat_rename_requested = pyqtSignal(int, str)
    chat_delete_requested = pyqtSignal(int)

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
        self.chat_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chat_list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.chat_list_widget.itemClicked.connect(self._on_item_clicked)
        self.layout.addWidget(self.chat_list_widget, stretch=1)

    def _show_context_menu(self, pos: QPoint) -> None:
        item: QListWidgetItem | None = self.chat_list_widget.itemAt(pos)
        if not item:
            return

        chat_id_data = item.data(Qt.ItemDataRole.UserRole)
        if chat_id_data is None:
            return
        chat_id: int = int(chat_id_data)
        current_title: str = item.text()

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #172033;
                color: #F0EADA;
                border: 1px solid rgba(240, 234, 218, 50);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(43, 62, 107, 220);
                color: #FFFFFF;
            }
        """)

        rename_action = menu.addAction("✏️ Rename")
        delete_action = menu.addAction("🗑️ Delete")

        action = menu.exec(self.chat_list_widget.mapToGlobal(pos))
        if action == rename_action:
            new_title, ok = QInputDialog.getText(
                self, "Rename Chat", "Enter new chat title:", text=current_title
            )
            if ok and new_title.strip():
                self.chat_rename_requested.emit(chat_id, new_title.strip())

        elif action == delete_action:
            confirm = QMessageBox.question(
                self,
                "Delete Chat",
                f"Are you sure you want to delete chat '{current_title}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self.chat_delete_requested.emit(chat_id)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        chat_id = item.data(Qt.ItemDataRole.UserRole)
        if chat_id is not None:
            self.chat_selected.emit(int(chat_id))

    def update_chats(self, chats: list[dict], current_chat_id: int | None) -> None:
        """Обновляет элементы списка чатов из БД."""
        self.chat_list_widget.blockSignals(True)
        self.chat_list_widget.clear()

        for chat in chats:
            chat_id: int = int(chat["id"])
            title: str = str(chat["title"])
            item: QListWidgetItem = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, chat_id)
            self.chat_list_widget.addItem(item)

            if current_chat_id is not None and chat_id == current_chat_id:
                self.chat_list_widget.setCurrentItem(item)

        if current_chat_id is None:
            self.chat_list_widget.clearSelection()

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
