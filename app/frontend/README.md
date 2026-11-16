# Native chat interface

The desktop UI follows the visual approach of [assistant-ui](https://github.com/assistant-ui/assistant-ui): a restrained sidebar, spacious conversation, rounded composer, starter suggestions and message actions. This is an original PyQt6 implementation, not an embedded React application or an integration of the assistant-ui package. Existing Python services and chat persistence remain in place.

- Dark and light themes cover chat, settings, menus, attachments and the companion window.
- Enter sends a message; Shift+Enter adds a newline. Clipboard images/files and drag-and-drop remain supported.
- Starter suggestions populate a draft without sending it.
- Copy actions preserve the original message text, including Markdown, during streaming.
- The animated companion lives below the chat history; pet mode is still available in the header.
- Russian and English labels update when the language changes.

Validation: `python -m pytest --ignore=tests/test_database.py` runs the offline suite, including the composer, attachment-only submission, streaming/copy, clearing and localization regressions. The database suite requires a separate test PostgreSQL database through `DATABASE_URL`. API calls and microphone recording require a configured runtime and are not exercised by the offline suite.
