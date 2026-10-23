"""
Интернационализация Kez AI (ru / en).

- Тексты интерфейса и фиксированные реплики Kez лежат в core/locales/<язык>.json.
- tr("ключ", **параметры) возвращает строку на языке из настроек (settings.language).
- Если ключа нет в выбранном языке — берётся русский, если нет и там — сам ключ.
"""

import json
import re
from pathlib import Path

from core.logger import logger

LOCALES_DIR: Path = Path(__file__).resolve().parent / "locales"
SUPPORTED_LANGUAGES: tuple[str, ...] = ("ru", "en")
DEFAULT_LANGUAGE: str = "ru"

CYRILLIC_PATTERN: re.Pattern = re.compile(r"[а-яё]", re.IGNORECASE)
LATIN_PATTERN: re.Pattern = re.compile(r"[a-z]", re.IGNORECASE)


def _load_locales() -> dict[str, dict[str, str]]:
    locales: dict[str, dict[str, str]] = {}
    for language in SUPPORTED_LANGUAGES:
        path: Path = LOCALES_DIR / f"{language}.json"
        try:
            locales[language] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Не удалось загрузить локаль {path}: {e}")
            locales[language] = {}
    return locales


LOCALES: dict[str, dict[str, str]] = _load_locales()


def current_language() -> str:
    """Язык из настроек; пустое значение (язык ещё не выбран) — язык по умолчанию."""
    from core.settings import settings
    return settings.language if settings.language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def tr(key: str, language: str | None = None, **params: object) -> str:
    """Переводит ключ на текущий (или явно указанный) язык и подставляет параметры."""
    lang: str = language if language in SUPPORTED_LANGUAGES else current_language()
    text: str = LOCALES.get(lang, {}).get(key) or LOCALES[DEFAULT_LANGUAGE].get(key) or key
    if params:
        try:
            return text.format(**params)
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Ошибка подстановки параметров в перевод '{key}': {e}")
    return text


def detect_language(text: str) -> str:
    """
    Определяет язык сообщения пользователя по алфавиту:
    кириллица — ru, латиница — en, иначе — язык из настроек.
    """
    cyrillic: int = len(CYRILLIC_PATTERN.findall(text))
    latin: int = len(LATIN_PATTERN.findall(text))
    if cyrillic == latin == 0:
        return current_language()
    return "ru" if cyrillic >= latin else "en"


def llm_language_name(language: str | None = None) -> str:
    """Название языка для промптов LLM ("Russian" / "English")."""
    return tr("language.llm_name", language=language)


def localize_prompt(template: str) -> str:
    """Подставляет язык по умолчанию в шаблон промпта (плейсхолдер {DEFAULT_LANGUAGE})."""
    return template.replace("{DEFAULT_LANGUAGE}", llm_language_name())
