<div align="center">

# 🐦 Kez AI — Intelligent Desktop Companion

<!-- Shield Badges -->
<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://riverbankcomputing.com/software/pyqt/"><img src="https://img.shields.io/badge/GUI-PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="PyQt6"></a>
  <a href="https://ai.google.dev/"><img src="https://img.shields.io/badge/AI-Google%20Gemini-8E75C2?style=for-the-badge&logo=google&logoColor=white" alt="Google Gemini"></a>
  <a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/Database-PostgreSQL%2016-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Container-Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"></a>
  <a href="./LICENSE.txt"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="MIT License"></a>
</p>

<p align="center">
  <b>A lively, charming, and context-aware avian AI companion living directly on your desktop.</b><br>
  <i>"Chirik-chirik! Less rigid corporate jargon, more sincere friendship, witty dialogue, and real assistance."</i>
</p>

<p align="center">
  <a href="#-overview">Overview</a> •
  <a href="#-key-features">Key Features</a> •
  <a href="#%EF%B8%8F-system-architecture">System Architecture</a> •
  <a href="#%EF%B8%8F-technology-stack">Tech Stack</a> •
  <a href="#-project-structure">Project Structure</a> •
  <a href="#-getting-started">Getting Started</a> •
  <a href="#%EF%B8%8F-configuration-env">Configuration</a> •
  <a href="#-roadmap">Roadmap</a>
</p>

---

</div>

## 🌟 Overview

**Kez AI** is not just another robotic chat window. It is an interactive, animated desktop companion imbued with a vibrant bird personality. Kez strikes the sweet spot between intelligent reasoning and friendly camaraderie — greeting you warmly, recalling details from your past conversations, and smoothly transitioning between states.

### 🎯 Why Kez AI?
- 💬 **Human & Feathered Persona**: Warm, empathetic conversational tone with lighthearted avian humor.
- ⚡ **Zero-Latency Instant Responses**: Recognizes greetings, check-ins, and gratitude locally with 0 ms latency without hitting external APIs.
- 🧠 **Smart Context Window**: Silently digests previous conversation turns (up to 10 messages) to maintain deep conversational flow.
- 🎬 **Living Animated Visuals**: Powered by QtMultimedia video loops reflecting idle and thinking/searching states in real-time.
- 🛡️ **Fault-Tolerant AI Engine**: Resilient Google Gemini fallback model chain ensuring zero downtime.
- 🐘 **Enterprise-Grade Async Storage**: Backed by PostgreSQL with `asyncpg` connection pooling, cascading relations, and automated timestamp triggers.

---

## ✨ Key Features

