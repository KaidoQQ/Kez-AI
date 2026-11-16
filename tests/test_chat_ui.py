"""Interaction regressions for the native assistant-style UI (no network)."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QPushButton

from app.frontend.components.input_bar import InputBarWidget
from app.frontend.components.chat_area import ChatAreaWidget
from app.frontend.theme import apply_theme
from core import settings


def test_composer_enter_submits_shift_enter_inserts_newline(qapp):
    bar = InputBarWidget("")
    messages = []
    bar.message_submitted.connect(messages.append)
    bar.input_field.setText("First line")
    bar.input_field.moveCursor(bar.input_field.textCursor().MoveOperation.End)
    QTest.keyClick(bar.input_field, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
    QTest.keyClicks(bar.input_field, "Second line")
    assert messages == []
    assert bar.input_field.text() == "First line\nSecond line"
    QTest.keyClick(bar.input_field, Qt.Key.Key_Return)
    assert messages == ["First line\nSecond line"]
    assert bar.input_field.text() == ""
    QTest.keyClick(bar.input_field, Qt.Key.Key_Return)
    assert len(messages) == 1
    bar.close()


def test_attachment_only_submission_preserves_files_until_consumed(qapp, tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("hello")
    bar = InputBarWidget("")
    messages = []
    bar.message_submitted.connect(messages.append)
    bar.add_attachments([str(path), str(path)])
    bar.send_btn.click()
    assert messages == [""]
    assert bar.take_attachments() == [str(path)]
    assert bar.attachment_paths == []
    assert bar.attachment_label.isHidden()
    bar.close()


def test_stream_copy_clear_and_welcome_suggestions(qapp):
    area = ChatAreaWidget()
    area.resize(800, 500)
    area.show()
    selected = []
    area.suggestion_selected.connect(selected.append)
    area.suggestions[0][1].click()
    assert selected and "текст" in selected[0]
    browser, buffer = area.create_streaming_message()
    area.append_stream_chunk(browser, buffer, "**Hello** ")
    area.append_stream_chunk(browser, buffer, "world")
    assert area.welcome.isHidden()
    copy = area.content_widget.findChild(QPushButton, "copy_btn")
    copy.click()
    assert qapp.clipboard().text() == "**Hello** world"
    area.clear_messages()
    qapp.processEvents()
    assert not area.welcome.isHidden()
    assert area.chat_layout.count() == 1
    area.close()


def test_both_themes_and_live_translation(qapp, monkeypatch):
    from app.frontend.components.settings_dialog import SettingsDialog
    for theme in ("dark", "light"):
        apply_theme(theme)
        dialog = SettingsDialog(settings.settings, [])
        assert not dialog.styleSheet()  # Inherit the shared theme, including light mode.
        dialog.close()
    area = ChatAreaWidget()
    monkeypatch.setattr(settings.settings, "language", "en")
    area.retranslate_ui()
    assert area.welcome_title.text() == "Where shall we begin?"
    area.close()
