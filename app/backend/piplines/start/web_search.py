"""
Web Search Pipeline for Kez AI Companion.

Пайплайн поиска информации в интернете:
1. Санитизация запроса (удаление инъекций, сохранение семантики)
2. Поиск через DuckDuckGo (Top-N результатов со сниппетами)
3. Кеширование результатов на 5 минут (TTLCache)
4. Параллельный 3-уровневый каскадный сбор контента (httpx -> curl_cffi -> Playwright)
5. Извлечение чистого контента через trafilatura
6. Агрегация источников с атрибуцией
7. Формирование промпта и синтез ответа через Gemini с fallback-моделями
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from cachetools import TTLCache
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS
import trafilatura

from core.logger import logger
from core.const import PROMPTS, PROMPTS_DIR
from app.backend.utils.llm_fallback import generate_response_with_fallback
from app.backend.utils.text_cleaner import sanitize_search_query, extract_keywords


# Кэш результатов поисковых запросов: до 100 запросов, TTL 300 секунд (5 минут)
_search_cache: TTLCache = TTLCache(maxsize=100, ttl=300)

# Флаг доступности curl_cffi
try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession
    CURL_CFFI_AVAILABLE: bool = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    logger.warning("Библиотека curl_cffi не установлена, уровень 2 будет пропущен.")

# Флаг доступности playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE: bool = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Библиотека playwright не установлена, уровень 3 (браузер) будет пропущен.")


@dataclass
class SearchResult:
    """Результат из поисковой выдачи DuckDuckGo."""
    url: str
    title: str
    snippet: str


@dataclass
class ParsedPage:
    """Разобранный контент страницы."""
    url: str
    title: str
    content: str
    source_type: str  # 'httpx' | 'curl_cffi' | 'playwright' | 'snippet'


async def search_duckduckgo(query: str, max_results: int = 5) -> list[SearchResult]:
    """
    Выполняет поиск в DuckDuckGo и возвращает список результатов.
    
    :param query: Поисковый запрос.
    :param max_results: Максимальное количество результатов.
    :return: Список объектов SearchResult.
    """
    cached = _search_cache.get(query)
    if cached is not None:
        logger.info(f"Поисковой запрос '{query}' получен из TTLCache ({len(cached)} результатов)")
        return cached

    results: list[SearchResult] = []
    try:
        logger.info(f"Выполняется поиск DuckDuckGo по запросу: '{query}'")
        loop = asyncio.get_running_loop()
        
        def _fetch_ddg() -> list[dict[str, Any]]:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))

        raw_results = await loop.run_in_executor(None, _fetch_ddg)

        for item in raw_results:
            href: str = str(item.get("href") or item.get("link") or "").strip()
            title: str = str(item.get("title") or "").strip()
            body: str = str(item.get("body") or item.get("snippet") or "").strip()
            if href:
                results.append(SearchResult(url=href, title=title, snippet=body))

        if results:
            _search_cache[query] = results
            logger.info(f"Найдено {len(results)} ссылок в DuckDuckGo и сохранено в кеш.")
        else:
            logger.warning(f"DuckDuckGo вернул пустой список для '{query}'.")

    except Exception as e:
        logger.error(f"Ошибка при поиске через DuckDuckGo: {e}")

    return results


async def fetch_with_httpx(url: str, timeout: float = 8.0) -> str | None:
    """
    Уровень 1: Быстрый асинхронный HTTP-запрос через httpx с маскировкой под браузер.
    
    :param url: URL для загрузки.
    :param timeout: Таймаут в секундах.
    :return: HTML-разметка страницы или None при ошибке/блокировке.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.text
            logger.warning(f"[httpx] Статус {response.status_code} для {url}")
            return None
    except httpx.TimeoutException:
        logger.warning(f"[httpx] Таймаут ({timeout}s) для {url}")
        return None
    except Exception as e:
        logger.error(f"[httpx] Ошибка запроса к {url}: {e}")
        return None


async def fetch_with_curl_cffi(url: str, timeout: float = 10.0) -> str | None:
    """
    Уровень 2: Запрос через curl_cffi с имитацией TLS/JA3 отпечатков Chrome для обхода Cloudflare.
    
    :param url: URL для загрузки.
    :param timeout: Таймаут в секундах.
    :return: HTML-разметка страницы или None.
    """
    if not CURL_CFFI_AVAILABLE:
        return None

    try:
        async with CurlAsyncSession(impersonate="chrome") as session:
            response = await session.get(url, timeout=timeout)
            if response.status_code == 200:
                logger.info(f"[curl_cffi] Успешно загружен {url}")
                return response.text
            logger.warning(f"[curl_cffi] Статус {response.status_code} для {url}")
            return None
    except Exception as e:
        logger.error(f"[curl_cffi] Ошибка при запросе к {url}: {e}")
        return None