<table>
  <tr>
    <td width="50%">
      <h3>🧠 Conversational Memory & Bio</h3>
      <ul>
        <li><b>Sliding Context Window:</b> Reconstructs dynamic context across the last 10 messages to seamlessly resume conversations after breaks.</li>
        <li><b>Zero Meta-Talking:</b> Never outputs dry phrases like <i>"Based on the last 10 messages..."</i>; speaks naturally and authentically.</li>
        <li><b>User Profile Storage:</b> Tracks personal facts, interests, and bio data in the <code>user_info</code> table for enduring long-term memory.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>⚡ Two-Tier Intent Routing</h3>
      <ul>
        <li><b>Tier 1 (Instant Rules):</b> High-speed regex matching for common phrases (greetings, mood checks, identity) with 0 ms response.</li>
        <li><b>Tier 2 (LLM Classifier):</b> Gemini-powered structured JSON intent classification for nuanced, complex requests:
          <code>chat</code> | <code>web_search</code> | <code>photo</code> | <code>file</code>.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>🐣 Interactive Onboarding Flow</h3>
      <ul>
        <li><b>"Get to know Kez":</b> Friendly conversational wizard welcoming new users and learning their name, birth year, and hobbies.</li>
        <li><b>LLM Information Extraction:</b> Validates inputs using Gemini JSON filters, sanitizes personal facts, and stores them in PostgreSQL.</li>
        <li><b>Adaptive Placeholders:</b> Contextual prompt hints guiding users step-by-step through setup.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🔍 Cascading Web Search Engine</h3>
      <ul>
        <li><b>Query Sanitization:</b> Automated noise removal, injection prevention, and keyword extraction.</li>
        <li><b>3-Tier Scraper Cascade:</b> DuckDuckGo search ➔ <code>httpx</code> ➔ <code>curl_cffi</code> (anti-bot bypass) ➔ <code>Playwright</code> headless browser ➔ snippet fallback.</li>
        <li><b>Clean Content Extraction:</b> Structured text extraction via <code>trafilatura</code> with 5-minute TTLCache and citation links.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>🎨 Modern Desktop Experience</h3>
      <ul>
        <li><b>Animated Video Companion:</b> Seamless video playback for idle states (<code>anim 1.mp4</code>) and active search states (<code>anim search 2.mp4</code>).</li>
        <li><b>Sleek QSS Dark Theme:</b> Polished glass-styled UI, rounded message bubbles, responsive input field.</li>
        <li><b>Collapsible Sidebar:</b> Fast switching between multiple chat sessions with right-click context menu (Rename, Delete) and Gemini-style lazy session creation.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🛡️ Resilience & Performance</h3>
      <ul>
        <li><b>Model Fallback Chain:</b> Automatically cascades through Gemini endpoints (<code>2.5-flash</code> ➔ <code>3.5-flash</code> ➔ <code>2.5-flash-lite</code> ➔ <code>3.1-flash-lite</code> ➔ <code>2.0-flash</code>).</li>
        <li><b>Non-Blocking GUI:</b> Powered by <code>qasync</code>, binding PyQt6's event loop directly with Python's native <code>asyncio</code>.</li>
        <li><b>Dual Logging:</b> Colored console outputs alongside structured <code>.jsonl</code> logs and audit trails.</li>
      </ul>
    </td>
  </tr>
</table>

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    User([👤 User]) -->|Inputs message / clicks Meet Kez| UI[🖥️ PyQt6 GUI / MainWindow]
    UI -->|qasync EventLoop| CoreDispatch{Dispatch Mode}

    subgraph OnboardingArea [" 🐣 Onboarding Flow "]
        CoreDispatch -->|Onboarding Active / Button Clicked| OnboardingPipe[🐣 OnboardingManager]
        OnboardingPipe -->|Step Validation: Name / Age / Interests| ValLLM[🧠 Gemini Extraction & Validation]
        ValLLM -->|Save User Profile| DB[(🐘 PostgreSQL Database)]
        OnboardingPipe -->|Step Prompts & Welcome| UI
    end

    subgraph AgentArea [" 🤖 KezAgent Orchestrator "]
        CoreDispatch -->|Standard Chat Message| Agent[🤖 KezAgent]
        Agent --> Router{⚡ Dual-Tier Router<br/>route_intent}
        Router -->|Regex & Quick Rules| Instant[⚡ Instant Reply 0ms]
        Router -->|Ambiguous Request| LLMRouter[🧠 LLM Intent Classifier]
    end

    Instant -->|Direct Feathered Reply| UI

    subgraph PipelineArea [" 🚀 Execution Pipelines "]
        LLMRouter -->|Intent: CHAT| MemPipe[🧠 Memory Pipeline<br/>get_memory]
        LLMRouter -->|Intent: WEB_SEARCH| SearchPipe[🔎 Web Search Pipeline<br/>web_search]
        LLMRouter -->|Intent: PHOTO| PhotoPipe[🎨 Photo Generation Pipeline]
        LLMRouter -->|Intent: FILE| FilePipe[📁 File Processing Pipeline]
    end

    subgraph SearchDetails [" 🔍 3-Tier Cascading Web Search "]
        SearchPipe -->|1. Sanitize & Keywords| DDG[🦆 DuckDuckGo Search]
        DDG -->|2. Parallel Scrape Top-3| Cascade{Cascade Fallback}
        Cascade -->|Tier 1| Httpx[⚡ httpx]
        Cascade -->|Tier 2| Curl[🛡️ curl_cffi]
        Cascade -->|Tier 3| Pw[🎭 Playwright Headless]
        Cascade -->|Fallback| Snippet[📄 DDG Snippet]
        Cascade -->|3. Clean Text| Traf[🧹 trafilatura]
        Traf -->|4. TTL Cache 5m| Cache[(⚡ TTLCache)]
    end

    subgraph DataArea [" 🗄️ Storage & Model Services "]
        MemPipe <-->|Fetch Last 10 Messages + user_info| DB
        SearchPipe <-->|Fetch user_info Profile| DB
        MemPipe -->|Prompt + Fallback Chain| Gemini[✨ Google Gemini API]
        SearchPipe -->|Web Context + Fallback Chain| Gemini
        Gemini -->|Save Message| DB
    end

    Gemini -->|In-Character Reply| UI
    SearchPipe -.->|Trigger Search Animation| UI
    DB -.->|Sidebar Chat Sessions & History| UI
