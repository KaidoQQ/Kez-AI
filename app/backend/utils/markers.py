"""Разбор служебных маркеров медиа в тексте сообщений: [IMAGE:path] и [FILE:path]."""

import re

MARKER_PATTERN: re.Pattern = re.compile(r"\[(IMAGE|FILE):([^\]]*)\]")


def split_message_markers(text: str) -> list[tuple[str, str]]:
    """
    Разбивает сообщение на последовательность сегментов:
    ('text', '...') | ('IMAGE', path) | ('FILE', path). Пустые текстовые сегменты пропускаются.
    """
    segments: list[tuple[str, str]] = []
    last_end: int = 0
    for match in MARKER_PATTERN.finditer(text):
        before: str = text[last_end:match.start()].strip()
        if before:
            segments.append(("text", before))
        segments.append((match.group(1), match.group(2).strip()))
        last_end = match.end()
    tail: str = text[last_end:].strip()
    if tail:
        segments.append(("text", tail))
    return segments


def find_last_image(messages: list[dict]) -> str | None:
    """Возвращает путь к последнему изображению в истории сообщений чата."""
    for message in reversed(messages):
        images: list[str] = [path for kind, path in split_message_markers(str(message.get("text_content", ""))) if kind == "IMAGE"]
        if images:
            return images[-1]
    return None
