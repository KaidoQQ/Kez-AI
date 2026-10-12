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
        self.current_chat_id: int = 1

        self._setup_ui()

        # Загрузка сессии чата после старта event loop
        QTimer.singleShot(100, lambda: asyncio.create_task(self.load_initial_chat_session()))

    def _setup_ui(self) -> None:
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Левый сайдбар
        self.sidebar = SidebarWidget()
        self.sidebar.new_chat_requested.connect(lambda: asyncio.create_task(self.handle_new_chat()))
        self.sidebar.chat_selected.connect(lambda cid: asyncio.create_task(self.handle_chat_selected(cid)))
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

        # Видео-аватар
        self.video_companion = VideoCompanionWidget(self.idle_video_path, self.search_video_path)
        self.right_layout.addWidget(self.video_companion, stretch=1)

        # Область сообщений чата
        self.chat_area = ChatAreaWidget()
        self.right_layout.addWidget(self.chat_area, stretch=1)

        # Панель ввода
        self.input_bar = InputBarWidget(self.icons_dir)
        self.input_bar.message_submitted.connect(lambda text: asyncio.create_task(self.handle_send(text)))
        self.right_layout.addWidget(self.input_bar)

        self.main_layout.addWidget(self.right_widget)

    @asyncSlot()
    async def load_initial_chat_session(self) -> None:
        """Загружает последний активный чат или создает дефолтный."""
        try:
            self.current_chat_id = await db.get_or_create_default_chat()
            await self.load_chats_list()
            await self.load_chat_messages(self.current_chat_id)
        except Exception as e:
            logger.error(f"Ошибка при инициализации сессии чата: {e}")

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
        """Создает новый чат и переключает окно."""
        try:
            new_chat_id = await db.create_chat("Новый чат")
            if new_chat_id is None:
                logger.error("Не удалось создать новый чат в базе данных")
                return

            self.current_chat_id = new_chat_id
            self.chat_area.clear_messages()
            await self.load_chats_list()
            self.input_bar.set_focus()
            logger.info(f"Переключено на новый чат ID={self.current_chat_id}")
        except Exception as e:
            logger.error(f"Ошибка при создании нового чата: {e}")

    @asyncSlot()
    async def handle_chat_selected(self, chat_id: int) -> None:
        """Переключает текущий чат при выборе из сайдбара."""
        try:
            if chat_id == self.current_chat_id:
                return

            self.current_chat_id = chat_id
            logger.info(f"Выбран чат ID={self.current_chat_id}")
            await self.load_chat_messages(self.current_chat_id)
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

    @asyncSlot()
    async def handle_send(self, text: str) -> None:
        """Обрабатывает отправку сообщения пользователем."""
        self.chat_area.add_message(text, "user", animate=True)

        # Сохранение в БД
        try:
            await db.add_message_to_chat(self.current_chat_id, "user", text)
        except Exception as e:
            logger.error(f"Не удалось сохранить сообщение пользователя в БД: {e}")

        # Авто-переименование нового чата по первой фразе
        try:
            current_title = self.sidebar.get_current_chat_title()
            if current_title in ("Новый чат", "Основной чат"):
                short_title: str = " ".join(text.split()[:5])
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
