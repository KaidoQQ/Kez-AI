import array
import math
import re
import time
import wave
from PyQt6.QtCore import QObject, pyqtSignal, QIODevice
from PyQt6.QtMultimedia import QAudioSource, QAudioFormat, QMediaDevices

from core.logger import logger
from core.constants.file_const import CACHE_AUDIO_DIR

SAMPLE_RATE: int = 16000
PRE_ROLL_SECONDS: float = 0.4       # сколько звука до начала речи сохраняем
SILENCE_TO_END_SECONDS: float = 0.9  # пауза, после которой фраза считается законченной
MIN_PHRASE_SECONDS: float = 0.5
MAX_PHRASE_SECONDS: float = 12.0

# «Эй, Kez», «Кез, ...», «Кес» (частая ошибка распознавания), «Hey Kez»
WAKE_WORD_PATTERN: re.Pattern = re.compile(
    r"^\W*(?:эй|hey|hi|ok|окей)?[\s,!.]*(?:kez|kes|кез|кес|кэз|киз)\b[\s,!.:-]*(?P<command>.*)$",
    re.IGNORECASE | re.DOTALL,
)


def match_wake_word(transcript: str) -> str | None:
    """
    Проверяет, начинается ли фраза с обращения к Kez.
    Возвращает текст команды после обращения ('' — только обращение) или None.
    """
    match = WAKE_WORD_PATTERN.match(transcript.strip())
    return match.group("command").strip() if match else None


def rms_level(pcm_bytes: bytes) -> float:
    """Громкость (RMS) блока 16-bit PCM."""
    if len(pcm_bytes) < 2:
        return 0.0
    samples = array.array("h", pcm_bytes[: len(pcm_bytes) // 2 * 2])
    return math.sqrt(sum(s * s for s in samples) / len(samples))


class WakeWordListener(QObject):
    """
    Фоновое прослушивание микрофона для фразы «Эй, Kez» (без нажатия кнопок).
    Локальный детектор голосовой активности (по громкости) вырезает фразы,
    и только они отправляются на распознавание — тишина в API не уходит.
    """
    phrase_captured = pyqtSignal(str)  # путь к .wav с фразой

    def __init__(self, threshold: int = 900, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.threshold: int = threshold
        self._source: QAudioSource | None = None
        self._device: QIODevice | None = None
        self._paused: bool = False
        self._reset_phrase()

    @property
    def is_running(self) -> bool:
        return self._source is not None

    def start(self) -> None:
        if self._source is not None:
            return
        audio_format = QAudioFormat()
        audio_format.setSampleRate(SAMPLE_RATE)
        audio_format.setChannelCount(1)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            logger.warning("Микрофон не найден — прослушивание «Эй, Kez» не запущено.")
            return
        self._source = QAudioSource(device, audio_format, self)
        self._device = self._source.start()
        self._device.readyRead.connect(self._on_ready_read)
        logger.info("Прослушивание фразы «Эй, Kez» запущено.")

    def stop(self) -> None:
        if self._source is not None:
            self._source.stop()
            self._source.deleteLater()
        self._source = None
        self._device = None
        self._reset_phrase()
        logger.info("Прослушивание фразы «Эй, Kez» остановлено.")

    def set_paused(self, paused: bool) -> None:
        """Пауза, пока Kez говорит или идёт ручная запись — чтобы не слушать самого себя."""
        self._paused = paused
        if paused:
            self._reset_phrase()

    def _reset_phrase(self) -> None:
        self._pre_roll: bytearray = bytearray()
        self._phrase: bytearray = bytearray()
        self._in_speech: bool = False
        self._silence_bytes: int = 0

    def _on_ready_read(self) -> None:
        if self._device is None:
            return
        chunk: bytes = bytes(self._device.readAll())
        if not chunk or self._paused:
            return

        bytes_per_second: int = SAMPLE_RATE * 2
        loud: bool = rms_level(chunk) >= self.threshold

        if not self._in_speech:
            self._pre_roll += chunk
            max_pre_roll: int = int(PRE_ROLL_SECONDS * bytes_per_second)
            if len(self._pre_roll) > max_pre_roll:
                del self._pre_roll[: len(self._pre_roll) - max_pre_roll]
            if loud:
                self._in_speech = True
                self._phrase = bytearray(self._pre_roll)
                self._silence_bytes = 0
            return

        self._phrase += chunk
        self._silence_bytes = 0 if loud else self._silence_bytes + len(chunk)

        phrase_seconds: float = len(self._phrase) / bytes_per_second
        if self._silence_bytes >= SILENCE_TO_END_SECONDS * bytes_per_second or phrase_seconds >= MAX_PHRASE_SECONDS:
            speech_seconds: float = phrase_seconds - self._silence_bytes / bytes_per_second
            phrase: bytes = bytes(self._phrase)
            self._reset_phrase()
            if speech_seconds >= MIN_PHRASE_SECONDS:
                self._emit_phrase(phrase)

    def _emit_phrase(self, pcm: bytes) -> None:
        try:
            CACHE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            path = CACHE_AUDIO_DIR / f"wake_{int(time.time() * 1000)}.wav"
            with wave.open(str(path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(SAMPLE_RATE)
                wav_file.writeframes(pcm)
            self.phrase_captured.emit(str(path))
        except Exception as e:
            logger.error(f"Не удалось сохранить фразу для распознавания: {e}")
