import os
import glob
import asyncio
from datetime import datetime
from qasync import asyncSlot
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QIcon, QAction, QDragEnterEvent, QDropEvent, QCloseEvent
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QSystemTrayIcon, QMenu, QApplication
)

from Kez.kez import KezAgent
from core.loader import db
from core.logger import logger
from core import settings as settings_module
from core.settings import KezSettings, save_settings
from app.backend.piplines.start.onboarding import OnboardingManager
from app.backend.piplines.start.voice import transcribe_audio
from app.backend.utils.markers import split_message_markers
from app.frontend.components.sidebar import SidebarWidget
from app.frontend.components.video_companion import VideoCompanionWidget
from app.frontend.components.chat_area import ChatAreaWidget
from app.frontend.components.input_bar import InputBarWidget
from app.frontend.components.speech_queue import SpeechQueue
from app.frontend.components.wake_word import WakeWordListener, match_wake_word
from app.frontend.components.pet_window import PetWindow
from app.frontend.components.settings_dialog import SettingsDialog

FRONTEND_DIR: str = os.path.dirname(os.path.abspath(__file__))
REMINDER_CHECK_INTERVAL_MS: int = 15_000


def apply_theme(theme: str) -> None:
    """Применяет тему: базовый style.qss + переопределения style_light.qss для светлой темы."""
    stylesheet: str = ""
    for name in ("style.qss", "style_light.qss" if theme == "light" else ""):
        path: str = os.path.join(FRONTEND_DIR, name) if name else ""
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                stylesheet += f.read() + "\n"
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(stylesheet)


