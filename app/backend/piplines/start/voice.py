import re
import time
import uuid
import wave
from pathlib import Path

from google import genai
from google.genai import types

from core.logger import logger
from core.constants.const import MODELS_FALLBACK
from core.constants.file_const import (
    CACHE_AUDIO_DIR,
    NATIVE_MIME_TYPES,
    TTS_MODELS,
    TTS_VOICE_NAME,
    TTS_SAMPLE_RATE,
    TTS_MAX_CHARS,
)
from Kez.prepare import _get_client

TRANSCRIBE_INSTRUCTION: str = (
    "Transcribe this voice message verbatim in its original language. "
    "Return ONLY the transcribed text, without quotes or comments. "
    "If there is no intelligible speech, return an empty string."
)


async def transcribe_audio(audio_path: str) -> str:
    """
    Распознаёт речь (STT): отправляет записанный файл в Gemini с fallback-моделями.
    Возвращает распознанный текст или пустую строку.
    """
    path: Path = Path(audio_path)
    if not path.is_file() or path.stat().st_size == 0:
        logger.warning(f"Аудиофайл для распознавания пуст или отсутствует: {audio_path}")
        return ""

    try:
        client: genai.Client = _get_client()
    except Exception as e:
        logger.error(f"Не удалось получить Gemini клиент для распознавания речи: {e}")
        return ""

    mime_type: str = NATIVE_MIME_TYPES.get(path.suffix.lower(), "audio/wav")
    audio_part = types.Part.from_bytes(data=path.read_bytes(), mime_type=mime_type)

    for model_name in MODELS_FALLBACK:
        try:
            logger.info(f"Распознавание речи через модель {model_name}...")
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=[audio_part, TRANSCRIBE_INSTRUCTION],
            )
            if response and response.text is not None:
                text: str = response.text.strip().strip('"«»')
                logger.info(f"Речь распознана моделью {model_name}: '{text}'")
                return text
        except Exception as e:
            logger.error(f"Ошибка распознавания речи моделью {model_name}: {e}")

    logger.error("Все fallback-модели не смогли распознать речь.")
    return ""


def prepare_text_for_speech(text: str) -> str:
    """Убирает код, ссылки и Markdown-разметку, чтобы озвучивался только живой текст."""
    cleaned: str = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    cleaned = re.sub(r"\[IMAGE:[^\]]*\]|\[FILE:[^\]]*\]", " ", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"[#*_`>|]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) > TTS_MAX_CHARS:
        cut: str = cleaned[:TTS_MAX_CHARS]
        last_dot: int = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
        cleaned = cut[:last_dot + 1] if last_dot > 0 else cut
    return cleaned


async def synthesize_speech(text: str) -> str | None:
    """
    Синтез речи (TTS) через Gemini TTS: сохраняет PCM-ответ в .wav в кэше аудио.
    Возвращает путь к файлу или None.
    """
    speech_text: str = prepare_text_for_speech(text)
    if not speech_text:
        return None

    try:
        client: genai.Client = _get_client()
        CACHE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Не удалось подготовить синтез речи: {e}")
        return None

    from core.settings import settings
    speech_config = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=settings.tts_voice or TTS_VOICE_NAME)
            )
        ),
    )

    for model_name in TTS_MODELS:
        try:
            logger.info(f"Синтез речи через модель {model_name}...")
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=f"Say in a warm, cheerful and friendly voice: {speech_text}",
                config=speech_config,
            )
            if not (response and response.candidates):
                continue

            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    output_path: Path = CACHE_AUDIO_DIR / f"tts_{int(time.time())}_{uuid.uuid4().hex[:6]}.wav"
                    with wave.open(str(output_path), "wb") as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(TTS_SAMPLE_RATE)
                        wav_file.writeframes(part.inline_data.data)
                    logger.info(f"Речь синтезирована моделью {model_name}: {output_path}")
                    return str(output_path)
        except Exception as e:
            logger.error(f"Ошибка синтеза речи моделью {model_name}: {e}")

    logger.error("Все TTS-модели не смогли синтезировать речь.")
    return None
