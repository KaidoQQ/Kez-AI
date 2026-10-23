from dataclasses import replace
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QWidget, QComboBox, QCheckBox,
    QLineEdit, QPushButton, QFileDialog, QSpinBox, QListWidget, QListWidgetItem, QLabel, QDialogButtonBox
)

from core.settings import KezSettings, available_models
from core.i18n import tr, SUPPORTED_LANGUAGES
from core.constants.file_const import TTS_VOICES

DIALOG_STYLE: str = """
    QDialog, QTabWidget::pane, QWidget#settings_tab { background-color: #111A2E; color: #F0EADA; }
    QLabel, QCheckBox { color: #F0EADA; }
    QTabBar::tab { background: #172033; color: #E2DFD2; padding: 8px 16px; border-top-left-radius: 8px; border-top-right-radius: 8px; }
    QTabBar::tab:selected { background: #2B3E6B; color: #FFFFFF; }
    QComboBox, QLineEdit, QSpinBox, QListWidget {
        background-color: #172033; color: #F0EADA; border: 1px solid rgba(240, 234, 218, 50);
        border-radius: 8px; padding: 5px 8px;
    }
    QPushButton {
        background-color: rgba(29, 43, 83, 220); color: #F0EADA; border: none; border-radius: 8px; padding: 6px 14px;
    }
    QPushButton:hover { background-color: rgba(39, 58, 113, 255); }
"""


