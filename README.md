# InterView AI

A real-time AI interview coaching system that simulates technical interviews with voice-first interaction and live delivery feedback. The system generates context-aware questions from resume and job description inputs, evaluates answers for technical accuracy, and provides zero-latency coaching on speaking delivery.

## Features

**Implemented:**

- **Context-Aware Question Generation** - Generates interview questions tailored to the candidate's resume and target job description using Google Gemini 2.0 Flash
- **Answer Evaluation** - Scores answers on technical accuracy, clarity, depth, and completeness with improvement tips
- **Real-Time Coaching (AudioCoach)** - Local signal processing for zero-latency feedback:
  - Volume analysis via RMS calculation
  - Speaking pace tracking (words per minute)
  - Filler word detection ("um", "uh", "like", etc.)
- **Speech-to-Text** - Local transcription using faster-whisper with configurable model sizes
- **Text-to-Speech** - Audio synthesis for question playback using pyttsx3
- **Resume Parsing** - PDF text extraction with encrypted file handling
- **Session Management** - State machine for interview flow with session statistics
- **REST API** - FastAPI backend with OpenAPI documentation
- **Web Frontend** - HTML/CSS/JavaScript interface with setup wizard, live coaching HUD, and session summary

**Experimental / Partial:**

- Voice input in browser (placeholder implemented, microphone recording not wired)
- Docker deployment (references legacy Streamlit configuration and requires updates for FastAPI)

## Tech Stack

**Runtime:**

| Layer | Technology |
|-------|------------|
| Backend Framework | FastAPI 0.109+ with uvicorn |
| LLM | Google Gemini 2.0 Flash via `google-generativeai` |
| Speech-to-Text | faster-whisper (local Whisper inference) |
| Text-to-Speech | pyttsx3 (local synthesis) |
| PDF Parsing | pypdf |
| Configuration | Pydantic Settings with `.env` loading |
| Audio Processing | numpy, pydub |

**Frontend:**

| Component | Technology |
|-----------|------------|
| Markup | HTML5 |
| Styling | Vanilla CSS with Inter font |
| Logic | Vanilla JavaScript |

**Development:**

| Tool | Purpose |
|------|---------|
| pytest | Testing framework |
| pytest-asyncio | Async test support |
| pytest-cov | Coverage reporting |

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    HTML/CSS/JS FRONTEND                         │
│      [Setup Wizard]  [Interview Panel]  [Coaching HUD]         │
└──────────────────────────────┬─────────────────────────────────┘
                               │ HTTP/REST
┌──────────────────────────────▼─────────────────────────────────┐
│                      FASTAPI LAYER                              │
│              src/api/app.py + src/api/routes.py                 │
│    Endpoints: /api/session, /api/question, /api/answer, etc.   │
└──────────────────────────────┬─────────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────────┐
│                   APPLICATION LAYER                             │
│  ┌────────────────────────┐  ┌─────────────────────────────┐   │
│  │ InterviewOrchestrator  │  │      AudioCoach (LOCAL)     │   │
│  │     State Machine      │  │  • Volume (RMS)             │   │
│  │ IDLE→SETUP→ASKING→...  │  │  • WPM Tracking             │   │
│  └────────────┬───────────┘  │  • Filler Detection         │   │
│               │              └─────────────────────────────┘   │
└───────────────┼────────────────────────────────────────────────┘
                │
┌───────────────▼────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                          │
│   [GeminiInterviewer]  [WhisperSTT]  [TTSEngine]  [PDFParser]  │
│        (Cloud)           (Local)       (Local)       (Local)   │
└────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `InterviewOrchestrator` | `src/app/orchestrator.py` | Manages interview state machine, coordinates all adapters |
| `AudioCoach` | `src/app/coaching.py` | Zero-latency local signal processing for delivery feedback |
| `GeminiInterviewer` | `src/infra/llm/gemini.py` | LLM integration for question generation and answer evaluation |
| `WhisperSTT` | `src/infra/speech/stt.py` | Speech-to-text transcription with singleton model caching |
| `TTSEngine` | `src/infra/speech/tts.py` | Text-to-speech synthesis for question audio |
| `PDFParser` | `src/infra/utils/pdf_parser.py` | Resume text extraction from uploaded PDFs |

## Setup & Installation

### Prerequisites

- Python 3.11 or higher
- ffmpeg (required for audio processing)
- Google Gemini API key

### 1. Clone and Create Virtual Environment

```bash
cd "System 32 - Inter View AI"

python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env
# Edit .env and set your Gemini API key
```

**Required Environment Variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google AI API key |
| `WHISPER_MODEL` | No | Model size: `tiny`, `base`, `small`, `medium`, `large` (default: `tiny`) |
| `WHISPER_DEVICE` | No | Device: `cpu`, `cuda`, `auto` (default: `cpu`) |
| `VOLUME_THRESHOLD` | No | RMS threshold for "speak up" alert (default: `0.02`) |
| `WPM_FAST` | No | WPM threshold for "slow down" alert (default: `160`) |
| `WPM_SLOW` | No | WPM threshold for "speed up" alert (default: `100`) |

### 3. Run the Application

