# VoiceChef HoloGuide - AI Backend

AI-powered backend for VoiceChef HoloGuide, a voice-controlled mixed reality cooking assistant for Microsoft HoloLens 2. This backend handles recipe generation, command interpretation, and cooking guidance without any audio processing (STT/TTS handled by Unity).

**CS 449-549 Human Computer Interaction Project**

## Architecture

```
User Voice → Unity/Azure STT → Text → Python Backend → JSON → Unity UI/TTS
```

### Responsibilities

**Unity (C# on HoloLens):**
- Microphone input
- Speech-to-text (Azure Speech SDK)
- Text-to-speech output
- AR UI rendering
- Timer visualization

**Python Backend (this repo):**
- AI logic only, no audio
- Recipe generation from natural language
- Command interpretation (next, repeat, questions, timers)
- Safety detection (heat/knife warnings)
- Session management
- Research analytics logging

## Features

- 🎙️ **Natural Language Processing**: Understands "I want to cook pasta carbonara"
- 🤖 **AI Recipe Generation**: Creates detailed recipes with LLM
- ⚠️ **Safety Detection**: Automatically flags steps requiring heat or knives
- ⏰ **Timer Management**: Parses "set timer for 3 minutes"
- 💬 **Q&A Support**: Answers cooking questions with context
- 📊 **Research Logging**: Tracks all interactions for NASA-TLX/SUS analysis
- 🔄 **Session Management**: Handles multiple concurrent cooking sessions

## Project Structure

```
voicechef_backend/
├─ app/
│  ├─ __init__.py
│  ├─ main.py              # FastAPI endpoints: /start_recipe, /interpret
│  ├─ config.py            # Settings and environment config
│  ├─ schemas.py           # Pydantic models (request/response)
│  ├─ state.py             # In-memory session/timer storage
│  └─ services/
│     ├─ __init__.py
│     ├─ planner.py        # LLM recipe generation + safety detection
│     └─ coach.py          # Command interpretation + coaching logic
├─ tests/
│  └─ test_basic.py
├─ requirements.txt
├─ .env.example
└─ README.md
```

## Installation

1. **Clone and navigate**:
```bash
cd voicechef_backend
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4
```

## Usage

### Start the Server

```bash
uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### 1. POST `/start_recipe`

**Unity sends natural language input:**
```json
{
  "user_message": "I want to cook pasta carbonara",
  "session_id": null
}
```

**Backend returns recipe with safety flags:**
```json
{
  "session_id": "abc-123-def",
  "action": "recipe_created",
  "recipe": {
    "dish_name": "Pasta Carbonara",
    "total_steps": 8,
    "ingredients": [
      "400g spaghetti",
      "200g pancetta",
      "4 large eggs",
      "100g Parmesan cheese"
    ],
    "steps": [
      {
        "step_number": 1,
        "instruction": "Boil water in a large pot with salt",
        "estimated_time": "5 minutes",
        "requires_heat": true,
        "requires_knife": false,
        "safety_confirmation": "This step involves heat. Please confirm you're ready to use the stove/oven."
      },
      {
        "step_number": 2,
        "instruction": "Dice the pancetta into small cubes",
        "estimated_time": "3 minutes",
        "requires_heat": false,
        "requires_knife": true,
        "safety_confirmation": "This step involves sharp objects. Please confirm you're ready."
      }
    ]
  },
  "tts_message": "Great! I've prepared a recipe for Pasta Carbonara. You'll need 400g spaghetti, 200g pancetta, and 2 more. There are 8 steps in total. Say 'next' when you're ready to start!"
}
```

### 2. POST `/interpret`

**Unity sends user command:**
```json
{
  "session_id": "abc-123-def",
  "user_message": "next"
}
```

**Backend returns action and step data:**
```json
{
  "session_id": "abc-123-def",
  "action": "next_step",
  "current_step": 1,
  "total_steps": 8,
  "step_data": {
    "step_number": 1,
    "instruction": "Boil water in a large pot with salt",
    "estimated_time": "5 minutes",
    "requires_heat": true,
    "requires_knife": false,
    "safety_confirmation": "This step involves heat. Please confirm you're ready to use the stove/oven."
  },
  "tts_message": "Step 1: Boil water in a large pot with salt. This should take about 5 minutes. This step involves heat. Please confirm you're ready to use the stove/oven.",
  "timer_data": null,
  "recipe_complete": false
}
```

### Supported Commands

**Navigation:**
- "next" / "continue" / "done" → Move to next step
- "repeat" / "again" → Repeat current step

**Timer:**
- "set timer for 3 minutes" → Creates timer
- "timer 30 seconds" → Creates 30s timer

**Control:**
- "pause" / "wait" → Pause session
- "resume" / "continue" → Resume session

**Questions:**
- "can I use olive oil instead?" → LLM answers with context
- "how long should I cook this?" → Context-aware answer
- "why do I need to add salt?" → Cooking advice

### Action Types

The backend returns different `action` types:

| Action | Description |
|--------|-------------|
| `recipe_created` | New recipe created successfully |
| `next_step` | Moved to next step |
| `repeat_step` | Repeated current step |
| `answer_question` | Answered user's question |
| `timer_set` | Timer created |
| `pause` | Session paused |
| `resume` | Session resumed |
| `recipe_complete` | All steps finished |
| `error` | Command unclear or error occurred |

### Research Endpoints

**GET `/session/{session_id}/status`**
```json
{
  "session_id": "abc-123",
  "dish_name": "Pasta Carbonara",
  "current_step_index": 2,
  "total_steps": 8,
  "is_paused": false,
  "active_timers": 1,
  "total_interactions": 15
}
```

**GET `/session/{session_id}/analytics`**

Returns detailed interaction log for research analysis (NASA-TLX, SUS, completion time):
```json
{
  "session_id": "abc-123",
  "recipe": "Pasta Carbonara",
  "total_interactions": 15,
  "interaction_breakdown": {
    "next_step": 8,
    "repeat_step": 2,
    "answer_question": 3,
    "timer_set": 2
  },
  "is_complete": false,
  "interaction_log": [
    {
      "timestamp": "2025-11-16T10:30:00Z",
      "type": "start_recipe",
      "user_message": "I want to cook pasta carbonara",
      "response": "Great! I've prepared a recipe..."
    }
  ]
}
```

**DELETE `/session/{session_id}`**

Deletes a session (cleanup).

## Safety Detection

The backend automatically detects and flags safety-critical steps:

### Heat Detection
Keywords: boil, fry, cook, bake, roast, grill, simmer, sauté, stove, oven, pan

### Knife Detection
Keywords: cut, chop, slice, dice, mince, knife, peel, trim, carve

Safety confirmations are generated for Unity to display before proceeding.

## Timer System

Timers are parsed from natural language:
- "set timer for 3 minutes" → 180 seconds
- "timer 5 minutes 30 seconds" → 330 seconds
- "set timer 45" → 45 minutes (default to minutes)

Unity receives `timer_data` with `timer_id`, `duration_seconds`, and `started_at` timestamp for countdown management.

## Development

### Run Tests
```bash
pytest tests/
```

### Code Structure

- **main.py**: FastAPI routes (`/start_recipe`, `/interpret`)
- **schemas.py**: Pydantic models for type safety
- **state.py**: In-memory session storage with interaction logging
- **planner.py**: LLM recipe generation + safety detection
- **coach.py**: Command interpretation + conversational coaching

### Adding New Commands

1. Add intent detection in `coach.py` → `_detect_intent()`
2. Create handler method (e.g., `_handle_new_command()`)
3. Add to `interpret_command()` routing
4. Update action type enum in `schemas.py` if needed

## Research Integration

The backend logs all interactions with timestamps for HCI research:

- **Completion time**: First to last interaction timestamp
- **Error rate**: Count of `repeat_step` and unclear commands
- **Interaction efficiency**: Steps completed vs. total interactions
- **Command distribution**: Breakdown of action types

Export analytics via `/session/{id}/analytics` for SPSS/R analysis.

## Future Enhancements

- [ ] Persistent storage (PostgreSQL/MongoDB)
- [ ] User profiles (novice/expert detection)
- [ ] Multi-language support (Turkish, Spanish, etc.)
- [ ] Recipe database integration
- [ ] Dietary restriction handling
- [ ] Ingredient substitution suggestions
- [ ] Gamification support (points, achievements)

## Contributing

This is a research project for CS 449-549. For questions or contributions, contact the team.

## License

MIT License

## Team

- **Eren**: AR integration & Unity
- **Serhat**: Voice systems & Azure Speech
- **Batuhan**: UI design
- **Ilgaz**: Research & ethics (AI backend)
- **İpek**: UX & study operations
- **Ozan**: Data analysis

## Citation

If you use this system in your research, please cite:

```
VoiceChef HoloGuide: An Audio-Driven Mixed Reality Cooking Assistant
CS 449-549 Human Computer Interaction, Sabancı University, 2025
```
