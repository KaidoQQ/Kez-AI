import os
import time
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer, QUrl, QEvent, QObject
from PyQt6.QtGui import QIcon, QKeyEvent, QKeySequence, QGuiApplication, QImage
from PyQt6.QtMultimedia import QMediaCaptureSession, QAudioInput, QMediaRecorder, QMediaFormat
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog
from core.logger import logger
from core.constants.file_const import CACHE_AUDIO_DIR, CACHE_FILES_DIR, MAX_ATTACHMENTS

ATTACH_FILE_FILTER: str = (
    "Поддерживаемые файлы (*.txt *.md *.csv *.json *.xml *.yaml *.yml *.log *.html *.py *.js *.ts "
    "*.java *.c *.cpp *.cs *.go *.rs *.sql *.docx *.pdf *.png *.jpg *.jpeg *.webp *.gif *.mp3 *.wav *.m4a *.ogg);;"
    "Все файлы (*)"
)


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
        self._glow_step: int = 0
        self._glow_timer: QTimer | None = None
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

        # Контейнер для кнопки знакомства (по центру над полем ввода)
        self.banner_layout = QHBoxLayout()
        self.banner_layout.setContentsMargins(0, 0, 0, 0)
        self.banner_layout.addStretch()

        self.meet_btn = QPushButton("Get to know Kez ✨")
        self.meet_btn.setObjectName("meet_kez_btn")
        self.meet_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.meet_btn.setFixedHeight(34)
        self.meet_btn.clicked.connect(self._on_meet_clicked)
        self.meet_btn.hide()  # По умолчанию скрыта, отображается только при проверке условий
        self.banner_layout.addWidget(self.meet_btn)

        self.banner_layout.addStretch()
        self.main_container_layout.addLayout(self.banner_layout)

        # Плашка прикреплённого файла (над полем ввода)
        self.attachment_layout = QHBoxLayout()
        self.attachment_layout.setContentsMargins(4, 0, 0, 0)
        self.attachment_label = QLabel("")
        self.attachment_label.setStyleSheet("color: #F0EADA; font-size: 12px;")
        self.attachment_label.hide()
        self.attachment_layout.addWidget(self.attachment_label)

        self.attachment_remove_btn = QPushButton("✕")
        self.attachment_remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attachment_remove_btn.setFixedSize(22, 22)
        self.attachment_remove_btn.setToolTip("Убрать вложение")
        self.attachment_remove_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #F0EADA; border: none; font-weight: bold; }"
            "QPushButton:hover { color: #EF4444; }"
        )
        self.attachment_remove_btn.clicked.connect(self.clear_attachment)
        self.attachment_remove_btn.hide()
        self.attachment_layout.addWidget(self.attachment_remove_btn)
        self.attachment_layout.addStretch()
        self.main_container_layout.addLayout(self.attachment_layout)

        # Нижняя панель ввода
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_layout.setSpacing(10)

        # Кнопка вложений
        self.attach_btn = QPushButton("")
        self.attach_btn.setIcon(QIcon(os.path.join(self.icons_dir, "files.png")))
        self.attach_btn.setIconSize(QSize(38, 38))
        self.attach_btn.setObjectName("action_btn")
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.setFixedSize(45, 45)
        self.attach_btn.setToolTip("Прикрепить файл")
        self.attach_btn.clicked.connect(self._on_attach_clicked)
        self.controls_layout.addWidget(self.attach_btn)

        # Поле ввода текста
        self.input_field = QLineEdit()
        self.input_field.setObjectName("input_field")
        self.input_field.setPlaceholderText("Message Kez...")
        self.input_field.setFixedHeight(45)
        self.input_field.returnPressed.connect(self._on_submit)
        self.input_field.installEventFilter(self)
        self.controls_layout.addWidget(self.input_field)

        # Кнопка микрофона
        self.voice_btn = QPushButton("")
        self.voice_btn.setIcon(QIcon(os.path.join(self.icons_dir, "micro.png")))
        self.voice_btn.setIconSize(QSize(38, 38))
        self.voice_btn.setObjectName("action_btn")
        self.voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.voice_btn.setFixedSize(45, 45)
        self.voice_btn.setToolTip("Голосовое сообщение")
        self.voice_btn.clicked.connect(self._on_voice_clicked)
        self.controls_layout.addWidget(self.voice_btn)

        # Кнопка отправки
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFixedHeight(45)
        self.send_btn.clicked.connect(self._on_submit)
        self.controls_layout.addWidget(self.send_btn)

        self.main_container_layout.addLayout(self.controls_layout)

    def show_meet_button(self) -> None:
        """Показывает кнопку знакомства и запускает неяркую пульсацию темными тонами."""
        self.meet_btn.show()
        if self._glow_timer is None:
            self._glow_timer = QTimer(self)
            self._glow_timer.setInterval(120)
            self._glow_timer.timeout.connect(self._pulse_glow)
        self._glow_timer.start()

    def hide_meet_button(self) -> None:
        """Скрывает кнопку знакомства и останавливает таймер."""
        if self._glow_timer and self._glow_timer.isActive():
            self._glow_timer.stop()
        self.meet_btn.hide()

    def _pulse_glow(self) -> None:
        """Плавно меняет темные цвета фона кнопки для создания ненавязчивого мерцания."""
        # Колебание синей составляющей в диапазоне темных цветов (RGB: 18..35, 26..48, 45..75)
        self._glow_step = (self._glow_step + 1) % 40
        factor = self._glow_step if self._glow_step <= 20 else (40 - self._glow_step)
        
        r = 18 + int(factor * 0.7)
        g = 26 + int(factor * 1.0)
        b = 48 + int(factor * 1.3)
        border_alpha = 40 + int(factor * 4.0)
        
        style = f"""
            QPushButton#meet_kez_btn {{
                background-color: rgb({r}, {g}, {b});
                color: #F0EADA;
                border: 1px solid rgba(240, 234, 218, {border_alpha});
                border-radius: 17px;
                padding: 6px 18px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton#meet_kez_btn:hover {{
                background-color: rgb({r + 15}, {g + 20}, {b + 30});
                border: 1px solid rgba(240, 234, 218, 180);
            }}
        """
        self.meet_btn.setStyleSheet(style)

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
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Прикрепить файлы", "", ATTACH_FILE_FILTER)
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
            self.voice_btn.setToolTip("Остановить запись")
            self.input_field.setPlaceholderText("🎙️ Слушаю... нажми на микрофон ещё раз, чтобы отправить")
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
        self.voice_btn.setToolTip("Голосовое сообщение")
        self.input_field.setPlaceholderText("Message Kez...")

    def _on_recorder_state_changed(self, state: QMediaRecorder.RecorderState) -> None:
        if state == QMediaRecorder.RecorderState.StoppedState and self._recorder is not None:
            audio_path: str = self._recorder.actualLocation().toLocalFile()
            if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                logger.info(f"Запись голоса завершена: {audio_path}")
                self.voice_recorded.emit(audio_path)

    def _on_recorder_error(self, error: QMediaRecorder.Error, error_string: str) -> None:
        logger.error(f"Ошибка записи голоса ({error}): {error_string}")
        self._reset_voice_button()

    def set_placeholder(self, text: str) -> None:
        """Устанавливает подсказку в поле ввода."""
        self.input_field.setPlaceholderText(text)

    def set_focus(self) -> None:
        self.input_field.setFocus()

