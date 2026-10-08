import os
import glob
import asyncio
from qasync import asyncSlot
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QFrame, QLabel, QLineEdit, QScrollArea, QSizePolicy, QScrollBar,
    QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QUrl, QTimer, QSize
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtGui import QIcon

class KezMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Kez AI Companion")
        self.resize(1100, 750)
        
        # Load animation paths dynamically
        self.frontend_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir = os.path.join(self.frontend_dir, "assets")
        anim_dir = os.path.join(self.assets_dir, "anim")
        self.icons_dir = os.path.join(self.assets_dir, "icons")
        
        idle_videos = glob.glob(os.path.join(anim_dir, "*1*.mp4"))
        search_videos = glob.glob(os.path.join(anim_dir, "*2*.mp4"))
        
        self.idle_video_path = idle_videos[0] if idle_videos else ""
        self.search_video_path = search_videos[0] if search_videos else ""

        # Central Widget Setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._setup_sidebar()
        self._setup_main_area()
        self._setup_video_player()

        # Connect buttons
        self.menu_btn.clicked.connect(self.toggle_sidebar)

    def _setup_sidebar(self) -> None:
        """Creates the left sidebar for chat history"""
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        
        # Initially open at 250px
        self.sidebar.setFixedWidth(250)
        
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(15, 20, 15, 20)
        
        self.sidebar_title = QLabel("Chat History")
        self.sidebar_layout.addWidget(self.sidebar_title)
        
        # New Chat Button
        self.new_chat_btn = QPushButton("+ New Chat")
        self.new_chat_btn.setObjectName("new_chat_btn")
        self.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_layout.addWidget(self.new_chat_btn)
        
        # TODO: A QListWidget will go here for history items
        self.sidebar_layout.addStretch()
        
        self.main_layout.addWidget(self.sidebar)

    def _setup_main_area(self) -> None:
        """Creates the central work area (Video + Chat)"""
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(20, 20, 20, 20)
        self.right_layout.setSpacing(15)
        
        # Top bar (Hamburger menu)
        self.top_bar = QHBoxLayout()
        self.menu_btn = QPushButton("")
        self.menu_btn.setIcon(QIcon(os.path.join(self.icons_dir, "chats.png")))
        self.menu_btn.setIconSize(QSize(38, 38))
        self.menu_btn.setObjectName("menu_btn")
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.setFixedSize(40, 40)
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
        
        # Companion Video Area
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(350)
        self.right_layout.addWidget(self.video_widget, stretch=1)
        
        # Chat Messages Area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setObjectName("chat_area")
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.chat_content = QWidget()
        self.chat_content.setObjectName("chat_content")
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_content)
        
        self.right_layout.addWidget(self.chat_scroll, stretch=1)
        
        # Input Field & Send Button
        self.input_layout = QHBoxLayout()
        self.input_layout.setSpacing(10)
        
        self.attach_btn = QPushButton("")
        self.attach_btn.setIcon(QIcon(os.path.join(self.icons_dir, "files.png")))
        self.attach_btn.setIconSize(QSize(38, 38))
        self.attach_btn.setObjectName("action_btn")
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.setFixedSize(45, 45)
        
        self.input_field = QLineEdit()
        self.input_field.setObjectName("input_field")
        self.input_field.setPlaceholderText("Message Kez...")
        self.input_field.setFixedHeight(45)
        
        self.voice_btn = QPushButton("")
        self.voice_btn.setIcon(QIcon(os.path.join(self.icons_dir, "micro.png")))
        self.voice_btn.setIconSize(QSize(38, 38))
        self.voice_btn.setObjectName("action_btn")
        self.voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.voice_btn.setFixedSize(45, 45)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFixedHeight(45)
        
        self.input_layout.addWidget(self.attach_btn)
        self.input_layout.addWidget(self.input_field)
        self.input_layout.addWidget(self.voice_btn)
        self.input_layout.addWidget(self.send_btn)
        
        self.right_layout.addLayout(self.input_layout)
        self.main_layout.addWidget(self.right_widget)

        # Send Signals
        self.send_btn.clicked.connect(self.handle_send)
        self.input_field.returnPressed.connect(self.handle_send)

    def _setup_video_player(self) -> None:
        """Configures the QMediaPlayer for animations"""
        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_widget)
        
        if self.idle_video_path and os.path.exists(self.idle_video_path):
            self.player.setSource(QUrl.fromLocalFile(self.idle_video_path))
            self.player.play()
            
        # Loop the video
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)

    def on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        # Restart if stopped
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.player.play()

    def toggle_sidebar(self) -> None:
        """Animates the left sidebar (Show/Hide)"""
        width = self.sidebar.width()
        target_width = 0 if width > 0 else 250
        
        self.animation = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.animation.setDuration(350)
        self.animation.setStartValue(width)
        self.animation.setEndValue(target_width)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.animation_max = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.animation_max.setDuration(350)
        self.animation_max.setStartValue(width)
        self.animation_max.setEndValue(target_width)
        self.animation_max.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.animation.start()
        self.animation_max.start()

    @asyncSlot()
    async def handle_send(self) -> None:
        """Processes the sent message"""
        text = self.input_field.text().strip()
        if not text:
            return
        
        self.add_message(text, "user")
        self.input_field.clear()
        
        # Simple heuristic to determine if we should play the search animation.
        # Your backend will eventually dictate this logic!
        search_keywords = ["search", "find", "look for", "who", "what", "where", "how", "найти", "поиск"]
        is_searching = any(word in text.lower() for word in search_keywords)
        
        if is_searching and self.search_video_path and os.path.exists(self.search_video_path):
            self.player.setSource(QUrl.fromLocalFile(self.search_video_path))
            self.player.play()
        
        #TODO Добавить тут функцию для поиска через DuckDuckGo
        # Simulate waiting for the backend response
        await asyncio.sleep(3)
        await self.simulate_backend_response(was_searching=is_searching)

    async def simulate_backend_response(self, was_searching: bool = False) -> None:
        """Temporary mock method for AI response"""
        if was_searching:
            self.add_message("I searched the web and found this for you! 🔎", "ai")
        else:
            self.add_message("That's interesting! Tell me more about it. 😊", "ai")
        
        # Revert to idle animation after response
        if self.idle_video_path and os.path.exists(self.idle_video_path):
            # Only change source if it's currently on the search animation
            if self.player.source() != QUrl.fromLocalFile(self.idle_video_path):
                self.player.setSource(QUrl.fromLocalFile(self.idle_video_path))
                self.player.play()

    def add_message(self, text: str, msg_type: str) -> None:
        """Appends a chat bubble to the UI"""
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setProperty("msg_type", msg_type)
        
        # Restrict max width so it looks like a proper chat bubble
        lbl.setMaximumWidth(600)
        
        # Force stylesheet update for dynamic properties
        lbl.setStyleSheet("/* update */")
        
        # Fade-in effect
        opacity_effect = QGraphicsOpacityEffect(lbl)
        lbl.setGraphicsEffect(opacity_effect)
        anim = QPropertyAnimation(opacity_effect, b"opacity", lbl)
        anim.setDuration(400)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        layout = QHBoxLayout()
        if msg_type == "user":
            layout.addStretch()  # Align Right
            layout.addWidget(lbl)
        else:
            layout.addWidget(lbl)
            layout.addStretch()  # Align Left
            
        # Insert just before the final stretch in the VBox
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, layout)
        
        anim.start()
        
        # Auto-scroll to bottom
        QTimer.singleShot(50, self.scroll_to_bottom)

    def scroll_to_bottom(self) -> None:
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