async def fetch_with_playwright(url: str, timeout_ms: int = 15000) -> str | None:
    """
    Уровень 3: Загрузка через headless-браузер Playwright для сайтов с чистым JS-рендером.
    
    :param url: URL страницы.
    :param timeout_ms: Таймаут в миллисекундах.
    :return: HTML разметка или None.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                )
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                # Короткая пауза для базового рендеринга
                await asyncio.sleep(1.0)
                content = await page.content()
                logger.info(f"[playwright] Страница успешно отрисована: {url}")
                return content
            finally:
                await browser.close()
    except Exception as e:
        logger.error(f"[playwright] Ошибка парсинга {url}: {e}")
        return None


def extract_clean_text(html: str) -> str:
    """
    Извлекает чистый читаемый контент из HTML с помощью trafilatura.
    
    :param html: Исходный HTML.
    :return: Чистый текст статьи / страницы.
    """
    if not html:
        return ""
    try:
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            output_format="txt"
        )
        return extracted.strip() if extracted else ""
    except Exception as e:
        logger.error(f"Ошибка извлечения текста trafilatura: {e}")
        return ""


def is_content_valid(text: str, keywords: list[str]) -> bool:
    """
    Проверяет валидность полученного текста:
    1. Длина более 200 символов
    2. При наличии ключевых слов хотя бы одно должно присутствовать в тексте
    
    :param text: Извлечённый текст.
    :param keywords: Список ключевых слов запроса.
    :return: True если контент полезен, иначе False.
    """
    if len(text) < 200:
        return False

    if not keywords:
        return True

    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


async def parse_single_url(result: SearchResult, keywords: list[str]) -> ParsedPage | None:
    """
    Парсит один URL по каскаду (httpx -> curl_cffi -> playwright).
    
    :param result: Результат поиска.
    :param keywords: Ключевые слова запроса.
    :return: ParsedPage или None если все уровни не вернули валидный контент.
    """
    url: str = result.url

    # Уровень 1: httpx
    html = await fetch_with_httpx(url)
    if html:
        text = extract_clean_text(html)
        if is_content_valid(text, keywords):
            return ParsedPage(url=url, title=result.title, content=text[:3000], source_type="httpx")

    # Уровень 2: curl_cffi (если httpx не вернул или контент пустой/защищен)
    logger.info(f"Переход на уровень 2 (curl_cffi) для {url}")
    html = await fetch_with_curl_cffi(url)
    if html:
        text = extract_clean_text(html)
        if is_content_valid(text, keywords):
            return ParsedPage(url=url, title=result.title, content=text[:3000], source_type="curl_cffi")

    # Уровень 3: Playwright (тяжелый headless браузер)
    logger.info(f"Переход на уровень 3 (playwright) для {url}")
    html = await fetch_with_playwright(url)
    if html:
        text = extract_clean_text(html)
        if is_content_valid(text, keywords):
            return ParsedPage(url=url, title=result.title, content=text[:3000], source_type="playwright")

    logger.warning(f"Не удалось получить валидный контент со страницы: {url}")
    return None


async def parse_urls_parallel(search_results: list[SearchResult], keywords: list[str]) -> list[ParsedPage]:
    """
    Параллельно парсит до 3 первых ссылок. Если сайт падает — используется сниппет.
    
    :param search_results: Список результатов выдачи.
    :param keywords: Ключевые слова запроса.
    :return: Список ParsedPage с валидным контентом или сниппетами.
    """
    targets = search_results[:3]
    if not targets:
        return []

    tasks = [parse_single_url(item, keywords) for item in targets]
    gathered_results = await asyncio.gather(*tasks, return_exceptions=True)

    parsed_pages: list[ParsedPage] = []
    for idx, res in enumerate(gathered_results):
        target = targets[idx]
        if isinstance(res, Exception):
            logger.error(f"Исключение при парсинге {target.url}: {res}")
            # План Б: сниппет
            if target.snippet:
                parsed_pages.append(
                    ParsedPage(url=target.url, title=target.title, content=target.snippet, source_type="snippet")
                )
        elif res is not None:
            parsed_pages.append(res)
        else:
            # Парсинг вернул None -> План Б: сниппет из DuckDuckGo
            if target.snippet:
                parsed_pages.append(
                    ParsedPage(url=target.url, title=target.title, content=target.snippet, source_type="snippet")
                )

    return parsed_pages


def build_web_search_context(pages: list[ParsedPage]) -> tuple[str, str]:
    """
    Собирает единый контекстный блок и список ссылок на источники.
    
    :param pages: Список распарсенных страниц.
    :return: Кортеж (текст контекста, список источников с доменами).
    """
    if not pages:
        return "Никаких данных не удалось собрать из сети.", "Нет доступных ссылок."

    context_blocks: list[str] = []
    url_lines: list[str] = []

    for idx, page in enumerate(pages, start=1):
        parsed_url = urlparse(page.url)
        domain = parsed_url.netloc or page.url
        title = page.title or domain
        
        block = f"[Источник {idx}: {title} ({domain})]\n{page.content}\n"
        context_blocks.append(block)
        url_lines.append(f"{idx}. [{title}]({page.url})")

    web_context = "\n".join(context_blocks)
    source_urls = "\n".join(url_lines)
    return web_context, source_urls


def get_web_search_prompt_template() -> str:
    """
    Загружает шаблон промпта веб-поиска из кэша PROMPTS, файла или аварийного дефолта.
    
    :return: Строка шаблона промпта.
    """
    template = PROMPTS.get("web_search", "")
    if template:
        return template

    file_path = PROMPTS_DIR / "web_search.txt"
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Не удалось прочитать промпт {file_path}: {e}")

    # Fallback промпт
    return (
        "You are Kez, a witty and helpful bird companion.\n"
        "User search query: {SEARCH_QUERY}\n\n"
        "Web sources:\n{WEB_CONTEXT}\n\n"
        "Source links:\n{SOURCE_URLS}\n\n"
        "Provide an accurate, in-character summary with avian charm. List source URLs at the end."
    )


async def web_search(query: str) -> str:
    """
    Главная точка входа пайплайна веб-поиска:
    1. Санитизирует запрос
    2. Извлекает ключевые слова
    3. Ищет ссылки в DuckDuckGo
    4. Каскадно парсит топ-3 страницы (httpx -> curl_cffi -> playwright)
    5. Агрегирует контекст и источники
    6. Формирует ответ через Gemini LLM fallback chain
    
    :param query: Исходный запрос пользователя.
    :return: Ответ ассистента Kez со ссылками на источники.
    """
    try:
        sanitized_query: str = sanitize_search_query(query)
        if not sanitized_query:
            return "Чирик? Ты забыл сказать, что именно нужно найти в сети! 🐦"

        keywords: list[str] = extract_keywords(sanitized_query)
        logger.info(f"Запуск веб-поиска: query='{sanitized_query}', keywords={keywords}")

        # Поиск ссылок
        search_results = await search_duckduckgo(sanitized_query, max_results=5)
        if not search_results:
            return (
                f"Чирик-чирик! 🐦 Я облетел весь интернет по запросу «{sanitized_query}», "
                "но ничего толкового не нашёл. Попробуй уточнить запрос!"
            )

        # Параллельный парсинг контента
        pages = await parse_urls_parallel(search_results, keywords)
        web_context, source_urls = build_web_search_context(pages)

        # Сборка промпта
        template = get_web_search_prompt_template()
        try:
            from app.backend.piplines.start.memory import format_user_profile
            from core.loader import db
            user_info = await db.get_user_info()
            profile_text = format_user_profile(user_info)
        except Exception as e:
            logger.error(f"Не удалось получить user_info для веб-поиска: {e}")
            profile_text = "Информация о пользователе пока неизвестна."

        final_prompt = (
            template.replace("{USER_PROFILE_INFO}", profile_text)
            .replace("{SEARCH_QUERY}", sanitized_query)
            .replace("{WEB_CONTEXT}", web_context)
            .replace("{SOURCE_URLS}", source_urls)
        )

        # Вызов LLM
        response = await generate_response_with_fallback(final_prompt)
        if response:
            return response

        # Аварийный ответ если LLM не ответила
        return (
            f"Чирик! Я нашёл информацию в сети по запросу «{sanitized_query}», "
            f"но мои мыслительные крылья немного устали. Вот найденные источники:\n\n{source_urls}"
        )

    except Exception as e:
        logger.error(f"Критическая ошибка в пайплайне веб-поиска: {e}")
        return "Фррр... 🐦 Мой компас сбился во время поиска в интернете. Попробуем ещё разок?"
