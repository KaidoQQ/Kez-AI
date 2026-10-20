import re
import html
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QLabel
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
            '<table width="100%" cellpadding="0" cellspacing="0" bgcolor="#000000" style="background-color: #000000; border: 1px solid rgba(240, 234, 218, 0.25); border-radius: 6px;">'
            '<tr>'
            f'<td bgcolor="#161F30" style="background-color: #161F30; padding: 4px 10px; font-family: Consolas, monospace; font-size: 11px; color: #94A3B8; border-bottom: 1px solid rgba(240, 234, 218, 0.15);">'
            f'💻 {lang.upper()}'
            '</td>'
            '</tr>'
            '<tr>'
            '<td bgcolor="#000000" style="background-color: #000000; padding: 10px;">'
            f'<pre style="margin: 0; padding: 0; font-family: Consolas, \'Courier New\', monospace; font-size: 13px; color: #4ADE80; background-color: #000000; white-space: pre-wrap; word-break: break-all; line-height: 1.25;"><code>{escaped_code}</code></pre>'
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
        inline_html = f'<code style="font-family: Consolas, monospace; font-size: 13px; background-color: rgba(15, 23, 42, 0.9); color: #38BDF8; border: 1px solid rgba(240, 234, 218, 0.25); border-radius: 4px; padding: 2px 6px;">{escaped_inline}</code>'
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
        browser.setMaximumWidth(720)

        formatted_html = markdown_to_clean_html(text)
        browser.setHtml(formatted_html)
        browser.update_auto_height()

        layout = QHBoxLayout()
        if msg_type == "user":
            layout.addStretch()
            layout.addWidget(browser)
        else:
            layout.addWidget(browser)
            layout.addStretch()

        self.chat_layout.insertLayout(self.chat_layout.count() - 1, layout)

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
        browser.setMaximumWidth(720)
        browser.setHtml("")

        layout = QHBoxLayout()
        if msg_type == "user":
            layout.addStretch()
            layout.addWidget(browser)
        else:
            layout.addWidget(browser)
            layout.addStretch()

        self.chat_layout.insertLayout(self.chat_layout.count() - 1, layout)
        buffer: list[str] = []
        return browser, buffer

    def append_stream_chunk(self, browser: MessageBrowser, buffer: list[str], chunk: str) -> None:
        """
        Добавляет новый кусочек текста в стриминговое сообщение,
        обновляет форматирование и высоту пузыря в реальном времени.
        """
        buffer.append(chunk)
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

