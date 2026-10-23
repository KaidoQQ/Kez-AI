from dataclasses import replace

from core import settings as settings_module
from core.constants.const import MODELS_FALLBACK


def test_preferred_model_goes_first_in_shared_list(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_module, "SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(settings_module, "SETTINGS_FILE", tmp_path / "settings.json")
    original = settings_module.settings
    try:
        target = settings_module.available_models()[-1]
        settings_module.save_settings(replace(original, preferred_model=target))
        # Список изменён на месте — его видят все модули, импортировавшие MODELS_FALLBACK
        assert MODELS_FALLBACK[0] == target
        assert sorted(MODELS_FALLBACK) == sorted(settings_module.available_models())

        loaded = settings_module.load_settings()
        assert loaded.preferred_model == target
    finally:
        settings_module.apply_settings(original)


def test_unknown_keys_are_ignored(monkeypatch, tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text('{"theme": "light", "something_old": 1}', encoding="utf-8")
    monkeypatch.setattr(settings_module, "SETTINGS_FILE", settings_file)
    loaded = settings_module.load_settings()
    assert loaded.theme == "light"
    assert loaded.tts_voice == "Puck"


def test_broken_file_falls_back_to_defaults(monkeypatch, tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text("{broken", encoding="utf-8")
    monkeypatch.setattr(settings_module, "SETTINGS_FILE", settings_file)
    assert settings_module.load_settings() == settings_module.KezSettings()
