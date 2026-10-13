"""Text sanitization and keyword extraction utilities for web search."""

import re


def sanitize_search_query(raw_text: str) -> str:
    """
    Очищает и нормализует поисковый запрос:
    - Удаляет потенциально вредоносные скрипты, инъекции и шелл-паттерны
    - Сохраняет семантические операторы поисковика (кавычки, +, -, site:)
    - Ограничивает длину до 200 символов
    
    :param raw_text: Исходный текст запроса.
    :return: Очищенная строка поискового запроса.
    """
    if not raw_text:
        return ""

    text: str = raw_text.strip()

    # Удаление HTML тегов и скриптовых конструкций
    text = re.sub(r"<[^>]+>", " ", text)

    # Удаление явных SQL/Shell инъекционных маркеров (например, '; DROP, $(cmd), `cmd`)
    text = re.sub(r"['\"];\s*(drop|select|insert|delete|update|truncate)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\$[\(\{].*?[\)\}]", " ", text)
    text = re.sub(r"`.*?`", " ", text)

    # Замена множественных пробелов и спец-разделителей
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Ограничение длины запроса
    if len(text) > 200:
        text = text[:200].rsplit(" ", 1)[0].strip()

    return text


def extract_keywords(query: str) -> list[str]:
    """
    Извлекает список ключевых слов (длиной > 2 символов) из поискового запроса в нижнем регистре.
    
    :param query: Поисковый запрос.
    :return: Список уникальных ключевых слов.
    """
    if not query:
        return []

    words: list[str] = re.findall(r"\b\w{3,}\b", query.lower(), flags=re.UNICODE)
    # Убираем дубликаты с сохранением порядка
    seen: set[str] = set()
    result: list[str] = []
    for w in words:
        if w not in seen:
            seen.add(w)
            result.append(w)
    return result
