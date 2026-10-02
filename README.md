# Kez AI - Desktop AI Companion

## About the Project
**Kez AI** is an intelligent desktop AI companion application. The neural network communicates with the user like a real friend: it doesn't overload you with complex terms, but it doesn't give overly simple answers either.

The main feature of the companion is its **memory and context**:
- It remembers the user's name, age, hobbies, and key biographical facts.
- It uses this data to build a personalized and friendly dialogue.
- It can search the internet (DuckDuckGo / Google API) to help the user achieve their goals and answer questions.

## Interface and Design
The application is being developed with a focus on modern, fresh, and beautiful design (Modern UI):
- **Animated Character**: The screen displays a visual representation of the companion. In standby mode, it smoothly plays the idle animation (`Анимация 1.mp4`). When searching for information, the companion switches to the activity animation (`Анимация поиска 2.mp4`).
- **Modern Chat**: Convenient message bubbles, smooth scrolling, and a beautiful input field.
- **Chat History (Sidebar)**: A slide-out panel on the left that allows you to switch between past conversations. The panel smoothly opens and hides on click, keeping the main interface clean.

## Technology Stack
- **Frontend**: Python + `PyQt6` (using modern stylesheets and `QPropertyAnimation` for fluid interface animations).
- **Backend**: Python (custom implementation of AI logic, LLM, database management, and web search).
- **Database**: PostgreSQL (for storing chat history and extracted user facts).

## Project Structure
- `app/frontend/` — source code for the interface (windows, widgets, video player, animations).
- `app/backend/` — source code for the neural network logic, memory management, and search integration.
- `anim/` — video files for the character animations.
- `core/` — core utilities (logging, environment loading).
- `logs/` — application execution logs (plain text and JSONL for analytics).

## How to Run
*(To be updated as the project nears completion)*
