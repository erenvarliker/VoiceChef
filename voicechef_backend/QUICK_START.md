# Quick Start Guide

Get the VoiceChef backend up and running in 5 minutes.

## 1. Setup (2 minutes)

```bash
# Install dependencies
pip install -r requirements.txt

# Configure OpenAI
echo 'OPENAI_API_KEY=sk-your-key-here' > .env

# Start server
uvicorn app.main:app --reload
```

Server runs at: http://localhost:8000

## 2. Test with curl (2 minutes)

### Create a Recipe

```bash
curl -X POST http://localhost:8000/start_recipe \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "I want to cook an omelette",
    "session_id": null
  }'
```

**Copy the `session_id` from the response!**

### Get Next Step

```bash
# Replace YOUR_SESSION_ID with the actual ID
curl -X POST http://localhost:8000/interpret \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "user_message": "next"
  }'
```

### Ask a Question

```bash
curl -X POST http://localhost:8000/interpret \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "user_message": "can I use olive oil instead of butter?"
  }'
```

### Set a Timer

```bash
curl -X POST http://localhost:8000/interpret \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "user_message": "set timer for 3 minutes"
  }'
```

## 3. Interactive Testing (1 minute)

Visit: http://localhost:8000/docs

This opens Swagger UI where you can:
- Click on endpoints
- Try them out interactively
- See request/response examples
- No command line needed!

## Common Commands

| User Says | Backend Interprets | Action |
|-----------|-------------------|---------|
| "next" | Move forward | `next_step` |
| "repeat" | Repeat current | `repeat_step` |
| "set timer 5 minutes" | Create timer | `timer_set` |
| "can I use X?" | Answer question | `answer_question` |
| "pause" | Pause cooking | `pause` |
| "continue" | Resume | `resume` |

## Troubleshooting

### "OpenAI API key not provided"
→ Add your key to `.env` file

### "Session not found"
→ Use the `session_id` from `/start_recipe` response

### "Failed to create recipe"
→ Check OpenAI API key is valid

### Server won't start
→ Make sure port 8000 is free: `lsof -ti:8000 | xargs kill -9`

## Next Steps

- Read [README.md](README.md) for full documentation
- Read [UNITY_INTEGRATION.md](UNITY_INTEGRATION.md) for Unity/HoloLens integration
- Test endpoints with your HoloLens device
- Export research data with `python export_research_data.py`

## Example Workflow

```bash
# 1. Start recipe
curl -X POST http://localhost:8000/start_recipe \
  -H "Content-Type: application/json" \
  -d '{"user_message": "cook pasta carbonara", "session_id": null}'
# → Returns session_id: "abc-123"

# 2. Move to first step
curl -X POST http://localhost:8000/interpret \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc-123", "user_message": "next"}'
# → Returns step 1 with safety flags

# 3. Repeat if needed
curl -X POST http://localhost:8000/interpret \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc-123", "user_message": "repeat"}'
# → Repeats step 1

# 4. Set a timer
curl -X POST http://localhost:8000/interpret \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc-123", "user_message": "set timer for 10 minutes"}'
# → Returns timer_data with timer_id

# 5. Ask a question
curl -X POST http://localhost:8000/interpret \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc-123", "user_message": "how do I know when pasta is ready?"}'
# → Returns AI-generated answer

# 6. Continue cooking...
curl -X POST http://localhost:8000/interpret \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc-123", "user_message": "next"}'
# → Move to step 2

# 7. Check status (for debugging)
curl http://localhost:8000/session/abc-123/status
# → Returns current state

# 8. Get analytics (for research)
curl http://localhost:8000/session/abc-123/analytics
# → Returns full interaction log
```

## Visual Testing with Postman

1. Import this collection URL: `http://localhost:8000/openapi.json`
2. Create requests for `/start_recipe` and `/interpret`
3. Save session_id as environment variable
4. Test different commands visually

## Python Testing

```python
import requests

# Start recipe
response = requests.post(
    "http://localhost:8000/start_recipe",
    json={
        "user_message": "I want to cook an omelette",
        "session_id": None
    }
)
data = response.json()
session_id = data["session_id"]
print(f"Session: {session_id}")
print(f"Recipe: {data['recipe']['dish_name']}")
print(f"TTS: {data['tts_message']}")

# Get next step
response = requests.post(
    "http://localhost:8000/interpret",
    json={
        "session_id": session_id,
        "user_message": "next"
    }
)
data = response.json()
print(f"Action: {data['action']}")
print(f"Step: {data['step_data']['instruction']}")
print(f"TTS: {data['tts_message']}")
```

## Ready for HoloLens Integration?

See [UNITY_INTEGRATION.md](UNITY_INTEGRATION.md) for:
- C# HTTP request examples
- JSON response handling
- UI recommendations
- Complete workflow examples




