from datetime import datetime
from tech.basicDB import BaseDatabase
from core.logger import logger

class DataBase(BaseDatabase):
    async def create_tables(self) -> None:
        statements = (
            '''
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = now();
                RETURN NEW;
            END;
            $$ language 'plpgsql';
            ''',
            '''
            CREATE TABLE IF NOT EXISTS user_info(
                id SERIAL PRIMARY KEY,
                full_name TEXT DEFAULT '',
                birth BIGINT NOT NULL,
                interests TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''',
            '''
            CREATE TABLE IF NOT EXISTS history_chats(
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,    
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''',
            '''
            CREATE TABLE IF NOT EXISTS messages(
                id SERIAL PRIMARY KEY,
                chat_id INTEGER NOT NULL REFERENCES history_chats(id) ON DELETE CASCADE,
                sender_type VARCHAR(50) NOT NULL,
                text_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''',
            "CREATE INDEX IF NOT EXISTS idx_history_chats_id ON history_chats (id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages (chat_id)"
        )

        triggers = (
            '''
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_user_info_updated_at') THEN
                    CREATE TRIGGER update_user_info_updated_at
                    BEFORE UPDATE ON user_info
                    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
                END IF;
            END
            $$;
            ''',
            '''
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_history_chats_updated_at') THEN
                    CREATE TRIGGER update_history_chats_updated_at
                    BEFORE UPDATE ON history_chats
                    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
                END IF;
            END
            $$;
            '''
        )

        try:
            async with self.transaction() as connection:
                for stat in statements:
                    await connection.execute(stat)
                for trig in triggers:
                    await connection.execute(trig)
            logger.info("Database tables, functions, and triggers successfully initialized.")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    async def create_chat_with_first_message(self, title: str, first_message: str, sender: str = "user") -> int | None:
        """Пример использования транзакций для безопасного добавления связанных записей."""
        try:
            async with self.transaction() as connection:
                chat_id = await connection.fetchval(
                    "INSERT INTO history_chats (title) VALUES ($1) RETURNING id", 
                    title
                )
                await connection.execute(
                    "INSERT INTO messages (chat_id, sender_type, text_content) VALUES ($1, $2, $3)",
                    chat_id, sender, first_message
                )
                logger.info(f"Successfully created chat '{title}' with first message.")
                return chat_id
        except Exception as e:
            logger.error(f"Failed to create chat with first message: {e}")
            # Транзакция автоматически откатывается при ошибке
            return None

    async def get_all_chats(self) -> list[dict]:
        """Возвращает список всех чатов, отсортированных по дате обновления."""
        try:
            records = await self.fetchall("SELECT id, title, updated_at FROM history_chats ORDER BY updated_at DESC")
            return [dict(record) for record in records]
        except Exception as e:
            logger.error(f"Failed to fetch chats: {e}")
            return []

    async def get_chat_messages(self, chat_id: int) -> list[dict]:
        """Возвращает все сообщения конкретного чата."""
        try:
            records = await self.fetchall("SELECT id, sender_type, text_content, created_at FROM messages WHERE chat_id = $1 ORDER BY created_at ASC", chat_id)
            return [dict(record) for record in records]
        except Exception as e:
            logger.error(f"Failed to fetch messages for chat {chat_id}: {e}")
            return []

    async def add_message_to_chat(self, chat_id: int, sender: str, text_content: str) -> bool:
        """Добавляет новое сообщение в существующий чат."""
        try:
            await self.execute(
                "INSERT INTO messages (chat_id, sender_type, text_content) VALUES ($1, $2, $3)",
                chat_id, sender, text_content
            )
            logger.info(f"Message added to chat {chat_id} by {sender}")
            return True
        except Exception as e:
            logger.error(f"Failed to add message to chat {chat_id}: {e}")
            return False