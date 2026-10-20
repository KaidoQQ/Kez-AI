import os
import sys
from pathlib import Path

import pytest

# Qt без окон (CI / тесты), корень проекта в sys.path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="session")
def qapp():
    """Единственный QApplication на сессию (нужен для PDF-экспорта через Qt)."""
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def export_dir(tmp_path, monkeypatch):
    """Перенаправляет папку экспорта во временную директорию."""
    from core import settings as settings_module
    monkeypatch.setattr(settings_module.settings, "export_dir", str(tmp_path))
    return tmp_path
