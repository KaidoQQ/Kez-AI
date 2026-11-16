import re
import html
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QWheelEvent, QIcon
from core.i18n import tr
from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QLabel, QPushButton, QGridLayout, QApplication
)


def markdown_to_clean_html(text: str) -> str:
    """
    Преобразует текст в аккуратный HTML:
    - Блоки кода (любые языки ```lang ... ```) в стиле терминала CMD с рамкой и моноширинным шрифтом
    - Инлайн-код (`code`) в виде консольных меток
    - Преобразует markdown (*, **, ссылки) без сырых символов
    """
    code_blocks: list[str] = []

    def _extract_code_block(match: re.Match) -> str:
        lang: str = (match.group(1) or "cmd").strip()
        code_content: str = match.group(2)
        escaped_code: str = html.escape(code_content.strip("\r\n"))
        
        # Шапка и монолитное терминальное окно в чисто чёрном стиле CMD (без разрывов цвета между строками)
        block_html: str = (
            '<div style="margin: 8px 0;">'
            '<table width="100%" cellpadding="0" cellspacing="0" bgcolor="#18181b" style="background-color: #18181b; border: 1px solid rgba(240, 234, 218, 0.25); border-radius: 6px;">'
            '<tr>'
            f'<td bgcolor="#27272a" style="background-color: #27272a; padding: 4px 10px; font-family: Consolas, monospace; font-size: 11px; color: #94A3B8; border-bottom: 1px solid rgba(240, 234, 218, 0.15);">'
            f'{lang.upper()}'
            '</td>'
            '</tr>'
            '<tr>'
            '<td bgcolor="#18181b" style="background-color: #18181b; padding: 10px;">'
            f'<pre style="margin: 0; padding: 0; font-family: Consolas, \'Courier New\', monospace; font-size: 13px; color: #e4e4e7; background-color: #18181b; white-space: pre-wrap; word-break: break-all; line-height: 1.25;"><code>{escaped_code}</code></pre>'
            '</td>'
            '</tr>'
            '</table>'
            '</div>'
        )
        idx = len(code_blocks)
        code_blocks.append(block_html)
        return f"@@@CODEBLOCK{idx}@@@"

    # 1. Извлекаем блоки кода с любым языком ```lang ... ```
    processed = re.sub(r"```([a-zA-Z0-9_\-\+\#]*)\s*\n(.*?)```", _extract_code_block, text, flags=re.DOTALL)
    # Если остались блоки без переноса строки после ```
    processed = re.sub(r"```([a-zA-Z0-9_\-\+\#]*)(.*?)```", _extract_code_block, processed, flags=re.DOTALL)

    # 2. Извлекаем инлайн-код `code`
    inline_codes: list[str] = []
    def _extract_inline_code(match: re.Match) -> str:
        raw_code = match.group(1)
        escaped_inline = html.escape(raw_code)
        inline_html = f'<code style="font-family: Consolas, monospace; font-size: 13px; background-color: rgba(15, 23, 42, 0.9); color: #a99af8; border: 1px solid rgba(240, 234, 218, 0.25); border-radius: 4px; padding: 2px 6px;">{escaped_inline}</code>'
        idx = len(inline_codes)
        inline_codes.append(inline_html)
        return f"@@@INLINECODE{idx}@@@"

    processed = re.sub(r"`([^`\r\n]+)`", _extract_inline_code, processed)

    # 3. Экранируем оставшийся обычный текст
    escaped = html.escape(processed)

    # 4. Форматирование обычного текста: жирный шрифт (** или __)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"__(.+?)__", r"<b>\1</b>", escaped)

    # 5. Курсив (* или _)
    escaped = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"<i>\1</i>", escaped)
    escaped = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", escaped)

    # 6. Ссылки [текст](url)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^\)]+)\)",
        r'<a href="\2" style="color: #60A5FA; text-decoration: underline;">\1</a>',
        escaped
    )

    # 7. Авто-определение ссылок
    escaped = re.sub(
        r'(?<!href=")(https?://[^\s<]+)',
        r'<a href="\1" style="color: #60A5FA; text-decoration: underline;">\1</a>',
        escaped
    )

    # 8. Переносы строк
    escaped = escaped.replace("\n", "<br>")

    # 9. Возвращаем блоки кода обратно
    for idx, code_html in enumerate(code_blocks):
        escaped = escaped.replace(f"@@@CODEBLOCK{idx}@@@", code_html)

    for idx, inline_html in enumerate(inline_codes):
        escaped = escaped.replace(f"@@@INLINECODE{idx}@@@", inline_html)

    return escaped