class KezMainWindow(QMainWindow):
    """
    Главное окно приложения Kez AI Companion.
    Координирует работу компонентов: сайдбара, видео-аватара, чата и панели ввода,
    а также фоновые сервисы: озвучку, «Эй, Kez», напоминания, трей и режим питомца.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Kez AI Companion")
        self.resize(1100, 750)
        self.setAcceptDrops(True)

        # Директории ресурсов
        assets_dir: str = os.path.join(FRONTEND_DIR, "assets")
        anim_dir: str = os.path.join(assets_dir, "anim")
        self.icons_dir: str = os.path.join(assets_dir, "icons")

        idle_videos = glob.glob(os.path.join(anim_dir, "*1*.mp4"))
        search_videos = glob.glob(os.path.join(anim_dir, "*2*.mp4"))
        self.idle_video_path: str = idle_videos[0] if idle_videos else ""
        self.search_video_path: str = search_videos[0] if search_videos else ""

        # Инициализация агента и сессии
        self.agent: KezAgent = KezAgent()
        self.onboarding: OnboardingManager = OnboardingManager()
        self.current_chat_id: int | None = None
        self._is_processing: bool = False
        self._checking_reminders: bool = False

        # Озвучка ответов Kez (TTS) — по предложениям, в порядке генерации
        self.speech = SpeechQueue(self)
        self.speech.on_playing_changed = lambda _: self._update_wake_pause()

        # «Эй, Kez» — фоновое прослушивание микрофона
        self.wake_listener = WakeWordListener(settings_module.settings.wake_word_threshold, self)
        self.wake_listener.phrase_captured.connect(self.handle_wake_phrase)

        apply_theme(settings_module.settings.theme)
        self._setup_ui()
        self._setup_pet_and_tray()

        # Проверка напоминаний
        self.reminder_timer = QTimer(self)
        self.reminder_timer.setInterval(REMINDER_CHECK_INTERVAL_MS)
        self.reminder_timer.timeout.connect(self.check_reminders)

    def _setup_ui(self) -> None:
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Левый сайдбар
        self.sidebar = SidebarWidget()
        self.sidebar.new_chat_requested.connect(self.handle_new_chat)
        self.sidebar.chat_selected.connect(self.handle_chat_selected)
        self.sidebar.chat_rename_requested.connect(self.handle_chat_rename)
        self.sidebar.chat_delete_requested.connect(self.handle_chat_delete)
        self.sidebar.search_requested.connect(self.handle_search)
        self.main_layout.addWidget(self.sidebar)

        # 2. Правая рабочая область (Видео + Чат + Ввод)
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(20, 20, 20, 20)
        self.right_layout.setSpacing(15)

        # Верхняя панель (кнопка меню + режим питомца + настройки)
        self.top_bar = QHBoxLayout()
        self.menu_btn = QPushButton("")
        self.menu_btn.setIcon(QIcon(os.path.join(self.icons_dir, "chats.png")))
        self.menu_btn.setIconSize(QSize(38, 38))
        self.menu_btn.setObjectName("menu_btn")
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.setFixedSize(40, 40)
        self.menu_btn.clicked.connect(self.sidebar.toggle_sidebar)
        self.top_bar.addWidget(self.menu_btn)

        self.top_bar.addStretch()

        self.pet_btn = QPushButton("🐤")
        self.pet_btn.setObjectName("pet_btn")
        self.pet_btn.setToolTip("Режим питомца: Kez в углу экрана поверх окон")
        self.pet_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pet_btn.setFixedSize(40, 40)
        self.pet_btn.clicked.connect(self.enter_pet_mode)
        self.top_bar.addWidget(self.pet_btn)

        self.settings_btn = QPushButton("")
        self.settings_btn.setIcon(QIcon(os.path.join(self.icons_dir, "settings.png")))
        self.settings_btn.setIconSize(QSize(38, 38))
        self.settings_btn.setObjectName("settings_btn")
        self.settings_btn.setToolTip("Настройки")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.clicked.connect(self.open_settings)
        self.top_bar.addWidget(self.settings_btn)

        self.right_layout.addLayout(self.top_bar)

        # Видео-аватар (компактная высота, чтобы чат занимал максимум пространства)
        self.video_companion = VideoCompanionWidget(self.idle_video_path, self.search_video_path)
        self.video_companion.setMaximumHeight(260)
        self.right_layout.addWidget(self.video_companion, stretch=0)

        # Область сообщений чата (главный эластичный элемент)
        self.chat_area = ChatAreaWidget()
        self.right_layout.addWidget(self.chat_area, stretch=1)

        # Панель ввода
        self.input_bar = InputBarWidget(self.icons_dir)
        self.input_bar.message_submitted.connect(self.handle_send)
        self.input_bar.meet_kez_clicked.connect(self.start_onboarding_flow)
        self.input_bar.voice_recorded.connect(self.handle_voice_message)
        self.input_bar.recording_state_changed.connect(lambda _: self._update_wake_pause())
        self.right_layout.addWidget(self.input_bar)

        self.main_layout.addWidget(self.right_widget)

    def _setup_pet_and_tray(self) -> None:
        # Режим «питомца»
        self.pet_window = PetWindow(self.idle_video_path)
        self.pet_window.message_submitted.connect(self.handle_pet_message)
        self.pet_window.restore_requested.connect(self.exit_pet_mode)

        # Иконка в системном трее: уведомления напоминаний + быстрые действия
        self.tray_icon = QSystemTrayIcon(QIcon(os.path.join(self.icons_dir, "chats.png")), self)
        self.tray_icon.setToolTip("Kez AI Companion")
        tray_menu = QMenu(self)
        open_action = QAction("Открыть Kez", self)
        open_action.triggered.connect(self.exit_pet_mode)
        pet_action = QAction("Режим питомца 🐤", self)
        pet_action.triggered.connect(self.enter_pet_mode)
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(open_action)
        tray_menu.addAction(pet_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()

    def start_background_services(self) -> None:
        """Запускается после подключения к БД: напоминания и (по настройке) «Эй, Kez»."""
        self.reminder_timer.start()
        QTimer.singleShot(1000, self.check_reminders)
        if settings_module.settings.wake_word_enabled:
            self.wake_listener.start()

    # ---------- Режим питомца и трей ----------

    def enter_pet_mode(self) -> None:
        self.hide()
        self.video_companion.player.pause()
        self.pet_window.show_pet()
        logger.info("Kez перешёл в режим питомца.")

    def exit_pet_mode(self) -> None:
        self.pet_window.hide_pet()
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.video_companion.player.play()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.exit_pet_mode()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.wake_listener.stop()
        self.speech.stop()
        self.pet_window.close()
        self.tray_icon.hide()
        super().closeEvent(event)

    # ---------- Перетаскивание файлов ----------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        local_files: list[str] = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if local_files:
            self.input_bar.add_attachments(local_files)
            event.acceptProposedAction()

    # ---------- Настройки ----------

    @asyncSlot()
    async def open_settings(self) -> None:
        facts: list[dict] = await db.get_user_facts()
        dialog = SettingsDialog(settings_module.settings, facts, self)
        dialog.settings_saved.connect(self.apply_new_settings)
        dialog.fact_delete_requested.connect(self.handle_fact_delete)
        # open() вместо exec(): не запускаем вложенный цикл событий поверх qasync
        dialog.open()

    def apply_new_settings(self, new_settings: KezSettings) -> None:
        save_settings(new_settings)
        apply_theme(new_settings.theme)

        self.wake_listener.threshold = new_settings.wake_word_threshold
        if new_settings.wake_word_enabled and not self.wake_listener.is_running:
            self.wake_listener.start()
        elif not new_settings.wake_word_enabled and self.wake_listener.is_running:
            self.wake_listener.stop()
        logger.info(f"Настройки применены: {new_settings}")

    @asyncSlot(int)
    async def handle_fact_delete(self, fact_id: int) -> None:
        await db.delete_user_fact(fact_id)

    # ---------- Сессия и чаты ----------

    @asyncSlot()
    async def load_initial_chat_session(self) -> None:
        """Загружает последний активный чат или переходит в режим нового."""
        try:
            chats: list[dict] = await db.get_all_chats()
            if chats:
                self.current_chat_id = int(chats[0]["id"])
                await self.load_chat_messages(self.current_chat_id)
            else:
                self.current_chat_id = None
                self.chat_area.clear_messages()

            await self.load_chats_list()

            # Проверяем условия для показа кнопки "Get to know Kez":
            # 1. Онбординг еще не был завершен
            # 2. Нет сообщений в текущем чате или чатов нет вовсе
            is_completed: bool = await db.is_onboarding_completed()
            if not is_completed:
                messages_count: int = 0
                if self.current_chat_id is not None:
                    msgs = await db.get_chat_messages(self.current_chat_id)
                    messages_count = len(msgs)
                if len(chats) <= 1 and messages_count == 0:
                    self.input_bar.show_meet_button()
                    logger.info("Кнопка 'Get to know Kez' показана при первом старте.")
        except Exception as e:
            logger.error(f"Ошибка при инициализации сессии чата: {e}")

    @asyncSlot()
    async def start_onboarding_flow(self) -> None:
        """Запускает процесс интерактивного знакомства."""
        try:
            if self.current_chat_id is None:
                self.current_chat_id = await db.create_chat("Знакомство с Kez")
                await self.load_chats_list()

            first_question: str = self.onboarding.start_onboarding()
            self.input_bar.set_placeholder(self.onboarding.get_current_placeholder())
            self.chat_area.add_message(first_question, "ai", animate=True)
            if self.current_chat_id is not None:
                await db.add_message_to_chat(self.current_chat_id, "ai", first_question)
            self.input_bar.set_focus()
        except Exception as e:
            logger.error(f"Ошибка при запуске знакомства с Kez: {e}")

    @asyncSlot()
    async def load_chats_list(self) -> None:
        """Обновляет список диалогов в сайдбаре (если не открыт поиск)."""
        if self.sidebar.is_searching:
            return
        try:
            chats: list[dict] = await db.get_all_chats()
            self.sidebar.update_chats(chats, self.current_chat_id)
        except Exception as e:
            logger.error(f"Не удалось загрузить список чатов: {e}")

    @asyncSlot(str)
    async def handle_search(self, query: str) -> None:
        """Поиск по истории всех чатов; пустой запрос возвращает обычный список."""
        if not query:
            await self.load_chats_list()
            return
        results: list[dict] = await db.search_messages(query)
        # Пока шёл запрос, текст поиска мог измениться — показываем только актуальное
        if self.sidebar.search_field.text().strip() == query:
            self.sidebar.show_search_results(query, results)

    @asyncSlot()
    async def handle_new_chat(self) -> None:
        """Переключает в режим нового чата (как в Gemini: чат создастся в БД при отправке первого сообщения)."""
        self.current_chat_id = None
        self.chat_area.clear_messages()
        await self.load_chats_list()
        self.input_bar.set_placeholder("Message Kez...")
        self.input_bar.set_focus()
        logger.info("Открыт пустой экран для нового чата.")

    @asyncSlot(int, str)
    async def handle_chat_rename(self, chat_id: int, new_title: str) -> None:
        """Переименовывает чат в базе данных и обновляет список."""
        try:
            success = await db.update_chat_title(chat_id, new_title)
            if success:
                await self.load_chats_list()
                logger.info(f"Чат ID={chat_id} успешно переименован в '{new_title}'")
        except Exception as e:
            logger.error(f"Ошибка при переименовании чата ID={chat_id}: {e}")

    @asyncSlot(int)
    async def handle_chat_delete(self, chat_id: int) -> None:
        """Удаляет чат из базы данных и переключает на следующий или пустой экран."""
        try:
            success = await db.delete_chat(chat_id)
            if not success:
                return

            if self.current_chat_id == chat_id:
                # Переключаемся на оставшийся активный чат или в режим нового
                remaining_chats = await db.get_all_chats()
                if remaining_chats:
                    self.current_chat_id = int(remaining_chats[0]["id"])
                    await self.load_chat_messages(self.current_chat_id)
                else:
                    self.current_chat_id = None
                    self.chat_area.clear_messages()

            await self.load_chats_list()
        except Exception as e:
            logger.error(f"Ошибка при удалении чата ID={chat_id}: {e}")

    @asyncSlot(int)
    async def handle_chat_selected(self, chat_id: int) -> None:
        """Переключает текущий чат при выборе из сайдбара (в т.ч. из результатов поиска)."""
        try:
            if chat_id == self.current_chat_id:
                return

            self.current_chat_id = chat_id
            logger.info(f"Выбран чат ID={self.current_chat_id}")
            await self.load_chat_messages(self.current_chat_id)
            await self.load_chats_list()
        except Exception as e:
            logger.error(f"Ошибка при переключении чата: {e}")

    def render_message(self, text: str, sender: str, animate: bool = False) -> None:
        """Отрисовывает сообщение с маркерами [IMAGE:path] / [FILE:path] как текст + карточки."""
        for kind, value in split_message_markers(text):
            if kind == "IMAGE":
                if os.path.exists(value):
                    self.chat_area.add_image_message(value, sender=sender)
            elif kind == "FILE":
                self.chat_area.add_file_message(value, sender=sender)
            else:
                self.chat_area.add_message(value, sender, animate=animate)

    async def load_chat_messages(self, chat_id: int) -> None:
        """Загружает и отрисовывает историю сообщений для выбранного чата."""
        try:
            self.chat_area.clear_messages()
            messages: list[dict] = await db.get_chat_messages(chat_id)
            for msg in messages:
                self.render_message(str(msg.get("text_content", "")), str(msg.get("sender_type", "user")))
        except Exception as e:
            logger.error(f"Не удалось загрузить сообщения для чата {chat_id}: {e}")

    # ---------- Голос ----------

    def _update_wake_pause(self) -> None:
        """«Эй, Kez» не слушает, пока Kez говорит, идёт ручная запись или обработка сообщения."""
        self.wake_listener.set_paused(
            self.speech.is_active or self.input_bar._is_recording or self._is_processing
        )

    @asyncSlot(str)
    async def handle_voice_message(self, audio_path: str) -> None:
        """Распознаёт голосовое сообщение и отправляет его как обычное, с озвучкой ответа."""
        self.chat_area.show_typing_indicator()
        try:
            text: str = await transcribe_audio(audio_path)
        except Exception as e:
            logger.error(f"Ошибка распознавания голосового сообщения: {e}")
            text = ""
        finally:
            self.chat_area.hide_typing_indicator()

        if not text:
            self.chat_area.add_message("Чирик? Я не расслышал... 🎙️ Попробуй сказать ещё раз, чуть ближе к микрофону!", "ai")
            return

        await self.process_message(text, speak_reply=True)

    @asyncSlot(str)
    async def handle_wake_phrase(self, audio_path: str) -> None:
        """Фраза из фонового прослушивания: реагируем, только если она начинается с «Kez»."""
        if self._is_processing:
            return
        try:
            transcript: str = await transcribe_audio(audio_path)
        finally:
            try:
                os.remove(audio_path)
            except OSError:
                pass

        command: str | None = match_wake_word(transcript) if transcript else None
        if command is None:
            return

        logger.info(f"Услышано обращение к Kez: '{transcript}'")
        if self.isHidden() and not self.pet_window.isVisible():
            self.exit_pet_mode()

        if not command:
            # Только «Эй, Kez» — ждём команду обычной записью
            if self.pet_window.isVisible():
                self.pet_window.show_bubble("Да-да? Слушаю! 🎙️")
            self.input_bar.start_recording()
            QTimer.singleShot(6000, self.input_bar.stop_recording)
            return

        reply: str = await self.process_message(command, speak_reply=True)
        if self.pet_window.isVisible() and reply:
            self.pet_window.show_bubble(self._bubble_text(reply))

    # ---------- Режим питомца: быстрые сообщения ----------

    @staticmethod
    def _bubble_text(reply: str) -> str:
        parts: list[str] = [value for kind, value in split_message_markers(reply) if kind == "text"]
        return " ".join(parts).strip() or "Готово! Открой окно, чтобы посмотреть. 🐦"

    @asyncSlot(str)
    async def handle_pet_message(self, text: str) -> None:
        reply: str = await self.process_message(text)
        self.pet_window.show_bubble(self._bubble_text(reply) if reply else "Ой, что-то пошло не так... 🐦")

    # ---------- Напоминания ----------

    @asyncSlot()
    async def check_reminders(self) -> None:
        """Проверяет наступившие напоминания: уведомление в трее, сообщение в чат, анимация Kez."""
        if self._checking_reminders or db.pool is None:
            return
        self._checking_reminders = True
        try:
            for reminder in await db.get_due_reminders(datetime.now()):
                await db.mark_reminder_done(int(reminder["id"]))
                text: str = f"⏰ Чирик-чирик! Напоминаю: **{reminder['text_content']}**"
                plain_text: str = f"⏰ Напоминаю: {reminder['text_content']}"
                logger.info(f"Сработало напоминание ID={reminder['id']}: {reminder['text_content']}")

                if QSystemTrayIcon.isSystemTrayAvailable():
                    self.tray_icon.showMessage("Kez напоминает 🐦", str(reminder["text_content"]),
                                               QSystemTrayIcon.MessageIcon.Information, 10000)

                chat_id: int | None = reminder.get("chat_id")
                if chat_id is not None:
                    await db.add_message_to_chat(int(chat_id), "ai", text)
                if chat_id is not None and chat_id == self.current_chat_id:
                    self.chat_area.add_message(text, "ai", animate=True)

                if self.pet_window.isVisible():
                    self.pet_window.show_bubble(plain_text, timeout_ms=30000)

                # Kez «встрепенулся»: короткая активная анимация
                self.video_companion.play_search()
                QTimer.singleShot(4000, self.video_companion.play_idle)

                if settings_module.settings.auto_speak:
                    self.speech.speak(plain_text)
        except Exception as e:
            logger.error(f"Ошибка при проверке напоминаний: {e}")
        finally:
            self._checking_reminders = False

    # ---------- Отправка сообщений ----------

    @asyncSlot(str)
    async def handle_send(self, text: str) -> None:
        """Обрабатывает отправку сообщения пользователем."""
        await self.process_message(text)

    async def process_message(self, text: str, speak_reply: bool = False) -> str:
        """
        Общий пайплайн обработки сообщения (текст / голос / вложения / питомец):
        создание чата, сохранение в БД, онбординг или стриминг ответа агента.
        Возвращает сохранённый текст ответа Kez.
        """
        self.speech.stop()
        self._is_processing = True
        self._update_wake_pause()
        try:
            return await self._process_message(text, speak_reply)
        finally:
            self._is_processing = False
            self._update_wake_pause()

    async def _process_message(self, text: str, speak_reply: bool) -> str:
        attachment_paths: list[str] = self.input_bar.take_attachments()
        attachment_names: str = ", ".join(os.path.basename(p) for p in attachment_paths)
        display_text: str = f"📎 {attachment_names}\n\n{text}".strip() if attachment_paths else text

        # Если чат ещё не создан в БД (режим Gemini) — создаём его сейчас
        created_new_chat_now: bool = False
        if self.current_chat_id is None:
            short_title: str = " ".join((text or attachment_names).split()[:5])
            if len(short_title) > 30:
                short_title = short_title[:27] + "..."
            title: str = short_title or "Новый чат"
            try:
                new_id = await db.create_chat(title)
                self.current_chat_id = int(new_id) if new_id else 1
                created_new_chat_now = True
                await self.load_chats_list()
            except Exception as e:
                logger.error(f"Не удалось создать чат при первом сообщении: {e}")
                self.current_chat_id = 1

        self.chat_area.add_message(display_text, "user", animate=True)

        # Сохранение в БД
        try:
            await db.add_message_to_chat(self.current_chat_id, "user", display_text)
        except Exception as e:
            logger.error(f"Не удалось сохранить сообщение пользователя в БД: {e}")

        # Если активен онбординг (знакомство с Kez) — обрабатываем строго в пайплайне онбординга
        if self.onboarding.is_active:
            self.chat_area.show_typing_indicator()
            try:
                reply, is_done = await self.onboarding.process_user_input(text)
                if not is_done:
                    self.input_bar.set_placeholder(self.onboarding.get_current_placeholder())
                else:
                    self.input_bar.set_placeholder("Message Kez...")
            except Exception as e:
                logger.error(f"Ошибка при обработке ответа онбординга: {e}")
                reply = "Чирик! 🐦 Мои перышки запутались... Давай попробуем еще раз!"
            finally:
                self.chat_area.hide_typing_indicator()

            self.chat_area.add_message(reply, "ai", animate=True)
            try:
                await db.add_message_to_chat(self.current_chat_id, "ai", reply)
            except Exception as e:
                logger.error(f"Не удалось сохранить ответ онбординга в БД: {e}")
            return reply

        # Если чат уже существовал под дефолтным названием — обновим заголовок
        if not created_new_chat_now:
            try:
                current_title = self.sidebar.get_current_chat_title()
                if current_title in ("Новый чат", "Основной чат"):
                    short_title = " ".join((text or attachment_names).split()[:5])
                    if len(short_title) > 30:
                        short_title = short_title[:27] + "..."
                    if short_title:
                        await db.update_chat_title(self.current_chat_id, short_title)
                        await self.load_chats_list()
            except Exception as e:
                logger.error(f"Не удалось обновить заголовок чата: {e}")

        # Озвучка: для голосовых сообщений или если включена автоозвучка
        should_speak: bool = speak_reply or settings_module.settings.auto_speak
        stream_speech: bool = should_speak and settings_module.settings.stream_speech

        # Показ индикатора набора текста
        self.chat_area.show_typing_indicator()

        # Потоковый стриминг ответа Kez
        streaming_browser = None
        stream_buffer: list[str] = []
        saved_db_content: list[str] = []

        try:
            async for event in self.agent.generate_reply_stream(text, self.current_chat_id, attachment_paths):
                # Скрываем индикатор при первом событии
                self.chat_area.hide_typing_indicator()

                if event.event_type == "token" and event.text:
                    if streaming_browser is None:
                        streaming_browser, stream_buffer = self.chat_area.create_streaming_message("ai")
                    self.chat_area.append_stream_chunk(streaming_browser, stream_buffer, event.text)
                    saved_db_content.append(event.text)
                    if stream_speech:
                        self.speech.feed(event.text)

                elif event.event_type == "image":
                    streaming_browser = None
                    stream_buffer = []

                    if event.image_path and os.path.exists(event.image_path):
                        self.chat_area.add_image_message(event.image_path, event.prompt, "ai")
                        saved_db_content.append(f"\n[IMAGE:{event.image_path}]\n")

                    if event.text:
                        self.chat_area.add_message(event.text, "ai", animate=True)
                        saved_db_content.append(event.text)

                elif event.event_type == "file":
                    streaming_browser = None
                    stream_buffer = []

                    if event.file_path:
                        self.chat_area.add_file_message(event.file_path, "ai")
                        saved_db_content.append(f"\n[FILE:{event.file_path}]\n")

                    if event.text:
                        self.chat_area.add_message(event.text, "ai", animate=True)
                        saved_db_content.append(event.text)

                elif event.event_type == "error":
                    if streaming_browser is None:
                        streaming_browser, stream_buffer = self.chat_area.create_streaming_message("ai")
                    self.chat_area.append_stream_chunk(streaming_browser, stream_buffer, event.text)
                    saved_db_content.append(event.text)

        except Exception as e:
            logger.error(f"Ошибка при потоковой генерации ответа KezAgent: {e}")
            if streaming_browser is None:
                self.chat_area.add_message("Ой, у меня что-то пошло не так при обработке сообщения... Чирик! 🐦", "ai")
        finally:
            self.chat_area.hide_typing_indicator()

        # Сохранение полного ответа в БД
        final_saved_text: str = "".join(saved_db_content).strip()
        if final_saved_text:
            try:
                await db.add_message_to_chat(self.current_chat_id, "ai", final_saved_text)
            except Exception as e:
                logger.error(f"Не удалось сохранить ответ ассистента в БД: {e}")

        # Возврат к idle анимации
        self.video_companion.play_idle()

        # Озвучка: остаток стрима или весь текстовый ответ целиком
        if stream_speech:
            self.speech.finish()
        elif should_speak and final_saved_text:
            self.speech.speak(self._bubble_text(final_saved_text))

        return final_saved_text
