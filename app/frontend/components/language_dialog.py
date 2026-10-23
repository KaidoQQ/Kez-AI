from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QButtonGroup, QWidget

from core.i18n import tr, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

LANGUAGE_FLAGS: dict[str, str] = {"ru": "🇷🇺", "en": "🇬🇧"}

DIALOG_STYLE: str = """
    QDialog { background-color: #111A2E; }
    QLabel#language_heading { color: #F0EADA; font-size: 18px; font-weight: bold; }
    QLabel#language_subtitle { color: rgba(240, 234, 218, 0.7); font-size: 12px; }
    QPushButton#language_option {
        background-color: #172033; color: #F0EADA; border: 2px solid rgba(240, 234, 218, 40);
        border-radius: 12px; padding: 14px 22px; font-size: 15px;
    }
    QPushButton#language_option:hover { border-color: rgba(240, 234, 218, 120); }
    QPushButton#language_option:checked { background-color: #2B3E6B; border-color: #F0EADA; }
    QPushButton#language_continue {
        background-color: #F0EADA; color: #1D2B53; border: none; border-radius: 10px;
        padding: 9px 26px; font-weight: bold; font-size: 13px;
    }
    QPushButton#language_continue:hover { background-color: #FFFFFF; }
"""


class LanguageDialog(QDialog):
    """
    Выбор языка при первом запуске.
    Тексты диалога сразу переключаются на выбранный язык, чтобы было понятно, что получится.
    """

    def __init__(self, initial_language: str = DEFAULT_LANGUAGE, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(DIALOG_STYLE)
        self.setMinimumWidth(440)
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