class SettingsDialog(QDialog):
    """
    Панель настроек Kez:
    - Общие: тема, приоритетная модель, папка экспорта
    - Голос: голос TTS, автоозвучка, озвучка по предложениям, «Эй, Kez»
    - Память: автоизвлечение фактов и список того, что Kez помнит (с удалением)
    """
    settings_saved = pyqtSignal(object)      # KezSettings
    fact_delete_requested = pyqtSignal(int)

    def __init__(self, current: KezSettings, facts: list[dict], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("settings.title"))
        self.setMinimumSize(520, 460)
        self.setStyleSheet(DIALOG_STYLE)
        self._current: KezSettings = current
        self._setup_ui(facts)

    def _setup_ui(self, facts: list[dict]) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), tr("settings.tab_general"))
        tabs.addTab(self._build_voice_tab(), tr("settings.tab_voice"))
        tabs.addTab(self._build_memory_tab(facts), tr("settings.tab_memory"))
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("settings.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("settings.cancel"))
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _new_tab(self) -> tuple[QWidget, QFormLayout]:
        tab = QWidget()
        tab.setObjectName("settings_tab")
        form = QFormLayout(tab)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setSpacing(12)
        return tab, form

    def _build_general_tab(self) -> QWidget:
        tab, form = self._new_tab()

        # Каждый язык подписан на самом себе, чтобы его можно было найти при любом текущем языке
        self.language_combo = QComboBox()
        for language in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(tr("language.name", language=language), language)
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(self._current.language or "ru")))
        form.addRow(tr("settings.language"), self.language_combo)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem(tr("settings.theme_dark"), "dark")
        self.theme_combo.addItem(tr("settings.theme_light"), "light")
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(self._current.theme)))
        form.addRow(tr("settings.theme"), self.theme_combo)

        self.model_combo = QComboBox()
        self.model_combo.addItem(tr("settings.model_auto"), "")
        for model in available_models():
            self.model_combo.addItem(model.removeprefix("models/"), model)
        self.model_combo.setCurrentIndex(max(0, self.model_combo.findData(self._current.preferred_model)))
        form.addRow(tr("settings.model"), self.model_combo)

        export_row = QHBoxLayout()
        self.export_dir_edit = QLineEdit(self._current.export_dir)
        browse_btn = QPushButton(tr("settings.browse"))
        browse_btn.clicked.connect(self._choose_export_dir)
        export_row.addWidget(self.export_dir_edit)
        export_row.addWidget(browse_btn)
        form.addRow(tr("settings.export_dir"), export_row)
        return tab

    def _build_voice_tab(self) -> QWidget:
        tab, form = self._new_tab()

        self.voice_combo = QComboBox()
        self.voice_combo.addItems(TTS_VOICES)
        self.voice_combo.setCurrentText(self._current.tts_voice)
        form.addRow(tr("settings.voice"), self.voice_combo)

        self.auto_speak_check = QCheckBox(tr("settings.auto_speak"))
        self.auto_speak_check.setChecked(self._current.auto_speak)
        form.addRow(self.auto_speak_check)

        self.stream_speech_check = QCheckBox(tr("settings.stream_speech"))
        self.stream_speech_check.setChecked(self._current.stream_speech)
        form.addRow(self.stream_speech_check)

        self.wake_word_check = QCheckBox(tr("settings.wake_word"))
        self.wake_word_check.setChecked(self._current.wake_word_enabled)
        form.addRow(self.wake_word_check)

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(100, 10000)
        self.threshold_spin.setSingleStep(100)
        self.threshold_spin.setValue(self._current.wake_word_threshold)
        self.threshold_spin.setToolTip(tr("settings.threshold_tooltip"))
        form.addRow(tr("settings.threshold"), self.threshold_spin)

        hint = QLabel(tr("settings.wake_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: rgba(240, 234, 218, 0.6); font-size: 11px;")
        form.addRow(hint)
        return tab

    def _build_memory_tab(self, facts: list[dict]) -> QWidget:
        tab = QWidget()
        tab.setObjectName("settings_tab")
        layout = QVBoxLayout(tab)

        self.learn_facts_check = QCheckBox(tr("settings.learn_facts"))
        self.learn_facts_check.setChecked(self._current.learn_facts)
        layout.addWidget(self.learn_facts_check)

        layout.addWidget(QLabel(tr("settings.facts_label")))
        self.facts_list = QListWidget()
        for fact in facts:
            item = QListWidgetItem(str(fact.get("fact", "")))
            item.setData(Qt.ItemDataRole.UserRole, int(fact["id"]))
            self.facts_list.addItem(item)
        if not facts:
            placeholder = QListWidgetItem(tr("settings.facts_empty"))
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.facts_list.addItem(placeholder)
        layout.addWidget(self.facts_list, stretch=1)

        forget_btn = QPushButton(tr("settings.forget"))
        forget_btn.clicked.connect(self._forget_selected_fact)
        layout.addWidget(forget_btn, alignment=Qt.AlignmentFlag.AlignRight)
        return tab

    def _choose_export_dir(self) -> None:
        folder: str = QFileDialog.getExistingDirectory(self, tr("settings.export_dialog"), self.export_dir_edit.text())
        if folder:
            self.export_dir_edit.setText(folder)

    def _forget_selected_fact(self) -> None:
        item: QListWidgetItem | None = self.facts_list.currentItem()
        if item is None or item.data(Qt.ItemDataRole.UserRole) is None:
            return
        self.fact_delete_requested.emit(int(item.data(Qt.ItemDataRole.UserRole)))
        self.facts_list.takeItem(self.facts_list.row(item))

    def _on_save(self) -> None:
        new_settings: KezSettings = replace(
            self._current,
            language=self.language_combo.currentData(),
            theme=self.theme_combo.currentData(),
            preferred_model=self.model_combo.currentData(),
            export_dir=self.export_dir_edit.text().strip() or self._current.export_dir,
            tts_voice=self.voice_combo.currentText(),
            auto_speak=self.auto_speak_check.isChecked(),
            stream_speech=self.stream_speech_check.isChecked(),
            wake_word_enabled=self.wake_word_check.isChecked(),
            wake_word_threshold=self.threshold_spin.value(),
            learn_facts=self.learn_facts_check.isChecked(),
        )
        self.settings_saved.emit(new_settings)
        self.accept()
