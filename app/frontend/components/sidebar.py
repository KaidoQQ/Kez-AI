import re
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QPoint, QTimer
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QMenu, QInputDialog, QMessageBox, QLineEdit
)
from core.i18n import tr

# Пометка элемента списка как результата поиска (у таких нет контекстного меню Rename/Delete)
SEARCH_RESULT_ROLE: int = Qt.ItemDataRole.UserRole + 1
SNIPPET_LENGTH: int = 70


class SidebarWidget(QFrame):
    """
    Левая боковая панель с историей диалогов и кнопкой создания нового чата.
    Поддерживает контекстное меню (Delete / Rename) по правому клику на чат.
    """
    new_chat_requested = pyqtSignal()
    chat_selected = pyqtSignal(int)
    chat_rename_requested = pyqtSignal(int, str)
    chat_delete_requested = pyqtSignal(int)
    search_requested = pyqtSignal(str)   # пустая строка — сброс поиска

    def __init__(self, parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(250)

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 20, 15, 20)

        # Заголовок
        self.sidebar_title = QLabel(tr("sidebar.title"))
        self.layout.addWidget(self.sidebar_title)

        # Кнопка создания нового чата
        self.new_chat_btn = QPushButton(tr("sidebar.new_chat"))
        self.new_chat_btn.setObjectName("new_chat_btn")
        self.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_chat_btn.clicked.connect(self.new_chat_requested.emit)
        self.layout.addWidget(self.new_chat_btn)

        # Поиск по истории всех чатов (с задержкой 350 мс после ввода)
        self.search_field = QLineEdit()
        self.search_field.setObjectName("search_field")
        self.search_field.setPlaceholderText(tr("sidebar.search_placeholder"))
        self.search_field.setClearButtonEnabled(True)
        self.search_field.setStyleSheet(
            "QLineEdit#search_field { background-color: rgba(23, 32, 51, 160); color: #F0EADA;"
            " border: 1px solid rgba(240, 234, 218, 40); border-radius: 10px; padding: 6px 10px; font-size: 12px; margin-bottom: 8px; }"
        )
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(350)
        self._search_timer.timeout.connect(lambda: self.search_requested.emit(self.search_field.text().strip()))
        self.search_field.textChanged.connect(lambda _: self._search_timer.start())
        self.layout.addWidget(self.search_field)

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
        if chat_id_data is None or item.data(SEARCH_RESULT_ROLE):
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

        rename_action = menu.addAction(tr("sidebar.rename"))
        delete_action = menu.addAction(tr("sidebar.delete"))

        action = menu.exec(self.chat_list_widget.mapToGlobal(pos))
        if action == rename_action:
            new_title, ok = QInputDialog.getText(
                self, tr("sidebar.rename_title"), tr("sidebar.rename_label"), text=current_title
            )
            if ok and new_title.strip():
                self.chat_rename_requested.emit(chat_id, new_title.strip())

        elif action == delete_action:
            confirm = QMessageBox.question(
                self,
                tr("sidebar.delete_title"),
                tr("sidebar.delete_confirm", title=current_title),
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

    @property
    def is_searching(self) -> bool:
        return bool(self.search_field.text().strip())

    def show_search_results(self, query: str, results: list[dict]) -> None:
        """Показывает найденные сообщения: название чата + фрагмент вокруг совпадения."""
        self.chat_list_widget.blockSignals(True)
        self.chat_list_widget.clear()

        if not results:
            empty_item = QListWidgetItem(tr("sidebar.no_results", query=query))
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.chat_list_widget.addItem(empty_item)

        for result in results:
            snippet: str = self._make_snippet(str(result.get("text_content", "")), query)
            item = QListWidgetItem(f"{result.get('title') or tr('sidebar.default_chat')}\n{snippet}")
            item.setData(Qt.ItemDataRole.UserRole, int(result["chat_id"]))
            item.setData(SEARCH_RESULT_ROLE, True)
            item.setToolTip(str(result.get("text_content", ""))[:500])
            self.chat_list_widget.addItem(item)

        self.chat_list_widget.blockSignals(False)

    @staticmethod
    def _make_snippet(text: str, query: str) -> str:
        """Вырезает фрагмент сообщения вокруг первого совпадения запроса."""
        clean: str = re.sub(r"\[(IMAGE|FILE):[^\]]*\]", "", text)
        clean = re.sub(r"\s+", " ", clean).strip()
        position: int = clean.lower().find(query.lower().split()[0]) if query.split() else -1
        start: int = max(0, position - 20) if position >= 0 else 0
        snippet: str = clean[start:start + SNIPPET_LENGTH]
        return ("…" if start > 0 else "") + snippet + ("…" if start + SNIPPET_LENGTH < len(clean) else "")

    def retranslate_ui(self) -> None:
        """Обновляет тексты после смены языка."""
        self.sidebar_title.setText(tr("sidebar.title"))
        self.new_chat_btn.setText(tr("sidebar.new_chat"))
        self.search_field.setPlaceholderText(tr("sidebar.search_placeholder"))

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
