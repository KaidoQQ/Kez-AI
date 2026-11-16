import os
import time
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer, QUrl, QEvent, QObject
from PyQt6.QtGui import QIcon, QKeyEvent, QKeySequence, QGuiApplication, QImage
from PyQt6.QtMultimedia import QMediaCaptureSession, QAudioInput, QMediaRecorder, QMediaFormat
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog, QPlainTextEdit, QFrame, QSizePolicy
from core.logger import logger
from core.i18n import tr
from core.constants.file_const import CACHE_AUDIO_DIR, CACHE_FILES_DIR, MAX_ATTACHMENTS

ATTACH_FILE_PATTERNS: str = (
    "*.txt *.md *.csv *.json *.xml *.yaml *.yml *.log *.html *.py *.js *.ts "
    "*.java *.c *.cpp *.cs *.go *.rs *.sql *.docx *.pdf *.png *.jpg *.jpeg *.webp *.gif *.mp3 *.wav *.m4a *.ogg"
)


def attach_file_filter() -> str:
    return f"{tr('input.attach_filter_supported')} ({ATTACH_FILE_PATTERNS});;{tr('input.attach_filter_all')} (*)"


class ComposerEdit(QPlainTextEdit):
    """Multiline editor retaining the input API used by the application."""
    returnPressed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setTabChangesFocus(True)
        self.setFixedHeight(68)
        self.textChanged.connect(self._resize_to_content)

    def text(self) -> str:
        return self.toPlainText()

    def setText(self, text: str) -> None:
        self.setPlainText(text)

    def _resize_to_content(self) -> None:
        lines = sum(self.document().findBlockByNumber(i).layout().lineCount()
                    for i in range(self.document().blockCount()))
        self.setFixedHeight(min(160, max(68, lines * self.fontMetrics().lineSpacing() + 24)))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if not event.isAutoRepeat():
                self.returnPressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


