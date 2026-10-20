import pytest

from app.backend.piplines.start.routing import classify_intent_by_rules, IntentType


@pytest.mark.parametrize("text, intent", [
    ("напомни через 10 минут проверить духовку", IntentType.REMINDER),
    ("поставь таймер на 5 минут", IntentType.REMINDER),
    ("мои напоминания", IntentType.REMINDER),
    ("remind me in 2 hours to call mom", IntentType.REMINDER),
    ("напомни завтра нарисовать открытку", IntentType.REMINDER),
    ("сделай этот рисунок в стиле аниме", IntentType.IMAGE_EDIT),
    ("перерисуй последнюю картинку в акварели", IntentType.IMAGE_EDIT),
    ("эту картинку сделай ночной", IntentType.IMAGE_EDIT),
    ("edit this image to be black and white", IntentType.IMAGE_EDIT),
    ("нарисуй кота в шляпе", IntentType.PHOTO),
    ("сохрани в pdf наш разговор", IntentType.FILE),
    ("сделай таблицу расходов в excel", IntentType.FILE),
    ("создай презентацию про птиц", IntentType.FILE),
    ("экспортируй это в word", IntentType.FILE),
    ("найди в интернете погоду", IntentType.WEB_SEARCH),
])
def test_rule_intents(text, intent):
    result = classify_intent_by_rules(text)
    assert result is not None
    assert result.intent == intent


def test_ambiguous_text_goes_to_llm():
    assert classify_intent_by_rules("что думаешь о философии стоиков в современном мире") is None


def test_photo_prompt_is_extracted():
    result = classify_intent_by_rules("нарисуй закат над морем")
    assert result.intent == IntentType.PHOTO
    assert "закат" in result.extracted_data["prompt"]
