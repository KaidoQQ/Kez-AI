"""Centralized logging module for UpWork AI Tool.

Logs are written:
  1. To file (plain text) → logs/app.log (rotation 5 MB × 3 files)
  2. To file (JSON) → logs/app.jsonl (rotation 10 MB × 5 files)

JSON logs contain the following fields: timestamp, level, module, logger_name, message, traceback
and are designed for integration with ELK / Grafana Loki / Grafana.

Usage:
    from logger import logger, set_ui_callback
    logger.info("Message")
    set_ui_callback(my_func) # called from the GUI thread"""

import logging
import sys
import traceback as tb_module
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
import json

#─── Determine the log directory ──────────────────────────────
#For PyInstaller: if launched from .exe, the logs are next to the exe
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    #The file is located in the settings folder, so take the parent of the parent (root folder)
    BASE_DIR = Path(__file__).resolve().parent.parent

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"
JSON_LOG_FILE = LOG_DIR / "app.jsonl"

#─── Formatting (plain-text) ─────────────────────────────
LOG_FORMAT = "[%(asctime)s] [%(levelname)-7s] %(name)-18s │ %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


#─── JSON formatter for structured logs ──────────────
class JsonFormatter(logging.Formatter):
    """Structured JSON formatter.
    Each record is one JSON string with the following fields:
      timestamp, level, module, logger_name, message, traceback"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "module": record.module,
            "logger_name": record.name,
            "message": record.getMessage(),
        }

        #Add traceback only if there is an exception
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["traceback"] = tb_module.format_exception(*record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


#─── Create a root application logger ───────────────────────
def _build_logger() -> logging.Logger:
    log = logging.getLogger("habi_bot")
    log.setLevel(logging.DEBUG)

    #1. File handler (plain-text) with rotation
    fh = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,   # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    log.addHandler(fh)

    #2. JSON file handler (structured logs for monitoring)
    jh = RotatingFileHandler(
        JSON_LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    jh.setLevel(logging.DEBUG)
    jh.setFormatter(JsonFormatter())
    log.addHandler(jh)

    #4. We also duplicate it in stderr in case of launch from the console
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    log.addHandler(sh)

    return log


logger = _build_logger()

# ─── Audit logger ─────────────────────────────────────────────
AUDIT_LOG_FILE = LOG_DIR / "audit.jsonl"

def _build_audit_logger() -> logging.Logger:
    log = logging.getLogger("audit_logger")
    log.setLevel(logging.INFO)
    log.propagate = False
    fh = RotatingFileHandler(
        AUDIT_LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(fh)
    return log

audit_log = _build_audit_logger()

def log_audit(source: str, user_id: str, url: str) -> None:
    """Writes a URL processing event to the audit log."""
    try:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "user_id": str(user_id),
            "url": url
        }
        audit_log.info(json.dumps(log_entry, ensure_ascii=False))
    except Exception as e:
        logger.exception("Failed to write to audit log: %s", e)