```bash
# Run FastAPI server (default: http://localhost:8000)
python main.py

# Or run CLI demo for testing
python main.py --cli

# Additional options
python main.py --host 0.0.0.0 --port 8080 --debug
```

## Usage

### Web Interface

1. Open `http://localhost:8000` in your browser
2. Upload your resume PDF in the setup panel
3. Paste the target job description
4. Click "Start Interview" to begin
5. Answer questions via text input (voice input not yet implemented)
6. Review real-time coaching metrics and answer evaluations
7. End session to view summary statistics

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/session/start` | Start a new interview session |
| `POST` | `/api/session/end` | End session and get summary |
| `GET` | `/api/session/stats` | Get current session statistics |
| `GET` | `/api/question` | Get next interview question |
| `POST` | `/api/answer` | Submit answer and get evaluation |
| `POST` | `/api/resume/upload` | Upload and parse resume PDF |
| `GET` | `/api/health` | Health check |

API documentation available at `http://localhost:8000/api/docs`

### CLI Demo

```bash
python main.py --cli
```

Runs a single-question demo with mock resume data to verify Gemini API connectivity.

## Project Structure

```
InterView-AI/
├── main.py                 # Entry point (FastAPI server or CLI)
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── Dockerfile              # Container build (Streamlit - needs update)
├── docker-compose.yml      # Container orchestration
│
├── src/
│   ├── api/
│   │   ├── app.py          # FastAPI application factory
│   │   ├── routes.py       # API endpoint definitions
│   │   └── schemas.py      # Pydantic request/response models
│   │
│   ├── app/
│   │   ├── orchestrator.py # Interview state machine
│   │   └── coaching.py     # AudioCoach signal processing
│   │
│   ├── core/
│   │   ├── config.py       # Pydantic settings
│   │   ├── prompts.py      # LLM prompt templates
│   │   ├── exceptions.py   # Custom exception classes
│   │   └── domain/         # Domain models (sessions, feedback)
│   │
│   ├── infra/
│   │   ├── llm/
│   │   │   └── gemini.py   # Gemini API adapter
│   │   ├── speech/
│   │   │   ├── stt.py      # Whisper transcription
│   │   │   └── tts.py      # pyttsx3 synthesis
│   │   └── utils/
│   │       └── pdf_parser.py
│   │
│   └── ui/                 # Legacy Streamlit dashboard (unused)
│
├── frontend/
│   ├── index.html          # Main HTML page
│   ├── css/styles.css      # Stylesheet
│   └── js/app.js           # Frontend logic
│
├── tests/
│   ├── conftest.py         # Pytest fixtures
│   ├── test_coaching.py    # AudioCoach unit tests
│   └── test_pdf_parser.py  # PDF parser tests
│
└── data/
    ├── resumes/            # Uploaded resume storage
    └── session_logs/       # Session data (created at runtime)
```

## Security
 
This project uses **GitGuardian (ggshield)** to prevent secret leakage.
 
### Local Setup (Pre-commit)
 
1. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```
 
2. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```
 
3. (Optional) Run a manual scan:
   ```bash
   ggshield secret scan repo .
   ```
 
### CI/CD
 
A GitHub Action workflow (`.github/workflows/gitguardian.yml`) is configured to automatically scan pushes and pull requests for hardcoded secrets.
 
## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_coaching.py -v
```

## Known Limitations

1. **Voice Input Not Implemented** - The frontend shows a text input placeholder. Microphone recording and WebRTC streaming are not wired.

2. **Docker Configuration Outdated** - Dockerfile and docker-compose.yml reference the legacy Streamlit UI and port 8501. The current FastAPI server runs on port 8000.

3. **No Session Persistence** - Interview sessions exist only in memory. Restarting the server loses all session data.

4. **Single-User Design** - Uses a global orchestrator instance. Concurrent users would share state.

5. **No Authentication** - API endpoints have no access control. CORS is set to allow all origins.

6. **Whisper Model Loading** - The Whisper model loads synchronously on first transcription request, causing a delay of several seconds.

7. **TTS Platform Dependency** - pyttsx3 relies on platform-specific speech engines (SAPI5 on Windows, espeak on Linux) which may produce varying audio quality.

## Future Improvements

1. **Implement WebRTC Audio Streaming** - Add browser microphone capture with real-time streaming to enable true voice-first interaction.

2. **Update Docker Configuration** - Modify Dockerfile to run the FastAPI server instead of Streamlit.

3. **Add Session Persistence** - Store interview sessions in SQLite or PostgreSQL to survive restarts.

4. **Implement User Scoping** - Add session tokens to support concurrent users without shared state.

5. **Async Model Loading** - Load Whisper model at startup or in background thread to avoid first-request latency.

6. **Add Rate Limiting** - Protect Gemini API usage with request throttling.

## License

Apache License 2.0 - See [LICENSE](LICENSE) file for details.

---

**GitHub Repository Description (2-3 lines):**

> Real-time AI interview coach with context-aware question generation (Gemini 2.0), local speech transcription (Whisper), and zero-latency coaching feedback on speaking delivery. Built with FastAPI and vanilla HTML/CSS/JS frontend.
