import os
import json
import tempfile
import requests
import sounddevice as sd
import soundfile as sf
import whisper
import pyttsx3
from openai import OpenAI
from dotenv import load_dotenv


# ============================================================
# LOAD ENV VARIABLES
# ============================================================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY missing from .env")

client = OpenAI(api_key=OPENAI_API_KEY)


# ============================================================
# VOICE CHEF SYSTEM PROMPT
# ============================================================
VOICE_SYSTEM = """
You are Voice Chef, the voice assistant running inside a HoloLens mixed reality cooking app.

You MUST ALWAYS respond with a single JSON object:

{
  "assistant_role": "voice_chef",
  "response_text": "What you will say out loud to the user.",
  "actions": [
    {
      "type": "one of: show_intro_card, show_ingredient_card, show_step_card, next_step, previous_step, repeat_step, set_timer",
      "parameters": {
        "step_index": number (optional),
        "duration_seconds": number (optional),
        "raw_text": "the user's original request"
      }
    }
  ]
}

Rules:
- JSON ONLY. No extra text.
- response_text: natural English sentence.
- actions must ALWAYS be an array.
- For show_step_card: include step_index.
- For set_timer: include duration_seconds.
- Always include raw_text.
- Never add commentary or markdown.
"""


# ============================================================
# INIT WHISPER
# ============================================================
print("Loading Whisper model…")
asr_model = whisper.load_model("small")


# ============================================================
# TEXT TO SPEECH
# ============================================================
def speak(text: str):
    if not text:
        return
    print("Voice Chef:", text)
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    engine.stop()


# ============================================================
# UNITY HTTP BRIDGE
# ============================================================
UNITY_ENDPOINT = "http://localhost:5005/voice_action"

def send_action_to_unity(action: dict):
    try:
        requests.post(UNITY_ENDPOINT, json=action)
        print("→ Sent to Unity:", action)
    except Exception as e:
        print("❌ Unity send error:", e)


# ============================================================
# GPT CALLER
# ============================================================
def ask_gpt(user_text: str) -> dict:
    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": VOICE_SYSTEM},
            {"role": "user", "content": user_text},
        ],
    )

    # Extract raw structured JSON
    try:
        raw = response.output_text.strip()
    except:
        raw = response.output[0].content[0].text.strip()

    print("\n--- RAW GPT OUTPUT ---")
    print(raw)
    print("-----------------------\n")

    # Safe JSON parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("⚠ JSON parsing failed — falling back.")
        return {
            "assistant_role": "voice_chef",
            "response_text": raw,
            "actions": [],
        }


# ============================================================
# MICROPHONE RECORDING WITH SOUNDDEVICE (NO PYAUDIO)
# ============================================================
def record_speech_to_text() -> str:
    try:
        samplerate = 16000
        duration = 5  # seconds
        print("Listening for 5 seconds…")

        audio = sd.rec(int(duration * samplerate),
                       samplerate=samplerate,
                       channels=1,
                       dtype='int16')

        sd.wait()

        # Save to temporary WAV file
        wav_path = tempfile.mktemp(suffix=".wav")
        sf.write(wav_path, audio, samplerate)

        # Whisper transcription
        result = asr_model.transcribe(wav_path, fp16=False)
        os.remove(wav_path)

        text = result["text"].strip()
        print("You said:", text)
        return text

    except Exception as e:
        print("❌ Recording error:", e)
        return ""


# ============================================================
# MAIN LOOP
# ============================================================
print("\nVoice Chef ready! Say 'goodbye' to exit.\n")

while True:
    user_text = record_speech_to_text()

    if not user_text:
        continue

    if user_text.lower() in ["goodbye", "exit", "quit", "stop"]:
        speak("Goodbye, see you later!")
        break

    # LLM Response
    result = ask_gpt(user_text)

    # Speak response
    speak(result.get("response_text", ""))

    # Handle actions
    actions = result.get("actions", [])
    print("Actions:", actions)

    for action in actions:
        send_action_to_unity(action)
