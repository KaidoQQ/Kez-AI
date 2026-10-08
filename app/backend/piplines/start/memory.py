from core.loader import db

async def get_memory(user_text: str, chat_id: int) -> str:
    messages = db.get_chat_messages(chat_id)
    messages_latest = messages[:10]

    

