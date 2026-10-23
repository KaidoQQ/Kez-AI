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
  <a href="https://github.com/KaidoQQ/Kez-AI/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/KaidoQQ/Kez-AI/tests.yml?branch=master&style=for-the-badge&label=Tests" alt="Tests"></a>
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
- 📁 **Reads & Writes Files**: Drop, paste or attach up to 5 files (PDFs, documents, images, audio) — or ask Kez to export a polished PDF / Word / Excel / PowerPoint / Markdown / TXT document.
- 🎙️ **Talk Out Loud**: Say "Эй, Kez", send voice messages and hear Kez answer back sentence-by-sentence while it is still thinking.
- 🧠 **Remembers You**: Kez quietly learns durable facts about you from conversations ("you have a cat named Barsik") and uses them for months.
- ⏰ **Reminders & Timers**: "Напомни через 20 минут…" — with tray notifications, a message in the chat and an excited Kez animation.
- 🐤 **Desktop Pet Mode**: Shrink Kez into a tiny always-on-top window in the corner of your screen with a speech bubble and a mini input.
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
  <tr>
    <td width="50%">
      <h3>⚡ Real-Time Streaming Pipeline</h3>
      <ul>
        <li><b>Instant Token Streaming:</b> Uses <code>generate_content_stream</code> so user sees Kez "typing" letter-by-letter / word-by-word without 5-10s waiting.</li>
        <li><b>Auto-Resizing Bubbles:</b> Real-time dynamic document reflow and height adaptation with smooth bottom autoscroll.</li>
        <li><b>Fallback Resilient:</b> Automatic cascade over backup models if streaming connection drops.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🎨 Visual Image Generation & Cache</h3>
      <ul>
        <li><b>Google Imagen 3:</b> Photorealistic & artistic image synthesis via <code>imagen-3.0-generate-002</code> / <code>imagen-3.0-fast</code>.</li>
        <li><b>Prompt Enhancement:</b> Automatically enriches raw user prompts into professional English photographic prompts.</li>
        <li><b>Front-End Cache & Auto-Cleanup:</b> Images stored in <code>app/frontend/cache/images/</code> with an automated 7-day TTL cleanup at launch.</li>
        <li><b>Interactive Card Actions:</b> Right-click context menu allows user to <b>Скопировать</b> (Copy to Clipboard) or <b>Скачать...</b> (Save As to any folder).</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>📁 File Analyzer & Document Exporter</h3>
      <ul>
        <li><b>Attach Any File:</b> Paperclip button attaches text/code, <code>.docx</code>, PDF, images or audio; Kez streams an analysis or answers your question about it.</li>
        <li><b>Native Multimodal Input:</b> PDF, images and audio go to Gemini as raw bytes; text files and <code>.docx</code> are parsed locally (no extra dependencies).</li>
        <li><b>Export to PDF / Markdown / TXT:</b> "Сохрани в pdf", "сделай отчёт в txt" — Kez writes a clean document from the request and recent chat, saves it to <code>~/Documents/Kez AI</code> and shows a file card (Open / Folder / Save As).</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🎙️ Voice: Speech Recognition & Synthesis</h3>
      <ul>
        <li><b>Voice Messages (STT):</b> Microphone button records via <code>QtMultimedia</code>; speech is transcribed by Gemini with the fallback model chain.</li>
        <li><b>Spoken Replies (TTS):</b> Replies to voice messages are voiced by Gemini TTS (<code>gemini-2.5-flash-preview-tts</code>, voice "Puck"); code and links are skipped.</li>
        <li><b>Auto-Cleanup:</b> Audio is cached in <code>app/frontend/cache/audio/</code> with the same 7-day TTL.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>👂 Hands-Free "Эй, Kez" & Streaming Speech</h3>
      <ul>
        <li><b>Wake Word:</b> A local voice-activity detector (<code>QAudioSource</code> + RMS level) cuts out phrases; only speech — never silence — is sent to Gemini, and Kez reacts only to phrases starting with "Kez" / "Эй, Kez".</li>
        <li><b>Sentence-by-Sentence TTS:</b> <code>SpeechQueue</code> synthesizes finished sentences in parallel while the reply is still streaming and plays them strictly in order.</li>
        <li><b>No Self-Listening:</b> The listener pauses while Kez speaks, records or processes a message.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🧠 Long-Term Memory</h3>
      <ul>
        <li><b>Automatic Fact Extraction:</b> When you talk about yourself, a background Gemini call extracts new durable facts (pets, job, hobbies, goals) without slowing the reply.</li>
        <li><b>Cheap Pre-Filter:</b> Questions and small talk never reach the LLM — only messages that look like self-disclosure.</li>
        <li><b>Under Your Control:</b> Facts live in the <code>user_facts</code> table, are injected into the memory prompt, and can be reviewed or forgotten in <b>Settings → Память</b>.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>⏰ Reminders, Timers & Tray</h3>
      <ul>
        <li><b>Natural Language Time:</b> "через 10 минут", "на полчаса", "завтра в 9:30" are parsed locally in 0 ms; tricky ones ("в пятницу вечером") go to Gemini.</li>
        <li><b>Reliable Delivery:</b> Reminders are stored in PostgreSQL and checked every 15 s — missed ones fire right after launch.</li>
        <li><b>System Tray:</b> Notifications, "Open Kez", "Pet mode" and "Quit" in the tray menu; "мои напоминания" lists what is pending.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🐤 Desktop Pet Mode</h3>
      <ul>
        <li><b>Always on Top:</b> The 🐤 button turns Kez into a small frameless window in the corner of the screen — drag it anywhere.</li>
        <li><b>Speech Bubble & Mini Input:</b> Ask quick questions right from the pet; answers, reminders and "Эй, Kez" replies appear in a bubble.</li>
        <li><b>One Click Back:</b> ⤢ button, double-click or the tray icon restores the full window.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>🖌️ Image Editing</h3>
      <ul>
        <li><b>Edit What You See:</b> "Сделай этот рисунок в стиле аниме", "добавь шляпу на последнюю картинку" — Kez takes the last image in the chat and redraws it with Gemini image models.</li>
        <li><b>Your Own Pictures Too:</b> Attach or paste an image with an edit request; a "describe this picture" request is still treated as analysis.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>📊 Office Export & Drag-and-Drop</h3>
      <ul>
        <li><b>Word / Excel / PowerPoint:</b> <code>.docx</code> with headings, lists and tables; <code>.xlsx</code> with one sheet per table and real numbers; <code>.pptx</code> with a slide per section.</li>
        <li><b>Attach Any Way:</b> Drag files onto the window, <code>Ctrl+V</code> a screenshot or copied files, or pick several files in the dialog — up to 5 per message.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>⚙️ Settings Panel</h3>
      <ul>
        <li><b>Общие:</b> dark / light theme, preferred Gemini model (moved to the top of the fallback chain), export folder.</li>
        <li><b>Голос:</b> 8 TTS voices, auto-speak all replies, streaming speech, "Эй, Kez" with adjustable sensitivity.</li>
        <li><b>Память:</b> toggle fact learning, review and forget remembered facts. Stored in <code>~/.kez_ai/settings.json</code>.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🔎 Search Across All Chats</h3>
      <ul>
        <li><b>Full-Text Search:</b> PostgreSQL <code>to_tsvector</code> with a GIN index plus <code>ILIKE</code> for partial words.</li>
        <li><b>Right in the Sidebar:</b> Results show the chat title and a snippet around the match; click to open the chat.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td colspan="2">
      <h3>🌍 Russian & English (i18n)</h3>
      <ul>
        <li><b>First-Run Choice:</b> On the very first launch Kez asks for the language (pre-selected from the system locale); it can be changed any time in <b>Settings → General</b> — the interface switches instantly, no restart.</li>
        <li><b>Locale Files:</b> All UI texts and Kez's fixed replies live in <code>core/locales/ru.json</code> / <code>en.json</code> and are read via <code>tr("key")</code> with a fallback to Russian.</li>
        <li><b>Language-Aware AI:</b> Prompts get the default language through a <code>{DEFAULT_LANGUAGE}</code> placeholder, while Kez still answers in the language you actually write in; instant greetings reply in the language of your message.</li>
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
        LLMRouter -->|Intent: FILE| FilePipe[📁 File Export Pipeline<br/>PDF / DOCX / XLSX / PPTX / MD / TXT]
        LLMRouter -->|Intent: REMINDER| ReminderPipe[⏰ Reminder Pipeline]
        LLMRouter -->|Intent: IMAGE_EDIT| EditPipe[🖌️ Image Edit Pipeline]
        CoreDispatch -->|Attached / Dropped / Pasted Files| AnalyzePipe[📎 File Analysis Pipeline]
        UI -->|🎙️ Voice Recording / 👂 Эй, Kez| STT[🗣️ Gemini Speech-to-Text]
        STT -->|Transcribed Text| CoreDispatch
        Agent -.->|Background| FactsPipe[🧠 Fact Extraction]
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
        MemPipe <-->|Fetch Last 10 Messages + user_info + user_facts| DB
        FactsPipe -->|New Facts| DB
        ReminderPipe -->|Save| DB
        DB -.->|Due Reminders every 15s| Tray[🔔 Tray Notification + Pet Bubble]
        SearchPipe <-->|Fetch user_info Profile| DB
        MemPipe -->|Prompt + Fallback Chain| Gemini[✨ Google Gemini API]
        SearchPipe -->|Web Context + Fallback Chain| Gemini
        Gemini -->|Save Message| DB
    end

    Gemini -->|In-Character Reply| UI
    AnalyzePipe -->|Text / native PDF, image, audio| Gemini
    FilePipe -->|Generate Markdown + Save File| Gemini
    EditPipe -->|Image + Instruction| Gemini
    UI -.->|Sentence-by-Sentence Speech| TTS[🔊 Gemini TTS SpeechQueue]
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
| **AI / LLM & Streaming** | ✨ **Google Gemini API** (`google-genai`) | Multimodal LLMs with fallback resilience pipeline & token streaming |
| **Image Generation** | 🎨 **Google Gemini Image & Pollinations AI** | Multi-tier pipeline with LLM prompt engineering and unlimited free fallback |
| **File Analysis & Export** | 📁 **Gemini multimodal input, QPdfWriter, python-docx, openpyxl, python-pptx** | Native PDF/image/audio understanding, `.docx` parsing, PDF/DOCX/XLSX/PPTX/MD/TXT export |
| **Voice (STT / TTS)** | 🎙️ **QtMultimedia, QAudioSource, Gemini TTS** | Push-to-talk & wake-word capture with local VAD, Gemini transcription, streaming `gemini-2.5-flash-preview-tts` speech |
| **Desktop Integration** | 🐤 **QSystemTrayIcon, frameless always-on-top window** | Tray notifications for reminders, desktop pet mode, drag & drop, clipboard paste |
| **Testing** | 🧪 **pytest** | Offscreen Qt tests for routing, exporters, reminders, memory, voice helpers and settings |
| **Web Search & Scraping** | 🔍 **DuckDuckGo, httpx, curl_cffi, Playwright, trafilatura** | Cascading web retrieval with Cloudflare bypass & text extraction |
| **Database** | 🐘 **PostgreSQL 16** | Chat histories, user facts, reminders, full-text GIN index & triggers |
| **DB Drivers** | 🔌 **asyncpg** & **psycopg2** | High-performance asynchronous connection pooling & transactions |
| **Logging** | 📋 **Custom Logging Core** | Terminal output, plain-text logs (`.log`), and JSONL audit files |
| **DevOps** | 🐳 **Docker & Docker Compose** | One-command isolated PostgreSQL and application containerization |

