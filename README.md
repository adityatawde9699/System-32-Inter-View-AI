# InterView AI 🎙️

A real-time AI interview coach that simulates authentic technical interviews with voice-first interaction and live coaching feedback.

## Features

- **🎯 Context-Aware Questions**: Generates interview questions based on your resume and target job description using Gemini 2.0
- **🎤 Voice-First Interface**: Speak your answers naturally (or type for testing)
- **⚡ Real-Time Coaching**: Zero-latency feedback on speaking pace, volume, and filler words
- **📊 Answer Evaluation**: Technical accuracy, clarity, and depth scoring
- **📋 Session Summary**: Comprehensive post-interview report with improvement tips

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      STREAMLIT UI                            │
│         [Resume Upload] [Interview] [Coaching HUD]          │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    APPLICATION LAYER                         │
│  ┌─────────────┐  ┌─────────────────────────────────────┐   │
│  │ Orchestrator│  │        AudioCoach (LOCAL)            │   │
│  │ State Machine│  │  • Volume (RMS) • WPM • Fillers    │   │
│  └──────┬──────┘  └─────────────────────────────────────┘   │
│         │                                                    │
└─────────┼────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                        │
│  [Gemini LLM]  [Whisper STT]  [pyttsx3 TTS]  [PDF Parser]   │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Clone & Setup

```bash
cd "System 32 - Inter View AI"

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
copy .env.example .env

# Edit .env and add your Gemini API key
# GEMINI_API_KEY=your-api-key-here
```

### 3. Run the Application

```bash
# Run Streamlit dashboard
python main.py

# Or run CLI demo for testing
python main.py --cli
```

Open http://localhost:8501 in your browser.

## Usage

1. **Upload Resume**: Upload your PDF resume in the sidebar
2. **Add Job Description**: Paste the target job description
3. **Start Interview**: Click "Start Interview" to begin
4. **Answer Questions**: Speak or type your answers
5. **Review Feedback**: Get real-time coaching and post-answer evaluation
6. **End Session**: View your comprehensive interview summary

## Project Structure

```
InterView-AI/
├── src/
│   ├── core/           # Domain models, config, prompts
│   ├── app/            # Application logic (orchestrator, coaching)
│   ├── infra/          # External adapters (LLM, STT, TTS, PDF)
│   └── ui/             # Streamlit dashboard
├── tests/              # Unit and integration tests
├── data/               # Uploaded resumes and session logs
├── main.py             # Entry point
├── requirements.txt    # Python dependencies
└── docker-compose.yml  # Container deployment
```

## Key Components

### AudioCoach (The Winning Feature)
Local signal processing for zero-latency feedback:
- **Volume Analysis**: RMS calculation to detect mumbling
- **Pace Analysis**: Words-per-minute tracking
- **Filler Detection**: Counts "um", "uh", "like", etc.

### GeminiInterviewer
Cloud-powered question generation and evaluation:
- Context-aware questions from resume/JD
- Technical accuracy scoring
- Improvement recommendations

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | - | Google AI API key (required) |
| `WHISPER_MODEL` | `tiny` | Model size: tiny, base, small, medium, large |
| `WHISPER_DEVICE` | `cpu` | Device: cpu, cuda, auto |
| `WPM_FAST` | `160` | Words/min threshold for "slow down" alert |
| `WPM_SLOW` | `100` | Words/min threshold for "speed up" alert |
| `VOLUME_THRESHOLD` | `0.02` | RMS threshold for "speak up" alert |

## Docker Deployment

```bash
# Build and run
docker-compose up --build

# Access at http://localhost:8501
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Tech Stack

- **Python 3.11+**
- **Streamlit** - Web UI
- **Google Generative AI** - Gemini 2.0 for Q&A
- **faster-whisper** - Local speech recognition
- **pyttsx3** - Text-to-speech
- **pypdf** - Resume parsing
- **pydantic** - Configuration management

## License

MIT License - See LICENSE file for details.
