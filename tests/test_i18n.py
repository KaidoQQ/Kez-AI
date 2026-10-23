import re
from datetime import datetime, timedelta

import pytest

from core import i18n
from core import settings as settings_module
from core.i18n import tr, detect_language, localize_prompt, LOCALES


def test_locales_have_identical_keys():
    assert set(LOCALES["ru"]) == set(LOCALES["en"])


@pytest.mark.parametrize("key", sorted(LOCALES["ru"]))
def test_placeholders_match_between_languages(key):
    placeholders = lambda text: sorted(re.findall(r"\{(\w+)\}", text))
    assert placeholders(LOCALES["ru"][key]) == placeholders(LOCALES["en"][key])


def test_tr_uses_current_language(monkeypatch):
    assert tr("settings.save") == "Сохранить"
    monkeypatch.setattr(settings_module.settings, "language", "en")
    assert tr("settings.save") == "Save"
    assert tr("settings.save", language="ru") == "Сохранить"


def test_tr_formats_and_falls_back(monkeypatch):
    assert tr("reminder.due_today", time="18:30") == "сегодня в 18:30"
    monkeypatch.setitem(LOCALES["en"], "only.ru", "")
    monkeypatch.setitem(LOCALES["ru"], "only.ru", "только по-русски")
    monkeypatch.setattr(settings_module.settings, "language", "en")
    assert tr("only.ru") == "только по-русски"
    assert tr("missing.key") == "missing.key"


def test_empty_language_means_default(monkeypatch):
    monkeypatch.setattr(settings_module.settings, "language", "")
    assert i18n.current_language() == "ru"


@pytest.mark.parametrize("text, expected", [
    ("привет", "ru"),
    ("hello there", "en"),
    ("Kez, как дела?", "ru"),
])
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_detect_language_without_letters_uses_settings(monkeypatch):
    monkeypatch.setattr(settings_module.settings, "language", "en")
    assert detect_language("👍 123") == "en"


def test_prompts_get_default_language(monkeypatch):
    from core.constants.const import PROMPTS
    assert "{DEFAULT_LANGUAGE}" not in PROMPTS["memory"]
    assert "Russian" in PROMPTS.get("memory")
    monkeypatch.setattr(settings_module.settings, "language", "en")
    assert "use English" in PROMPTS.get("memory")
    assert localize_prompt("x {DEFAULT_LANGUAGE}") == "x English"


def test_quick_replies_follow_message_language():
    from app.backend.piplines.start.routing import classify_intent_by_rules
    ru_reply = classify_intent_by_rules("привет").extracted_data["direct_reply"]
    en_reply = classify_intent_by_rules("hello").extracted_data["direct_reply"]
    assert re.search("[а-яё]", ru_reply, re.IGNORECASE)
    assert not re.search("[а-яё]", en_reply, re.IGNORECASE)


def test_backend_messages_switch_language(monkeypatch):
    from app.backend.piplines.start.reminders import format_due
    now = datetime(2026, 10, 20, 14, 0)
    monkeypatch.setattr(settings_module.settings, "language", "en")
    assert format_due(now + timedelta(days=1), now) == "tomorrow at 14:00"
    assert format_due(now + timedelta(days=5), now) == "25.10 at 14:00"


def test_onboarding_questions_are_localized(monkeypatch):
    from app.backend.piplines.start.onboarding import OnboardingManager
    monkeypatch.setattr(settings_module.settings, "language", "en")
    manager = OnboardingManager()
    assert manager.start_onboarding().startswith("Chirp!")
    assert manager.get_current_placeholder() == "Type your name..."


def test_language_dialog_switches_texts(qapp):
    from app.frontend.components.language_dialog import LanguageDialog
    dialog = LanguageDialog("ru")
    assert dialog.continue_btn.text() == "Продолжить"
    dialog._select("en")
    assert dialog.selected_language == "en"
    assert dialog.continue_btn.text() == "Continue"


def test_main_window_retranslates_live(qapp, monkeypatch):
    from app.frontend.main_window import KezMainWindow
    window = KezMainWindow()
    assert window.sidebar.new_chat_btn.text() == "+ Новый чат"
    monkeypatch.setattr(settings_module.settings, "language", "en")
    window.retranslate_ui()
    assert window.sidebar.new_chat_btn.text() == "+ New Chat"
    assert window.input_bar.send_btn.text() == "Send"
    assert window.tray_quit_action.text() == "Quit"
    window.wake_listener.stop()
    window.close()
