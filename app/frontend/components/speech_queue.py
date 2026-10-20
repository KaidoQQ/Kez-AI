import asyncio
import re
from collections import deque
from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from core.logger import logger
from app.backend.piplines.start.voice import synthesize_speech

# Конец предложения: . ! ? … (с возможными кавычками/эмодзи) + пробел или перевод строки
SENTENCE_END_PATTERN: re.Pattern = re.compile(r"[.!?…]+[\"»)\]]*\s+|\n{2,}")
MIN_SEGMENT_CHARS: int = 60


class SpeechQueue(QObject):
    """
    Очередь озвучки по предложениям (TTS во время стриминга):
    - feed() копит текст и отправляет на синтез каждое законченное предложение (от ~60 символов)
    - синтез идёт параллельно, а воспроизведение — строго по порядку
    - finish() досылает остаток текста
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._buffer: str = ""
        self._pending: deque[asyncio.Task] = deque()
        self._is_playing: bool = False
        self._last_active: bool = False
        self.on_playing_changed = None  # колбэк(bool): Kez начал/закончил говорить

        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

    @property
    def is_active(self) -> bool:
        return self._is_playing or bool(self._pending)

    def feed(self, chunk: str) -> None:
        """Добавляет очередной чанк стрима; законченные предложения уходят на синтез."""
        self._buffer += chunk
        while True:
            match = None
            for candidate in SENTENCE_END_PATTERN.finditer(self._buffer):
                if candidate.end() >= MIN_SEGMENT_CHARS:
                    match = candidate
                    break
            if match is None:
                return
            segment: str = self._buffer[:match.end()]
            self._buffer = self._buffer[match.end():]
            self._enqueue(segment)

    def finish(self) -> None:
        """Отправляет на синтез оставшийся текст."""
        if self._buffer.strip():
            self._enqueue(self._buffer)
        self._buffer = ""

    def speak(self, text: str) -> None:
        """Озвучивает готовый текст целиком (без стриминга)."""
        self.feed(text)
        self.finish()

    def stop(self) -> None:
        """Останавливает речь и отменяет ещё не озвученные фрагменты."""
        for task in self._pending:
            task.cancel()
        self._pending.clear()
        self._buffer = ""
        self.player.stop()
        self._set_playing(False)

    def _enqueue(self, text: str) -> None:
        task: asyncio.Task = asyncio.ensure_future(synthesize_speech(text))
        task.add_done_callback(lambda _: self._pump())
        self._pending.append(task)
        self._notify_active()

    def _pump(self) -> None:
        """Проигрывает следующий фрагмент, если плеер свободен и синтез готов."""
        if self._is_playing:
            return
        while self._pending and self._pending[0].done():
            task: asyncio.Task = self._pending.popleft()
            if task.cancelled():
                continue
            try:
                audio_path: str | None = task.result()
            except Exception as e:
                logger.error(f"Ошибка синтеза фрагмента речи: {e}")
                continue
            if audio_path:
                self.player.setSource(QUrl.fromLocalFile(audio_path))
                self.player.play()
                self._set_playing(True)
                return
        if not self._pending:
            self._set_playing(False)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status in (QMediaPlayer.MediaStatus.EndOfMedia, QMediaPlayer.MediaStatus.InvalidMedia):
            self._is_playing = False
            self._pump()

    def _set_playing(self, playing: bool) -> None:
        self._is_playing = playing
        self._notify_active()

    def _notify_active(self) -> None:
        """Сообщает подписчику, когда очередь начала или закончила говорить."""
        active: bool = self.is_active
        if active != self._last_active:
            self._last_active = active
            if self.on_playing_changed:
                self.on_playing_changed(active)