class MessageBrowser(QTextBrowser):
    """
    Текстовый браузер сообщения:
    - Без внутренних скроллбаров
    - Полностью раскрывается на всю высоту своего контента (никакого скролла внутри сообщения!)
    - Колёсико мыши свободно прокручивает общее окно чата
    """
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Отслеживаем изменение размера документа для точной подгонки высоты
        self.document().documentLayout().documentSizeChanged.connect(self._adjust_height)

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()

    def _adjust_height(self) -> None:
        """Автоматически подстраивает высоту под документ, чтобы внутри никогда не появлялся скролл."""
        doc_height = int(self.document().size().height())
        if doc_height > 0:
            self.setFixedHeight(doc_height + 24)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.document().setTextWidth(self.viewport().width())
        self._adjust_height()

    def update_auto_height(self) -> None:
        w = self.viewport().width()
        if w > 50:
            self.document().setTextWidth(w)
        else:
            self.document().setTextWidth(680)
        self._adjust_height()


class ChatAreaWidget(QScrollArea):
    """
    Область отображения сообщений чата, скролла и индикатора 'Kez думает...'.
    Поддерживает выделение, копирование, терминальные блоки кода и плавную прокрутку колесиком.
    """

    suggestion_selected = pyqtSignal(str)

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
        self.chat_layout.setSpacing(20)
        self.chat_layout.setContentsMargins(24, 24, 24, 24)
        self.chat_layout.addStretch()
        self.setWidget(self.content_widget)
        self._setup_welcome()

    def _setup_welcome(self) -> None:
        self.welcome = QWidget(self.viewport())
        layout = QVBoxLayout(self.welcome)
        layout.setSpacing(16)
        mark = QLabel("✳")
        mark.setObjectName("welcome_mark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(mark)
        self.welcome_title = QLabel()
        self.welcome_title.setObjectName("welcome_title")
        self.welcome_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.welcome_title)
        self.welcome_subtitle = QLabel()
        self.welcome_subtitle.setObjectName("welcome_subtitle")
        self.welcome_subtitle.setWordWrap(True)
        self.welcome_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.welcome_subtitle)
        grid = QGridLayout()
        grid.setSpacing(10)
        self.suggestions = []
        for index, key in enumerate(("write", "learn", "plan", "code")):
            button = QPushButton()
            button.setObjectName("suggestion")
            icon_path = Path(__file__).resolve().parents[1] / "assets" / "icons" / f"{key}.svg"
            button.setIcon(QIcon(str(icon_path)))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _, k=key: self.suggestion_selected.emit(tr("ui.prompt_" + k)))
            grid.addWidget(button, index // 2, index % 2)
            self.suggestions.append((key, button))
        layout.addSpacing(12)
        layout.addLayout(grid)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.welcome_title.setText(tr("ui.welcome_title"))
        self.welcome_subtitle.setText(tr("ui.welcome_subtitle"))
        for key, button in self.suggestions:
            button.setText(tr("ui.suggest_" + key))
        for button in self.content_widget.findChildren(QPushButton, "copy_btn"):
            button.setText(tr("ui.copy"))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        width = self.viewport().width()
        margin = max(16, (width - 800) // 2)
        self.chat_layout.setContentsMargins(margin, 24, margin, 24)
        if hasattr(self, "welcome"):
            w = min(580, max(0, width - 24))
            h = min(320, self.viewport().height())
            self.welcome.setGeometry((width-w)//2, max(0, (self.viewport().height()-h)//2 - 20), w, h)

    def _insert_message(self, browser: MessageBrowser, msg_type: str) -> None:
        self.welcome.hide()
        card = QWidget()
        column = QVBoxLayout(card)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(4)
        if msg_type != "user":
            author = QLabel("✳  Kez")
            author.setObjectName("header_title")
            column.addWidget(author)
        column.addWidget(browser)
        copy = QPushButton(tr("ui.copy"))
        copy.setObjectName("copy_btn")
        copy.setCursor(Qt.CursorShape.PointingHandCursor)
        copy.setFixedHeight(28)
        def copy_message():
            QApplication.clipboard().setText(browser.property("source_text") or browser.toPlainText())
            copy.setText(tr("ui.copied"))
            timer = QTimer(copy)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: copy.setText(tr("ui.copy")))
            timer.start(1600)
        copy.clicked.connect(copy_message)
        column.addWidget(copy, alignment=Qt.AlignmentFlag.AlignLeft)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if msg_type == "user":
            row.addStretch(1)
            row.addWidget(card, 4)
        else:
            row.addWidget(card, 1)
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, row)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Гарантирует плавную прокрутку колесиком мыши по всему окну чата."""
        scrollbar = self.verticalScrollBar()
        delta = event.angleDelta().y()
        if delta != 0:
            step = -delta
            scrollbar.setValue(scrollbar.value() + step)
            event.accept()
        else:
            super().wheelEvent(event)

    def add_message(self, text: str, msg_type: str, animate: bool = True) -> None:
        """Добавляет пузырь сообщения в чат на полную высоту без внутренней прокрутки."""
        browser = MessageBrowser()
        browser.setProperty("msg_type", msg_type)
        browser.setMaximumWidth(800)

        formatted_html = markdown_to_clean_html(text)
        browser.setProperty("source_text", text)
        browser.setHtml(formatted_html)
        browser.update_auto_height()

        self._insert_message(browser, msg_type)

        # Перепроверяем высоту и плавно прокручиваем
        QTimer.singleShot(50, browser.update_auto_height)
        QTimer.singleShot(100, self.scroll_to_bottom)

    def create_streaming_message(self, msg_type: str = "ai") -> tuple[MessageBrowser, list[str]]:
        """
        Создает пустой пузырь сообщения для потоковой передачи (стриминга).
        Возвращает кортеж (MessageBrowser, buffer_list).
        """
        browser = MessageBrowser()
        browser.setProperty("msg_type", msg_type)
        browser.setMaximumWidth(800)
        browser.setHtml("")

        self._insert_message(browser, msg_type)
        buffer: list[str] = []
        return browser, buffer

    def append_stream_chunk(self, browser: MessageBrowser, buffer: list[str], chunk: str) -> None:
        """
        Добавляет новый кусочек текста в стриминговое сообщение,
        обновляет форматирование и высоту пузыря в реальном времени.
        """
        buffer.append(chunk)
        browser.setProperty("source_text", "".join(buffer))
        full_text: str = "".join(buffer)
        formatted_html: str = markdown_to_clean_html(full_text)
        browser.setHtml(formatted_html)
        browser.update_auto_height()
        self.scroll_to_bottom()

    def add_image_message(self, image_path: str, prompt: str = "", sender: str = "ai") -> None:
        """
        Добавляет в чат интерактивную карточку сгенерированного изображения
        с контекстным меню 'Скопировать' и 'Скачать'.
        """
        self.welcome.hide()
        from app.frontend.components.chat_image_widget import ChatImageWidget
        image_widget = ChatImageWidget(image_path, prompt)

        layout = QHBoxLayout()
        if sender == "user":
            layout.addStretch()
            layout.addWidget(image_widget)
        else:
            layout.addWidget(image_widget)
            layout.addStretch()

        self.chat_layout.insertLayout(self.chat_layout.count() - 1, layout)
        QTimer.singleShot(50, self.scroll_to_bottom)

    def add_file_message(self, file_path: str, sender: str = "ai") -> None:
        """Добавляет в чат карточку экспортированного документа (Открыть / Папка / Сохранить как)."""
        self.welcome.hide()
        from app.frontend.components.chat_file_widget import ChatFileWidget
        file_widget = ChatFileWidget(file_path)

        layout = QHBoxLayout()
        if sender == "user":
            layout.addStretch()
            layout.addWidget(file_widget)
        else:
            layout.addWidget(file_widget)
            layout.addStretch()

        self.chat_layout.insertLayout(self.chat_layout.count() - 1, layout)
        QTimer.singleShot(50, self.scroll_to_bottom)

    def show_typing_indicator(self) -> None:
        """Отображает анимированный индикатор набора текста."""
        if self._typing_widget is not None:
            return

        self.welcome.hide()
        lbl = QLabel(f"{tr('chat.typing')} •")
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
            lbl.setText(f"{tr('chat.typing')} {dots.strip()}")

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
        self.welcome.show()
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