```

---

## 🛠️ Technology Stack

| Layer | Technology | Details |
|---|---|---|
| **Language** | 🐍 **Python 3.10+** | Modern asynchronous Python with strict typing |
| **GUI Framework** | 🖼️ **PyQt6** & **QtMultimedia** | High-DPI desktop interface, QSS stylesheets, video rendering |
| **Async Engine** | ⚡ **qasync** & **asyncio** | Concurrent execution bridging Qt event loop and async tasks |
| **AI / LLM** | ✨ **Google Gemini API** (`google-genai`) | Multimodal LLMs with fallback resilience pipeline |
| **Web Search & Scraping** | 🔍 **DuckDuckGo, httpx, curl_cffi, Playwright, trafilatura** | Cascading web retrieval with Cloudflare bypass & text extraction |
| **Database** | 🐘 **PostgreSQL 16** | Relational chat histories, user facts, indexes & triggers |
| **DB Drivers** | 🔌 **asyncpg** & **psycopg2** | High-performance asynchronous connection pooling & transactions |
| **Logging** | 📋 **Custom Logging Core** | Terminal output, plain-text logs (`.log`), and JSONL audit files |
| **DevOps** | 🐳 **Docker & Docker Compose** | One-command isolated PostgreSQL and application containerization |

---

## 📂 Project Structure

```text
kez-ai/
├── 📁 Kez/                      # Core AI Agent & Prompt Engineering
│   ├── kez.py                  # KezAgent orchestrator & session manager
│   ├── prepare.py              # Gemini client initialization & prompt loader
│   └── 📁 prompts/             # System prompt specifications
│       ├── routing.txt         # JSON intent classification prompt
│       ├── memory.txt          # 10-message conversational memory prompt
│       ├── web_search.txt      # Web synthesis prompt with source citations
│       └── lg.protect.txt      # Safety guardrails and persona constraints
├── 📁 app/
│   ├── 📁 backend/             # Server & pipeline infrastructure
│   │   ├── 📁 piplines/start/  # Core request pipelines
│   │   │   ├── routing.py      # Dual-tier intent router (Rules + Gemini)
│   │   │   ├── memory.py       # Context assembly & conversation history (10 msgs + user_info)
│   │   │   ├── onboarding.py   # Interactive multi-step onboarding & profile extractor
│   │   │   └── web_search.py   # Cascading search pipeline (DDG + httpx/curl/Playwright + trafilatura)
│   │   └── 📁 utils/           # Shared helper modules
│   │       ├── llm_fallback.py # Gemini fallback chain handler
│   │       └── text_cleaner.py # Search query sanitization & keywords extraction
│   └── 📁 frontend/            # PyQt6 Graphical Interface
│       ├── 📁 components/      # Modular UI widgets
│       │   ├── chat_area.py    # Scrollable chat bubbles & typing indicator
│       │   ├── input_bar.py    # Interactive input controls & action buttons (Meet Kez, Send)
│       │   ├── sidebar.py      # Slide-out chat history drawer with context menu
│       │   └── video_companion.py # Seamless animated video player (idle & search loops)
│       ├── 📁 assets/          # Application media (MP4 animations, icons)
│       ├── main_window.py      # Main application window setup & orchestrator
│       └── style.qss           # Modern dark-mode QSS stylesheet
├── 📁 core/                    # System utilities & loaders
│   ├── const.py                # Regular expressions, fallback models & templates
│   ├── loader.py               # Database and environment initialization
│   └── logger.py               # Structured console & JSONL logger
├── 📁 tech/                    # Database abstraction layer
│   ├── basicDB.py              # Asyncpg connection pool wrapper
│   └── database.py             # Schema definitions, migrations, and CRUD
├── 📁 logs/                    # Application and audit logs (.log / .jsonl)
├── docker-compose.yml          # Container configuration for PostgreSQL 16
├── Dockerfile                  # Application Docker container build file
├── requirements.txt            # Python dependencies
└── main.py                     # Application bootstrap and entry point
```

---

## 🚀 Getting Started

### 📋 Prerequisites
- **Python**: Version `3.10` or higher
- **PostgreSQL**: Version `14+` (or Docker installed)
- **Google Gemini API Key**: [Get your key from Google AI Studio](https://aistudio.google.com/)

---

### 📥 Installation Steps

#### 1. Clone the repository
```bash
git clone https://github.com/yourusername/kez-ai.git
cd kez-ai
```

#### 2. Create and activate a virtual environment
```bash
# On Windows:
python -m venv venv
venv\Scripts\activate

