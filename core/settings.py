"""Пользовательские настройки Kez AI (JSON-файл в ~/.kez_ai/settings.json)."""

import json
from dataclasses import dataclass, asdict, fields
from pathlib import Path

from core.logger import logger
from core.constants.const import MODELS_FALLBACK

SETTINGS_DIR: Path = Path.home() / ".kez_ai"
SETTINGS_FILE: Path = SETTINGS_DIR / "settings.json"
DEFAULT_EXPORT_DIR: Path = Path.home() / "Documents" / "Kez AI"

# Исходный порядок fallback-моделей (до применения предпочтений пользователя)
_ORIGINAL_MODELS: list[str] = list(MODELS_FALLBACK)


@dataclass
class KezSettings:
    """Набор пользовательских настроек приложения."""
    language: str = ""                      # ru | en ("" — ещё не выбран, спросить при первом запуске)
    theme: str = "dark"                     # dark | light
    tts_voice: str = "Puck"                 # голос Gemini TTS
    auto_speak: bool = False                # озвучивать все ответы, а не только голосовые
    stream_speech: bool = True              # озвучивать по предложениям во время генерации
    preferred_model: str = ""               # модель, которая пробуется первой ("" — порядок по умолчанию)
    export_dir: str = str(DEFAULT_EXPORT_DIR)
    learn_facts: bool = True                # автоматически запоминать факты о пользователе
    wake_word_enabled: bool = False         # слушать фразу «Эй, Kez»
    wake_word_threshold: int = 900          # порог громкости (RMS) для детектора речи


def load_settings() -> KezSettings:
    """Читает настройки с диска; неизвестные ключи игнорируются, отсутствующие — по умолчанию."""
    if not SETTINGS_FILE.exists():
        return KezSettings()
    try:
        raw: dict = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        known: set[str] = {f.name for f in fields(KezSettings)}
        return KezSettings(**{k: v for k, v in raw.items() if k in known})
    except Exception as e:
        logger.error(f"Не удалось прочитать настройки {SETTINGS_FILE}: {e}")
        return KezSettings()


def save_settings(new_settings: KezSettings) -> None:
    """Сохраняет настройки на диск и применяет их к текущему процессу."""
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(asdict(new_settings), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Не удалось сохранить настройки {SETTINGS_FILE}: {e}")
    apply_settings(new_settings)


def apply_settings(new_settings: KezSettings) -> None:
    """
    Применяет настройки к глобальному состоянию.
    MODELS_FALLBACK меняется на месте, чтобы все модули, импортировавшие список, увидели новый порядок.
    """
    global settings
    settings = new_settings

    ordered: list[str] = list(_ORIGINAL_MODELS)
    if new_settings.preferred_model:
        ordered = [new_settings.preferred_model] + [m for m in ordered if m != new_settings.preferred_model]
    MODELS_FALLBACK[:] = ordered


def available_models() -> list[str]:
    return list(_ORIGINAL_MODELS)


settings: KezSettings = load_settings()
apply_settings(settings)