---

## 📂 Project Structure

```text
kez-ai/
├── 📁 Kez/                      # Core AI Agent & Prompt Engineering
│   ├── kez.py                  # KezAgent orchestrator & streaming session manager
│   ├── prepare.py              # Gemini client initialization & prompt loader
│   └── 📁 prompts/             # System prompt specifications
│       ├── routing.txt         # JSON intent classification prompt
│       ├── memory.txt          # 10-message conversational memory prompt
│       ├── web_search.txt      # Web synthesis prompt with source citations
│       ├── image_generation.txt # English enhancement prompt for Imagen 3
│       ├── file_analysis.txt   # Attached file analysis prompt
│       ├── file_export.txt     # Markdown document writer for exports (format-aware)
│       ├── fact_extraction.txt # Long-term memory: durable user facts as JSON
│       ├── reminder_parse.txt  # Complex reminder times -> ISO date-time
│       └── lg.protect.txt      # Safety guardrails and persona constraints
├── 📁 app/
│   ├── 📁 backend/             # Server & pipeline infrastructure
│   │   ├── 📁 piplines/start/  # Core request pipelines
│   │   │   ├── routing.py      # Dual-tier intent router (Rules + Gemini)
│   │   │   ├── memory.py       # Context assembly & streaming memory (10 msgs + user_info)
│   │   │   ├── image_gen.py    # Image generation & editing pipeline (Gemini / Imagen / Pollinations)
│   │   │   ├── onboarding.py   # Interactive multi-step onboarding & profile extractor
│   │   │   ├── file_processing.py # Multi-file analysis (streaming) & document export
│   │   │   ├── facts.py        # Background long-term memory (user fact extraction)
│   │   │   ├── reminders.py    # Reminder/timer parsing (local rules + LLM) & storage
│   │   │   ├── voice.py        # Gemini speech-to-text & text-to-speech
│   │   │   └── web_search.py   # Cascading search pipeline (DDG + httpx/curl/Playwright + trafilatura)
│   │   └── 📁 utils/           # Shared helper modules
│   │       ├── llm_fallback.py # Gemini fallback chain handler & stream generator
│   │       ├── image_cache.py  # Cache manager with 7-day TTL cleanup (images & audio)
│   │       ├── file_tools.py   # Text/.docx extraction & PDF/DOCX/XLSX/PPTX/MD/TXT writers
│   │       ├── markers.py      # [IMAGE:] / [FILE:] message marker parsing
│   │       └── text_cleaner.py # Search query sanitization & keywords extraction
│   └── 📁 frontend/            # PyQt6 Graphical Interface
│       ├── 📁 components/      # Modular UI widgets
│       │   ├── chat_area.py    # Scrollable chat bubbles & real-time streaming
│       │   ├── chat_image_widget.py # Interactive photo card (Copy / Download)
│       │   ├── chat_file_widget.py  # Exported document card (Open / Folder / Save As)
│       │   ├── input_bar.py    # Input controls: multi-attachments, Ctrl+V paste, voice recording
│       │   ├── sidebar.py      # Chat history drawer with context menu & full-text search
│       │   ├── settings_dialog.py # Settings panel (General / Voice / Memory)
│       │   ├── language_dialog.py # First-run language choice (RU / EN)
│       │   ├── pet_window.py   # Always-on-top desktop pet with speech bubble
│       │   ├── speech_queue.py # Ordered sentence-by-sentence TTS playback
│       │   ├── wake_word.py    # "Эй, Kez" listener with local voice-activity detection
│       │   └── video_companion.py # Seamless animated video player (idle & search loops)
│       ├── 📁 cache/images/    # Front-end local image cache (auto-cleans > 7 days)
│       ├── 📁 cache/audio/     # Voice recordings & TTS replies (auto-cleans > 7 days)
│       ├── 📁 cache/files/     # Images pasted from the clipboard (auto-cleans > 7 days)
│       ├── 📁 assets/          # Application media (MP4 animations, icons)
│       ├── main_window.py      # Main window: streaming, voice, reminders, tray, pet mode
│       ├── style.qss           # Modern dark-mode QSS stylesheet
│       └── style_light.qss     # Light theme overrides
├── 📁 core/                    # System utilities & loaders
│   ├── 📁 constants/           # Dedicated modular constants
│   │   ├── image_const.py      # Imagen models, cache TTL, and image formats
│   │   ├── const.py            # Regex intent rules, fallback models & prompt loading
│   │   └── file_const.py       # Supported file types, export formats, TTS models & voices
│   ├── settings.py             # User settings (~/.kez_ai/settings.json)
│   ├── i18n.py                 # tr() translations, language detection, prompt localization
│   ├── 📁 locales/             # ru.json / en.json UI texts and fixed replies
│   ├── loader.py               # Database and environment initialization
│   └── logger.py               # Structured console & JSONL logger
├── 📁 tech/                    # Database abstraction layer
│   ├── basicDB.py              # Asyncpg connection pool wrapper
│   └── database.py             # Schema definitions, migrations, and CRUD
├── 📁 tests/                   # pytest suite (offscreen Qt)
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
> Database tables (`history_chats`, `messages`, `user_info`, `user_facts`, `reminders`), procedures, and indexes (including the full-text GIN index) are **automatically verified and created** on first launch!

### 🎛️ In-app settings
Everything else is configured in the app via **⚙️ Settings** and saved to `~/.kez_ai/settings.json`:

| Tab | Options |
|---|---|
| **Общие** | Language (Русский / English), theme (dark / light), preferred Gemini model, export folder (default `~/Documents/Kez AI`) |
| **Голос** | TTS voice, speak all replies, streaming speech, "Эй, Kez" + sensitivity threshold |
| **Память** | Learn facts from conversations, review / forget remembered facts |

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
4. Expired cached images, audio and pasted files (older than 7 days) are cleaned up.
5. Reminder checks start (missed reminders fire right away), the tray icon appears, and "Эй, Kez" starts listening if enabled.
6. You can start chatting immediately — by text, by voice 🎙️, or by attaching a file 📎!

### 💡 Usage tips
| Want to… | Do this |
|---|---|
| Ask about files | Click 📎 (several files at once), drag files onto the window or press `Ctrl+V` with a screenshot, then ask a question |
| Export a document | *«Сохрани наш диалог в pdf»*, *«Сделай таблицу расходов в excel»*, *«Создай презентацию про птиц»*, *«Экспортируй в word»* |
| Talk to Kez | Click 🎙️ to record and click again to send — or enable "Эй, Kez" in Settings and just say *«Эй, Kez, какая погода?»* |
| Generate / edit an image | *«Нарисуй закат над морем»*, then *«Сделай этот рисунок в стиле аниме»* |
| Set a reminder | *«Напомни через 20 минут проверить духовку»*, *«Поставь таймер на 5 минут»*, *«Мои напоминания»* |
| Find an old conversation | Type in the 🔍 search field in the sidebar |
| Keep Kez on screen | Click 🐤 — Kez moves to the corner of the screen; ⤢ or double-click brings the window back |

---

## 🧪 Testing

```bash
python -m pytest tests -q
```

Tests run Qt in offscreen mode and need no API key: they cover the intent rules, all six export formats, reminder time parsing, marker parsing, fact extraction helpers, wake-word matching and settings. `tests/test_database.py` runs against the PostgreSQL from `DATABASE_URL` (start it with `docker-compose up -d db`) and is skipped if the database is unreachable.

**CI:** [GitHub Actions](.github/workflows/tests.yml) runs the whole suite on every push and pull request to `master` / `dev`, with a PostgreSQL 16 service container.

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
- [x] ⚡ Real-Time Streaming Pipeline (`generate_content_stream` token streaming in PyQt6).
- [x] 🎨 Text-to-Image generation pipeline (Google Imagen 3 with prompt engineering, local cache, and right-click Copy/Download).
- [x] 📁 File analyzer and document exporter (PDF, Markdown, TXT).
- [x] 🎙️ Voice synthesis & speech recognition (TTS / STT integration).
- [x] ⚙️ Settings panel (theme, TTS voice & auto-speak, model choice, export folder).
- [x] 🧠 Long-term memory: automatic extraction of new user facts from conversations.
- [x] 🖱️ Drag & drop and clipboard paste for attachments; multiple files per message.
- [x] ⏰ Reminders & timers with system tray notifications.
- [x] 🐤 Floating "desktop pet" mode — Kez lives in a small always-on-top window.
- [x] 👂 "Эй, Kez" wake word and sentence-by-sentence streaming speech.
- [x] 🖌️ Image editing ("make this picture anime style").
- [x] 📊 Excel / PowerPoint export and DOCX output.
- [x] 🧪 pytest test suite.
- [x] 🔎 Full-text search across chat history.
- [x] 🌍 Russian / English interface with first-run language choice.
- [ ] 🔁 Recurring reminders ("каждый день в 9:00") and snooze from the notification.
- [ ] 🌐 Offline wake word (local keyword spotting) to avoid sending phrases to the cloud.

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
