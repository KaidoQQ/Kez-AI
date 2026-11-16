from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QButtonGroup, QWidget

from core.i18n import tr, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

LANGUAGE_FLAGS: dict[str, str] = {"ru": "🇷🇺", "en": "🇬🇧"}



class LanguageDialog(QDialog):
    """
    Выбор языка при первом запуске.
    Тексты диалога сразу переключаются на выбранный язык, чтобы было понятно, что получится.
    """

    def __init__(self, initial_language: str = DEFAULT_LANGUAGE, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from app.frontend.theme import apply_theme
        from core.settings import settings
        apply_theme(settings.theme)
        self.setMinimumWidth(480)
        self.selected_language: str = initial_language if initial_language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        self._setup_ui()
        self._retranslate()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(14)

        self.heading = QLabel()
        self.heading.setObjectName("language_heading")
        self.heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.heading)

        self.subtitle = QLabel()
        self.subtitle.setObjectName("language_subtitle")
        self.subtitle.setWordWrap(True)
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle)

        options = QHBoxLayout()
        options.setSpacing(12)
        self.buttons = QButtonGroup(self)
        self.buttons.setExclusive(True)
        for language in SUPPORTED_LANGUAGES:
            button = QPushButton(f"{LANGUAGE_FLAGS.get(language, '')}  {tr('language.name', language=language)}")
            button.setObjectName("language_option")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setChecked(language == self.selected_language)
            button.clicked.connect(lambda _, lang=language: self._select(lang))
            self.buttons.addButton(button)
            options.addWidget(button)
        layout.addLayout(options)

        self.continue_btn = QPushButton()
        self.continue_btn.setObjectName("language_continue")
        self.continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.continue_btn.clicked.connect(self.accept)
        layout.addWidget(self.continue_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _select(self, language: str) -> None:
        self.selected_language = language
        self._retranslate()

    def _retranslate(self) -> None:
        lang: str = self.selected_language
        self.setWindowTitle(tr("first_run.title", language=lang))
        self.heading.setText(tr("first_run.heading", language=lang))
        self.subtitle.setText(tr("first_run.subtitle", language=lang))
        self.continue_btn.setText(tr("first_run.continue", language=lang))
