import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from tech.database import DataBase
from core.logger import logger

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN is not configured. Add it to the .env file."
    )


def _read_mini_app_url() -> str:
    """Return a public HTTPS URL suitable for a Telegram Mini App button."""
    value = os.getenv("MINI_APP_URL", "").strip()
    if not value:
        logger.info("MINI_APP_URL is not set; the Mini App button is disabled.")
        return ""

    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        logger.warning("MINI_APP_URL must be an absolute HTTPS URL; the Mini App button is disabled.")
        return ""

    return value.rstrip("/")


db_dir = BASE_DIR.parent / "tech"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured. Add a PostgreSQL DSN to the .env file."
    )

db = DataBase(DATABASE_URL)
logger.info("PostgreSQL database configuration loaded")
