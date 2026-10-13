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

    async def create_chat(self, title: str = "Новый чат") -> int | None:
        """Создает новый чат и возвращает его id."""
        try:
            chat_id = await self.fetchval(
                "INSERT INTO history_chats (title) VALUES ($1) RETURNING id",
                title
            )
            logger.info(f"Создан новый чат '{title}' с id={chat_id}")
            return chat_id
        except Exception as e:
            logger.error(f"Не удалось создать чат '{title}': {e}")
            return None

    async def get_or_create_default_chat(self) -> int:
        """Возвращает id последнего активного чата или создает первый по умолчанию."""
        try:
            record = await self.fetchone("SELECT id FROM history_chats ORDER BY updated_at DESC LIMIT 1")
            if record:
                return int(record["id"])

            new_id = await self.create_chat("Основной чат")
            return int(new_id) if new_id else 1
        except Exception as e:
            logger.error(f"Ошибка при получении/создании чата по умолчанию: {e}")
            return 1

    async def update_chat_title(self, chat_id: int, new_title: str) -> bool:
        """Обновляет заголовок чата."""
        try:
            await self.execute(
                "UPDATE history_chats SET title = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                new_title, chat_id
            )
            logger.info(f"Заголовок чата {chat_id} обновлен на '{new_title}'")
            return True
        except Exception as e:
            logger.error(f"Не удалось обновить заголовок чата {chat_id}: {e}")
            return False

    async def add_message_to_chat(self, chat_id: int, sender: str, text_content: str) -> bool:
        """Добавляет новое сообщение в существующий чат и обновляет updated_at чата."""
        try:
            async with self.transaction() as connection:
                await connection.execute(
                    "INSERT INTO messages (chat_id, sender_type, text_content) VALUES ($1, $2, $3)",
                    chat_id, sender, text_content
                )
                await connection.execute(
                    "UPDATE history_chats SET updated_at = CURRENT_TIMESTAMP WHERE id = $1",
                    chat_id
                )
            logger.info(f"Message added to chat {chat_id} by {sender}")
            return True
        except Exception as e:
            logger.error(f"Failed to add message to chat {chat_id}: {e}")
            return False

    async def delete_chat(self, chat_id: int) -> bool:
        """Удаляет чат и все связанные сообщения (каскадно) по chat_id."""
        try:
            async with self.transaction() as connection:
                await connection.execute("DELETE FROM history_chats WHERE id = $1", chat_id)
            logger.info(f"Чат ID={chat_id} успешно удален из базы данных.")
            return True
        except Exception as e:
            logger.error(f"Не удалось удалить чат ID={chat_id}: {e}")
            return False

    async def get_user_info(self) -> dict[str, str | int] | None:
        """Возвращает актуальную информацию о пользователе из user_info."""
        try:
            record = await self.fetchone(
                "SELECT id, full_name, birth, interests, updated_at FROM user_info ORDER BY id ASC LIMIT 1"
            )
            if record:
                return dict(record)
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении user_info из БД: {e}")
            return None

    async def is_onboarding_completed(self) -> bool:
        """Проверяет, заполнена ли информация о пользователе (завершен ли онбординг)."""
        try:
            info = await self.get_user_info()
            if not info:
                return False
            name: str = str(info.get("full_name", "")).strip()
            interests: str = str(info.get("interests", "")).strip()
            return bool(name and interests)
        except Exception as e:
            logger.error(f"Ошибка проверки завершения онбординга: {e}")
            return False

    async def save_or_update_user_info(self, full_name: str, birth: int, interests: str) -> bool:
        """Создает или обновляет запись информации о пользователе в user_info."""
        try:
            async with self.transaction() as connection:
                existing_id = await connection.fetchval("SELECT id FROM user_info ORDER BY id ASC LIMIT 1")
                if existing_id is not None:
                    await connection.execute(
                        """
                        UPDATE user_info
                        SET full_name = $1, birth = $2, interests = $3, updated_at = CURRENT_TIMESTAMP
                        WHERE id = $4
                        """,
                        full_name, birth, interests, existing_id
                    )
                    logger.info(f"Обновлена информация о пользователе id={existing_id}: {full_name}")
                else:
                    await connection.execute(
                        """
                        INSERT INTO user_info (full_name, birth, interests)
                        VALUES ($1, $2, $3)
                        """,
                        full_name, birth, interests
                    )
                    logger.info(f"Создана новая запись информации о пользователе: {full_name}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении user_info в БД: {e}")
            return False