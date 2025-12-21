# VoiceChef HoloGuide Backend

FastAPI backend for the VoiceChef HoloGuide AR cooking assistant.

## ✅ Integration Status

**FULLY INTEGRATED** - The advanced backend is now complete and ready to use!

## Features

- 🎤 **Speech-to-Text**: Whisper integration for audio transcription
- 🍳 **Recipe Planning**: LLM-powered recipe generation from natural language
- 👨‍🍳 **Cooking Coach**: Step-by-step guidance with intent classification
- ⏱️ **Timer Management**: Voice-controlled timers
- 📊 **Analytics**: Session tracking for research
- 🔒 **Secure**: API keys stored in `.env` file (not in code)

## Quick Start

### 1. Install Dependencies

```bash
cd VoicechefBE
pip install -r requirements.txt
```

### 2. Configure API Keys

**Create `.env` file from template:**
```bash
cp env.example .env
```

**Edit `.env` and add your API keys:**
```env
# At least one is required (Groq recommended - faster & free tier)
OPENAI_API_KEY=sk-your-key-here
GROQ_API_KEY=gsk-your-key-here

# Models (defaults are fine)
OPENAI_MODEL=gpt-4o-mini
GROQ_MODEL=llama-3.1-8b-instant
WHISPER_MODEL=small
```

**Get API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- Groq: https://console.groq.com/ (recommended - free tier available)

### 3. Run Backend

```bash
uvicorn app.main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /
```

### Transcribe Audio
```
POST /transcribe
Content-Type: multipart/form-data
Body: audio_file (WAV, MP3, etc.)
```

### Start Recipe
```
POST /start_recipe
Content-Type: application/json
Body: {
  "user_message": "I want to cook pasta carbonara",
  "session_id": "optional-uuid"
}
```

### Interpret Command
```
POST /interpret
Content-Type: application/json
Body: {
  "session_id": "abc-123",
  "user_message": "next"
}
```

### Session Status
```
GET /session/{session_id}/status
```

### Session Analytics
```
GET /session/{session_id}/analytics
```

## Project Structure

```
VoicechefBE/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration (reads from .env)
│   ├── schemas.py           # Pydantic models
│   ├── state.py             # Session management
│   └── services/
│       ├── planner.py       # Recipe generation
│       └── coach.py         # Cooking coach (fully integrated!)
├── requirements.txt
├── env.example              # Template for .env
└── README.md
```

## Testing

### Test Recipe Creation
```bash
curl -X POST "http://localhost:8000/start_recipe" \
  -H "Content-Type: application/json" \
  -d '{"user_message": "I want to cook pasta"}'
```

### Test Command Interpretation
```bash
curl -X POST "http://localhost:8000/interpret" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "user_message": "next"
  }'
```

### Test Transcription
```bash
curl -X POST "http://localhost:8000/transcribe" \
  -F "audio_file=@test_audio.wav"
```

## Environment Variables

All configuration is done via `.env` file:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key |
| `GROQ_API_KEY` | Yes* | - | Groq API key (recommended) |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model |
| `GROQ_MODEL` | No | `llama-3.1-8b-instant` | Groq model |
| `WHISPER_MODEL` | No | `small` | Whisper model size |
| `DEBUG` | No | `true` | Debug mode |
| `CORS_ORIGINS` | No | `["*"]` | CORS allowed origins |

*At least one API key (OpenAI or Groq) is required.

## Security

⚠️ **IMPORTANT:** Never commit `.env` file to git! It contains sensitive API keys.

The `.env` file is already in `.gitignore` to prevent accidental commits.

## Next Steps

1. ✅ Backend structure created
2. ✅ Advanced backend integrated
3. ✅ Environment configuration set up
4. ⏳ Test all endpoints
5. ⏳ Create Unity C# integration scripts
6. ⏳ End-to-end testing

## Troubleshooting

### "No LLM client configured"
- Make sure you created `.env` file
- Add at least one API key (OPENAI_API_KEY or GROQ_API_KEY)
- Restart the server after adding keys

### "Module not found"
- Run `pip install -r requirements.txt`
- Make sure you're in the `VoicechefBE` directory

### CORS errors
- Update `CORS_ORIGINS` in `.env` to include your Unity client URL
- Or use `["*"]` for development (not recommended for production)
