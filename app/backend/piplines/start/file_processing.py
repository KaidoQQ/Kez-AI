import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google.genai import types

from core.loader import db
from core.logger import logger
from core.constants.const import PROMPTS
from core.constants.file_const import (
    NATIVE_MIME_TYPES,
    MAX_INLINE_FILE_BYTES,
    DEFAULT_EXPORT_FORMAT,
)
from app.backend.utils.file_tools import extract_text, detect_export_format, export_document
from app.backend.utils.llm_fallback import generate_response_with_fallback, generate_stream_with_fallback
from app.backend.piplines.start.memory import format_chat_history

# Запросы на чтение файла без вложения: просим прикрепить файл, а не экспортируем
READ_FILE_PATTERN: re.Pattern = re.compile(
    r"\b(прочитай|открой|прикрепи|скинь|проанализируй|read|open|analy[sz]e)\b", re.IGNORECASE
)
EXPORT_FILE_PATTERN: re.Pattern = re.compile(
    r"\b(сохрани|экспортируй|запиши|выгрузи|сделай|создай|save|export|create|write)\b", re.IGNORECASE
)
DEFAULT_ANALYSIS_REQUEST: str = "Расскажи, что в этом файле, и выдели главное."


@dataclass
class FileExportResult:
    """Результат экспорта документа."""
    success: bool
    file_path: str = ""
    export_format: str = ""
    error_message: str = ""


def is_read_request(text: str) -> bool:
    """True, если пользователь хочет прочитать/проанализировать файл, а не сохранить."""
    return bool(READ_FILE_PATTERN.search(text)) and not EXPORT_FILE_PATTERN.search(text)


def build_analysis_prompt(file_name: str, file_content: str, user_request: str) -> str:
    template: str = PROMPTS.get("file_analysis", "")
    if not template:
        logger.warning("Промпт 'file_analysis' не найден, используется упрощённый шаблон.")
        return f"Файл: {file_name}\n\n{file_content}\n\nЗапрос пользователя: {user_request}"

    return (
        template.replace("{FILE_NAME}", file_name)
        .replace("{FILE_CONTENT}", file_content)
        .replace("{USER_REQUEST}", user_request)
    )


def prepare_file_contents(paths: list[Path]) -> tuple[list[Any], list[str], list[str]]:
    """
    Готовит вложения к отправке в Gemini.
    Возвращает (бинарные части, текстовые блоки '=== имя ===\\nтекст', ошибки для пользователя).
    """
    binary_parts: list[Any] = []
    text_blocks: list[str] = []
    problems: list[str] = []

    for path in paths:
        suffix: str = path.suffix.lower()
        if not path.is_file():
            problems.append(f"«{path.name}» — файл не найден")
            continue
        try:
            file_text: str | None = extract_text(path)
            if file_text is not None:
                if file_text.strip():
                    text_blocks.append(f"=== {path.name} ===\n{file_text}")
                else:
                    problems.append(f"«{path.name}» — файл пустой")
            elif suffix in NATIVE_MIME_TYPES:
                if path.stat().st_size > MAX_INLINE_FILE_BYTES:
                    problems.append(f"«{path.name}» — больше {MAX_INLINE_FILE_BYTES // (1024 * 1024)} МБ")
                    continue
                binary_parts.append(types.Part.from_bytes(data=path.read_bytes(), mime_type=NATIVE_MIME_TYPES[suffix]))
                text_blocks.append(f"=== {path.name} === (приложен отдельно)")
            else:
                problems.append(f"«{path.name}» — формат {suffix or '?'} не поддерживается")
        except Exception as e:
            logger.error(f"Ошибка при чтении вложения {path}: {e}")
            problems.append(f"«{path.name}» — не удалось прочитать ({e})")

    return binary_parts, text_blocks, problems


async def analyze_file_stream(file_paths: list[str] | str, user_request: str):
    """
    Пайплайн анализа вложений (стриминг, один или несколько файлов):
    1. Текстовые файлы и .docx читаются локально и подставляются в промпт.
    2. PDF, изображения и аудио отправляются в Gemini нативно (inline bytes).
    3. Выдаёт чанки ответа модели.
    """
    if isinstance(file_paths, str):
        file_paths = [file_paths]
    paths: list[Path] = [Path(p) for p in file_paths]
    request_text: str = user_request.strip() or DEFAULT_ANALYSIS_REQUEST

    binary_parts, text_blocks, problems = prepare_file_contents(paths)
    if problems:
        yield "⚠️ " + "; ".join(problems) + "\n\n"
    if not text_blocks:
        yield (
            "Чирик... тут мне нечего прочитать. 🐦\n"
            "Поддерживаются текстовые файлы и код, .docx, PDF, изображения и аудио."
        )
        return

    file_names: str = ", ".join(p.name for p in paths)
    prompt: str = build_analysis_prompt(file_names, "\n\n".join(text_blocks), request_text)
    contents: str | list[Any] = [*binary_parts, prompt] if binary_parts else prompt

    logger.info(f"Анализ файлов {file_names}, запрос: '{request_text}'")
    got_any_chunk: bool = False
    async for chunk in generate_stream_with_fallback(contents):
        got_any_chunk = True
        yield chunk

    if not got_any_chunk:
        yield "Ой, не получилось разобрать файл — все модели сейчас недоступны. Попробуй чуть позже! 🐦"


async def export_file_from_request(user_text: str, chat_id: int) -> FileExportResult:
    """
    Пайплайн экспорта документа:
    1. Определяет формат (pdf / md / txt / docx / xlsx / pptx) по тексту запроса.
    2. Генерирует Markdown-документ по запросу и последним 10 сообщениям чата.
    3. Если LLM недоступна — сохраняет саму историю диалога.
    4. Сохраняет файл в папку экспорта из настроек.
    """
    export_format: str = detect_export_format(user_text) or DEFAULT_EXPORT_FORMAT

    try:
        messages: list[dict[str, Any]] = await db.get_chat_messages(chat_id)
    except Exception as e:
        logger.error(f"Ошибка при получении истории чата {chat_id} для экспорта: {e}")
        messages = []

    # Последнее сообщение — сам запрос на экспорт, в документ его не включаем
    history: list[dict[str, Any]] = messages[:-1][-10:]
    history_text: str = format_chat_history(history)

    template: str = PROMPTS.get("file_export", "")
    prompt: str = (
        template.replace("{CHAT_HISTORY}", history_text)
        .replace("{USER_REQUEST}", user_text)
        .replace("{EXPORT_FORMAT}", export_format)
        if template
        else f"Составь Markdown-документ ({export_format}) по запросу: {user_text}\n\nКонтекст диалога:\n{history_text}"
    )

    document_text: str = await generate_response_with_fallback(prompt)
    document_text = re.sub(r"^```(?:markdown|md)?\s*|\s*```$", "", document_text.strip()).strip()
    if not document_text:
        logger.warning("LLM не сгенерировала документ, экспортируем историю диалога как есть.")
        document_text = f"# Диалог с Kez\n\n{history_text}"

    try:
        saved_path: Path = export_document(document_text, export_format)
        return FileExportResult(success=True, file_path=str(saved_path), export_format=export_format)
    except Exception as e:
        logger.error(f"Ошибка при экспорте документа в {export_format}: {e}")
        return FileExportResult(
            success=False,
            export_format=export_format,
            error_message="Не удалось сохранить файл... Перышки дрогнули. Попробуй ещё раз!"
        )
