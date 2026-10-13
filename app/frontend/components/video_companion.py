import os
from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QWidget, QVBoxLayout


class VideoCompanionWidget(QWidget):
    """
    Виджет видео-аватара компаньона Kez с поддержкой смены анимаций (idle, search).
    """

    def __init__(
        self,
        idle_path: str,
        search_path: str,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.idle_video_path = idle_path
        self.search_video_path = search_path

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(180)
        self.video_widget.setMaximumHeight(260)
        self.layout.addWidget(self.video_widget)

        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_widget)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

        if self.idle_video_path and os.path.exists(self.idle_video_path):
            self.player.setSource(QUrl.fromLocalFile(self.idle_video_path))
            self.player.play()

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.player.play()

    def play_search(self) -> None:
        """Переключает видео на анимацию поиска."""
        if self.search_video_path and os.path.exists(self.search_video_path):
            self.player.setSource(QUrl.fromLocalFile(self.search_video_path))
            self.player.play()

    def play_idle(self) -> None:
        """Возвращает видео к фоновой idle-анимации."""
        if self.idle_video_path and os.path.exists(self.idle_video_path):
            if self.player.source() != QUrl.fromLocalFile(self.idle_video_path):
                self.player.setSource(QUrl.fromLocalFile(self.idle_video_path))
                self.player.play()
