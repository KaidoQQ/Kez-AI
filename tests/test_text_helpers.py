import array
from pathlib import Path

import pytest

from app.backend.utils.markers import split_message_markers, find_last_image
from app.backend.piplines.start.facts import should_extract_facts, parse_facts_response, format_user_facts
from app.backend.piplines.start.voice import prepare_text_for_speech
from app.backend.piplines.start.file_processing import is_read_request, prepare_file_contents
from app.frontend.components.wake_word import match_wake_word, rms_level


def test_split_message_markers():
    text = "Начало\n[IMAGE:C:/a.png]\nпосле\n[FILE:C:/d.pdf]\nГотово!"
    assert split_message_markers(text) == [
        ("text", "Начало"), ("IMAGE", "C:/a.png"), ("text", "после"), ("FILE", "C:/d.pdf"), ("text", "Готово!"),
    ]
    assert split_message_markers("просто текст") == [("text", "просто текст")]


def test_find_last_image():
    messages = [
        {"text_content": "[IMAGE:/old.png] первый"},
        {"text_content": "без картинки"},
        {"text_content": "вот [IMAGE:/new.png]"},
        {"text_content": "[FILE:/doc.pdf]"},
    ]
    assert find_last_image(messages) == "/new.png"
    assert find_last_image([{"text_content": "пусто"}]) is None


@pytest.mark.parametrize("text, expected", [
    ("я завёл кота Барсика", True),
    ("My sister lives in Berlin", True),
    ("какая погода завтра?", False),
    ("привет", False),
    ("расскажи про космос подробно", False),
])
def test_should_extract_facts(text, expected):
    assert should_extract_facts(text) is expected


def test_parse_facts_response():
    assert parse_facts_response('```json\n{"facts": ["У пользователя есть кот"]}\n```') == ["У пользователя есть кот"]
    assert parse_facts_response('{"facts": []}') == []
    assert parse_facts_response("not json") == []
    assert format_user_facts([{"fact": "Любит чай"}]).endswith("- Любит чай")


def test_prepare_text_for_speech():
    spoken = prepare_text_for_speech("## Привет!\n```py\nx=1\n```\n**Kez** тут [ссылка](http://a.b) [FILE:C:/x.pdf]")
    assert spoken == "Привет! Kez тут ссылка"


@pytest.mark.parametrize("transcript, command", [
    ("Эй, Kez, какая погода?", "какая погода?"),
    ("Кез, напомни через 5 минут", "напомни через 5 минут"),
    ("Hey Kez", ""),
    ("Кес!", ""),
    ("просто разговор на кухне", None),
    ("кезик мой", None),
])
def test_match_wake_word(transcript, command):
    assert match_wake_word(transcript) == command


def test_rms_level():
    silence = array.array("h", [0] * 100).tobytes()
    loud = array.array("h", [3000, -3000] * 50).tobytes()
    assert rms_level(silence) == 0
    assert rms_level(loud) == pytest.approx(3000)


def test_is_read_request():
    assert is_read_request("прочитай файл")
    assert is_read_request("открой файл pdf")
    assert not is_read_request("сохрани в файл")


def test_prepare_file_contents(tmp_path: Path):
    text_file = tmp_path / "notes.md"
    text_file.write_text("# Заметки", encoding="utf-8")
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")
    image_file = tmp_path / "pic.png"
    image_file.write_bytes(b"\x89PNG fake")
    unknown_file = tmp_path / "data.bin"
    unknown_file.write_bytes(b"\x00")

    parts, blocks, problems = prepare_file_contents([text_file, empty_file, image_file, unknown_file, tmp_path / "missing.txt"])
    assert len(parts) == 1
    assert blocks[0] == "=== notes.md ===\n# Заметки"
    assert "pic.png" in blocks[1]
    assert len(problems) == 3