# On macOS / Linux:
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install dependencies
```bash
pip install -r requirements.txt
```

#### 4. Launch PostgreSQL via Docker (Recommended)
You can launch an isolated, pre-configured PostgreSQL 16 database with persistent storage:
```bash
docker-compose up -d db
```

---

## ⚙️ Configuration (.env)

Create a `.env` file in the root directory:

```env
# 🔑 Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# 🐘 PostgreSQL Configuration
POSTGRES_DB=kez_db
POSTGRES_USER=kez_user
POSTGRES_PASSWORD=kez_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# 🔗 Full Connection DSN
DATABASE_URL=postgresql://kez_user:kez_password@localhost:5432/kez_db
```

> [!NOTE]
> Database tables (`history_chats`, `messages`, `user_info`), procedures, and indexes are **automatically verified and created** on first launch!

---

## 💻 Running the Application

Once your `.env` file is ready and PostgreSQL is up:

```bash
python main.py
```

### 🎬 What happens at launch:
1. `main.py` starts the `qasync` event loop.
2. The database connection pool is established and tables are verified.
3. The dark-themed GUI appears with Kez playing the idle animation.
4. You can start chatting immediately!

---

## 🗺️ Roadmap

- [x] ⚡ Fully asynchronous core with `PyQt6` + `qasync`.
- [x] 🎬 Smooth looping video companion for idle and thinking states.
- [x] 🐘 PostgreSQL relational history with cascading chat deletions.
- [x] 🐣 Interactive user onboarding flow ("Get to know Kez") with user bio extraction.
- [x] 🔀 Two-tier intent router (Instant regex + LLM classifier).
- [x] 🧠 10-message conversational memory prompt maintaining the bird persona.
- [x] 🛡️ Multi-model fallback resilience (`gemini-2.5-flash` down to `2.0-flash`).
- [x] 🔍 Web search pipeline integration (DuckDuckGo + 3-tier cascade httpx/curl_cffi/Playwright).
- [ ] 🎨 Text-to-Image generation pipeline (Google Imagen / Fal.ai).
- [ ] 📁 File analyzer and document exporter (PDF, Markdown, TXT).
- [ ] 🎙️ Voice synthesis & speech recognition (TTS / STT integration).

---

## 🤝 Contributing

Contributions are warmly welcome! If you'd like to help Kez grow:
1. **Fork** the repository.
2. Create your feature branch (`git checkout -b feature/amazing-feather`).
3. Commit your changes (`git commit -m 'feat: add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feather`).
5. Open a **Pull Request**.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE.txt`](./LICENSE.txt) for more details.

<div align="center">
  <sub>Crafted with feathers & care 🐦 Kez AI Team</sub>
</div>
