import os
import glob
import asyncio
from qasync import asyncSlot
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton

from Kez.kez import KezAgent
from core.loader import db
from core.logger import logger
from app.backend.piplines.start.onboarding import OnboardingManager
from app.frontend.components.sidebar import SidebarWidget
from app.frontend.components.video_companion import VideoCompanionWidget
from app.frontend.components.chat_area import ChatAreaWidget
from app.frontend.components.input_bar import InputBarWidget


class KezMainWindow(QMainWindow):
    """
    Главное окно приложения Kez AI Companion.
    Координирует работу компонентов: сайдбара, видео-аватара, чата и панели ввода.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Kez AI Companion")
        self.resize(1100, 750)

        # Директории ресурсов
        frontend_dir: str = os.path.dirname(os.path.abspath(__file__))
        assets_dir: str = os.path.join(frontend_dir, "assets")
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

        self._setup_ui()

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
        self.main_layout.addWidget(self.sidebar)

        # 2. Правая рабочая область (Видео + Чат + Ввод)
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(20, 20, 20, 20)
        self.right_layout.setSpacing(15)

        # Верхняя панель (кнопка меню + настройки)
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

        self.settings_btn = QPushButton("")
        self.settings_btn.setIcon(QIcon(os.path.join(self.icons_dir, "settings.png")))
        self.settings_btn.setIconSize(QSize(38, 38))
        self.settings_btn.setObjectName("settings_btn")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setFixedSize(40, 40)
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
        self.right_layout.addWidget(self.input_bar)

        self.main_layout.addWidget(self.right_widget)

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
        """Обновляет список диалогов в сайдбаре."""
        try:
            chats: list[dict] = await db.get_all_chats()
            self.sidebar.update_chats(chats, self.current_chat_id)
        except Exception as e:
            logger.error(f"Не удалось загрузить список чатов: {e}")

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
        """Переключает текущий чат при выборе из сайдбара."""
        try:
            if chat_id == self.current_chat_id:
                return

            self.current_chat_id = chat_id
            logger.info(f"Выбран чат ID={self.current_chat_id}")
            await self.load_chat_messages(self.current_chat_id)
            await self.load_chats_list()
        except Exception as e:
            logger.error(f"Ошибка при переключении чата: {e}")

    async def load_chat_messages(self, chat_id: int) -> None:
        """Загружает и отрисовывает историю сообщений для выбранного чата."""
        try:
            self.chat_area.clear_messages()
            messages: list[dict] = await db.get_chat_messages(chat_id)
            for msg in messages:
                sender: str = str(msg.get("sender_type", "user"))
                text: str = str(msg.get("text_content", ""))
                self.chat_area.add_message(text, sender, animate=False)
        except Exception as e:
            logger.error(f"Не удалось загрузить сообщения для чата {chat_id}: {e}")

    @asyncSlot(str)
    async def handle_send(self, text: str) -> None:
        """Обрабатывает отправку сообщения пользователем."""
        # Если чат ещё не создан в БД (режим Gemini) — создаём его сейчас
        created_new_chat_now: bool = False
        if self.current_chat_id is None:
            short_title: str = " ".join(text.split()[:5])
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

        self.chat_area.add_message(text, "user", animate=True)

        # Сохранение в БД
        try:
            await db.add_message_to_chat(self.current_chat_id, "user", text)
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
            return

        # Если чат уже существовал под дефолтным названием — обновим заголовок
        if not created_new_chat_now:
            try:
                current_title = self.sidebar.get_current_chat_title()
                if current_title in ("Новый чат", "Основной чат"):
                    short_title = " ".join(text.split()[:5])
                    if len(short_title) > 30:
                        short_title = short_title[:27] + "..."
                    if short_title:
                        await db.update_chat_title(self.current_chat_id, short_title)
                        await self.load_chats_list()
            except Exception as e:
                logger.error(f"Не удалось обновить заголовок чата: {e}")

        # Показ индикатора набора текста
        self.chat_area.show_typing_indicator()

        # Генерация ответа агентом
        try:
            reply: str = await self.agent.generate_reply(text, self.current_chat_id)
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа KezAgent: {e}")
            reply = "Произошла ошибка при обращении к агенту Kez."
        finally:
            self.chat_area.hide_typing_indicator()

        # Анимация поиска если запущен веб-поиск
        if "[Web Search]" in reply:
            self.video_companion.play_search()

        self.chat_area.add_message(reply, "ai", animate=True)

        # Сохранение ответа в БД
        try:
            await db.add_message_to_chat(self.current_chat_id, "ai", reply)
        except Exception as e:
            logger.error(f"Не удалось сохранить ответ ассистента в БД: {e}")

        # Возврат к idle анимации
        self.video_companion.play_idle()


