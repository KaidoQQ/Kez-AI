 # 🤖 Kez AI - Your Intelligent Desktop Companion

   ![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
   ![PyQt6](https://img.shields.io/badge/PyQt6-Framework-green.svg)
   ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue.svg)
   ![Status](https://img.shields.io/badge/Status-In%20Development-orange.svg)

   **Kez AI** is a smart, interactive desktop AI companion designed to communicate with you like a real friend. It
  strikes the perfect balance—avoiding overly complex jargon while providing thoughtful, detailed, and engaging
  responses.

   ---

   ## ✨ Key Features

   ### 🧠 Advanced Memory & Context
    - **Personalized Interaction**: Kez remembers your name, age, hobbies, and key biographical facts.
    - **Friendly Dialogue**: Leverages extracted user facts to build long-term context and a natural, personalized
  conversational experience.
    - **Smart Web Search**: Integrates with DuckDuckGo / Google API to search the web, answer your questions, and
  help you achieve your goals in real-time.

   ### 🎨 Modern Interface & Design
    Built with a focus on modern, fresh aesthetics (Modern UI):
    - **Animated Companion**: Features an animated visual representation of the AI. Includes smooth transitions
  between idle states (`Анимация 1.mp4`) and active search states (`Анимация поиска 2.mp4`).
    - **Modern Chat UI**: Enjoy comfortable message bubbles, smooth scrolling, and an elegant input field.
    - **Interactive Sidebar**: A sleek, slide-out chat history panel on the left allows you to effortlessly switch
  between past conversations while keeping the main interface clean.

    ---

    ## 🛠️ Technology Stack

    - **Frontend**: Python + `PyQt6`
      - *Utilizes modern QSS stylesheets and `QPropertyAnimation` for fluid, dynamic interface animations.*
    - **Backend**: Python
      - *Custom implementation handling AI logic, LLM integration, database management, and web search capabilities.*
    - **Database**: PostgreSQL
      - *Securely stores chat histories and extracted user memory/facts.*

    ---

    ## 📂 Project Structure

    ```text
    kez-ai/
    ├── anim/                  # Video files for character animations
    ├── app/
    │   ├── frontend/          # UI source code (windows, widgets, video player, animations)
    │   └── backend/           # Core AI logic, memory management, and search integration
    ├── core/                  # Core utilities (logging, environment variables)
    ├── logs/                  # Application execution logs (plain text & JSONL for analytics)
    ├── main.py                # Application entry point
    ├── requirements.txt       # Python dependencies
    └── README.md              # Project documentation
  ──────
  ## 🚀 Getting Started

  ### Prerequisites

  • Python 3.10 or higher
  • PostgreSQL Server

  ### Installation

  1. Clone the repository:
    git clone https://github.com/yourusername/kez-ai.git
    cd kez-ai

  2. Install dependencies:
    pip install -r requirements.txt

  3. Configure Environment:
      • Create a .env file based on .env.example
      • Add your database credentials and API keys.
  4. Run the Application:
    python main.py

  ──────
  ## 🤝 Contributing

  Contributions, issues, and feature requests are welcome! Feel free to check the issues page
  https://github.com/yourusername/kez-ai/issues.

  ## 📄 License

  This project is licensed under the MIT License /LICENSE.