class InputBarWidget(QWidget):
    """
    Нижняя панель ввода: опциональная кнопка знакомства с Kez,
    поле текста, кнопка вложений, микрофон и кнопка отправки.
    """
    message_submitted = pyqtSignal(str)
    meet_kez_clicked = pyqtSignal()
    voice_recorded = pyqtSignal(str)
    recording_state_changed = pyqtSignal(bool)

    def __init__(self, icons_dir: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.icons_dir: str = icons_dir
        self.attachment_paths: list[str] = []

        # Запись голоса (STT): сессия захвата микрофона -> .wav в кэше аудио
        self._capture_session: QMediaCaptureSession | None = None
        self._audio_input: QAudioInput | None = None
        self._recorder: QMediaRecorder | None = None
        self._is_recording: bool = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.main_container_layout = QVBoxLayout(self)
        self.main_container_layout.setContentsMargins(0, 0, 0, 0)
        self.main_container_layout.setSpacing(8)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # Контейнер для кнопки знакомства (по центру над полем ввода)
        self.banner_layout = QHBoxLayout()
        self.banner_layout.setContentsMargins(0, 0, 0, 0)
        self.banner_layout.addStretch()

        self.meet_btn = QPushButton(tr("input.meet_kez"))
        self.meet_btn.setObjectName("meet_kez_btn")
        self.meet_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.meet_btn.setFixedHeight(34)
        self.meet_btn.clicked.connect(self._on_meet_clicked)
        self.meet_btn.hide()  # По умолчанию скрыта, отображается только при проверке условий
        self.banner_layout.addWidget(self.meet_btn)

        self.banner_layout.addStretch()
        self.main_container_layout.addLayout(self.banner_layout)

        self.composer = QFrame()
        self.composer.setObjectName("composer")
        composer_layout = QVBoxLayout(self.composer)
        composer_layout.setContentsMargins(12, 10, 12, 10)
        composer_layout.setSpacing(6)
        self.main_container_layout.addWidget(self.composer)

        # Плашка прикреплённого файла (над полем ввода)
        self.attachment_layout = QHBoxLayout()
        self.attachment_layout.setContentsMargins(4, 0, 0, 0)
        self.attachment_label = QLabel("")
        self.attachment_label.setObjectName("muted")
        self.attachment_label.setWordWrap(True)
        self.attachment_label.hide()
        self.attachment_layout.addWidget(self.attachment_label)

        self.attachment_remove_btn = QPushButton("✕")
        self.attachment_remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attachment_remove_btn.setFixedSize(22, 22)
        self.attachment_remove_btn.setToolTip(tr("input.remove_attachment"))
        self.attachment_remove_btn.setObjectName("action_btn")
        self.attachment_remove_btn.clicked.connect(self.clear_attachment)
        self.attachment_remove_btn.hide()
        self.attachment_layout.addWidget(self.attachment_remove_btn)
        self.attachment_layout.addStretch()
        composer_layout.addLayout(self.attachment_layout)

        # Нижняя панель ввода
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_layout.setSpacing(10)

        # Кнопка вложений
        self.attach_btn = QPushButton("")
        self.attach_btn.setIcon(QIcon(os.path.join(self.icons_dir, "paperclip.svg")))
        self.attach_btn.setIconSize(QSize(20, 20))
        self.attach_btn.setObjectName("action_btn")
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.setFixedSize(36, 36)
        self.attach_btn.setToolTip(tr("input.attach_tooltip"))
        self.attach_btn.clicked.connect(self._on_attach_clicked)
        self.controls_layout.addWidget(self.attach_btn)

        # Поле ввода текста
        self.input_field = ComposerEdit()
        self.input_field.setObjectName("input_field")
        self.input_field.setPlaceholderText(tr("main.input_placeholder"))
        self.input_field.returnPressed.connect(self._on_submit)
        self.input_field.installEventFilter(self)
        composer_layout.addWidget(self.input_field)
        self.controls_layout.addStretch()

        # Кнопка микрофона
        self.voice_btn = QPushButton("")
        self.voice_btn.setIcon(QIcon(os.path.join(self.icons_dir, "microphone.svg")))
        self.voice_btn.setIconSize(QSize(20, 20))
        self.voice_btn.setObjectName("action_btn")
        self.voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.voice_btn.setFixedSize(36, 36)
        self.voice_btn.setToolTip(tr("input.voice_tooltip"))
        self.voice_btn.clicked.connect(self._on_voice_clicked)
        self.controls_layout.addWidget(self.voice_btn)

        # Кнопка отправки
        self.send_btn = QPushButton(tr("input.send"))
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFixedHeight(36)
        self.send_btn.clicked.connect(self._on_submit)
        self.controls_layout.addWidget(self.send_btn)

        composer_layout.addLayout(self.controls_layout)
        self.hint_label = QLabel(tr("ui.composer_hint"))
        self.hint_label.setObjectName("composer_hint")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_container_layout.addWidget(self.hint_label)
        self.input_field.setAccessibleName(tr("main.input_placeholder"))
        self.attach_btn.setAccessibleName(tr("input.attach_tooltip"))
        self.voice_btn.setAccessibleName(tr("input.voice_tooltip"))

    def show_meet_button(self) -> None:
        """Показывает кнопку знакомства с Kez."""
        self.meet_btn.show()

    def hide_meet_button(self) -> None:
        """Скрывает кнопку знакомства."""
        self.meet_btn.hide()

    def _on_meet_clicked(self) -> None:
        self.hide_meet_button()
        self.meet_kez_clicked.emit()

    def _on_submit(self) -> None:
        text: str = self.input_field.text().strip()
        if text or self.attachment_paths:
            self.input_field.clear()
            self.message_submitted.emit(text)

    # ---------- Вложения ----------

    def _on_attach_clicked(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(self, tr("input.attach_dialog"), "", attach_file_filter())
        if file_paths:
            self.add_attachments(file_paths)

    def add_attachments(self, file_paths: list[str]) -> None:
        """Добавляет файлы к следующему сообщению (до MAX_ATTACHMENTS, без дубликатов)."""
        for file_path in file_paths:
            if os.path.isfile(file_path) and file_path not in self.attachment_paths:
                self.attachment_paths.append(file_path)
        if len(self.attachment_paths) > MAX_ATTACHMENTS:
            logger.warning(f"Можно прикрепить не больше {MAX_ATTACHMENTS} файлов, лишние отброшены.")
            self.attachment_paths = self.attachment_paths[:MAX_ATTACHMENTS]
        self._refresh_attachment_label()
        self.set_focus()

    def set_attachment(self, file_path: str) -> None:
        self.add_attachments([file_path])

    def _refresh_attachment_label(self) -> None:
        if not self.attachment_paths:
            self.attachment_label.clear()
            self.attachment_label.hide()
            self.attachment_remove_btn.hide()
            return
        names: str = ", ".join(os.path.basename(p) for p in self.attachment_paths)
        self.attachment_label.setText(f"📎 {names}")
        self.attachment_label.setToolTip("\n".join(self.attachment_paths))
        self.attachment_label.show()
        self.attachment_remove_btn.show()

    def clear_attachment(self) -> None:
        self.attachment_paths = []
        self._refresh_attachment_label()

    def take_attachments(self) -> list[str]:
        """Возвращает прикреплённые файлы и очищает плашку вложений."""
        attachments: list[str] = list(self.attachment_paths)
        self.clear_attachment()
        return attachments

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Ctrl+V в поле ввода: картинка или файлы из буфера обмена становятся вложениями."""
        if (
            watched is self.input_field
            and event.type() == QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
            and event.matches(QKeySequence.StandardKey.Paste)
        ):
            if self.paste_from_clipboard():
                return True
        return super().eventFilter(watched, event)

    def paste_from_clipboard(self) -> bool:
        """Прикрепляет файлы/изображение из буфера обмена. Возвращает True, если что-то прикреплено."""
        mime_data = QGuiApplication.clipboard().mimeData()
        if mime_data is None:
            return False

        local_files: list[str] = [url.toLocalFile() for url in mime_data.urls() if url.isLocalFile()]
        if local_files:
            self.add_attachments(local_files)
            return True

        if mime_data.hasImage():
            image: QImage = QGuiApplication.clipboard().image()
            if image.isNull():
                return False
            CACHE_FILES_DIR.mkdir(parents=True, exist_ok=True)
            image_path: str = str(CACHE_FILES_DIR / f"paste_{int(time.time() * 1000)}.png")
            if image.save(image_path, "PNG"):
                logger.info(f"Изображение из буфера обмена сохранено: {image_path}")
                self.add_attachments([image_path])
                return True
        return False

    # ---------- Голосовой ввод ----------

    def _ensure_recorder(self) -> QMediaRecorder:
        if self._recorder is None:
            self._capture_session = QMediaCaptureSession(self)
            self._audio_input = QAudioInput(self)
            self._capture_session.setAudioInput(self._audio_input)

            self._recorder = QMediaRecorder(self)
            media_format = QMediaFormat()
            media_format.setFileFormat(QMediaFormat.FileFormat.Wave)
            media_format.setAudioCodec(QMediaFormat.AudioCodec.Wave)
            self._recorder.setMediaFormat(media_format)
            self._recorder.setQuality(QMediaRecorder.Quality.NormalQuality)
            self._capture_session.setRecorder(self._recorder)

            self._recorder.recorderStateChanged.connect(self._on_recorder_state_changed)
            self._recorder.errorOccurred.connect(self._on_recorder_error)
        return self._recorder

    def _on_voice_clicked(self) -> None:
        if self._is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self) -> None:
        """Начинает запись голосового сообщения с микрофона по умолчанию."""
        try:
            recorder: QMediaRecorder = self._ensure_recorder()
            CACHE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            output_path: str = str(CACHE_AUDIO_DIR / f"voice_{int(time.time())}.wav")
            recorder.setOutputLocation(QUrl.fromLocalFile(output_path))
            recorder.record()
            self._is_recording = True
            self.recording_state_changed.emit(True)
            self.voice_btn.setStyleSheet("QPushButton#action_btn { background: rgba(185, 28, 28, 220); }")
            self.voice_btn.setToolTip(tr("input.voice_stop_tooltip"))
            self.input_field.setPlaceholderText(tr("input.listening"))
            logger.info(f"Начата запись голоса: {output_path}")
        except Exception as e:
            logger.error(f"Не удалось начать запись голоса: {e}")
            self._reset_voice_button()

    def stop_recording(self) -> None:
        """Останавливает запись; путь к файлу придёт в сигнале voice_recorded."""
        if self._recorder is not None and self._is_recording:
            self._recorder.stop()
        self._reset_voice_button()

    def _reset_voice_button(self) -> None:
        if self._is_recording:
            self.recording_state_changed.emit(False)
        self._is_recording = False
        self.voice_btn.setStyleSheet("")
        self.voice_btn.setToolTip(tr("input.voice_tooltip"))
        self.input_field.setPlaceholderText(tr("main.input_placeholder"))

    def _on_recorder_state_changed(self, state: QMediaRecorder.RecorderState) -> None:
        if state == QMediaRecorder.RecorderState.StoppedState and self._recorder is not None:
            audio_path: str = self._recorder.actualLocation().toLocalFile()
            if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                logger.info(f"Запись голоса завершена: {audio_path}")
                self.voice_recorded.emit(audio_path)

    def _on_recorder_error(self, error: QMediaRecorder.Error, error_string: str) -> None:
        logger.error(f"Ошибка записи голоса ({error}): {error_string}")
        self._reset_voice_button()

    def retranslate_ui(self) -> None:
        """Обновляет тексты после смены языка."""
        self.hint_label.setText(tr("ui.composer_hint"))
        self.input_field.setAccessibleName(tr("main.input_placeholder"))
        self.attach_btn.setAccessibleName(tr("input.attach_tooltip"))
        self.voice_btn.setAccessibleName(tr("input.voice_tooltip"))
        self.meet_btn.setText(tr("input.meet_kez"))
        self.attach_btn.setToolTip(tr("input.attach_tooltip"))
        self.attachment_remove_btn.setToolTip(tr("input.remove_attachment"))
        self.send_btn.setText(tr("input.send"))
        if self._is_recording:
            self.voice_btn.setToolTip(tr("input.voice_stop_tooltip"))
            self.input_field.setPlaceholderText(tr("input.listening"))
        else:
            self.voice_btn.setToolTip(tr("input.voice_tooltip"))
            self.input_field.setPlaceholderText(tr("main.input_placeholder"))

    def set_placeholder(self, text: str) -> None:
        """Устанавливает подсказку в поле ввода."""
        self.input_field.setPlaceholderText(text)

    def set_focus(self) -> None:
        self.input_field.setFocus()

