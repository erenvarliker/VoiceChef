import os
import shutil
import json
import speech_recognition as sr
import whisper
import pyttsx3
from openai import OpenAI

# ---------- ffmpeg path ----------
os.environ["PATH"] += os.pathsep + r"C:\ffmpg\bin"
print("ffmpeg path:", shutil.which("ffmpeg"))


import json
from openai import OpenAI

# ---------- OpenAI client ----------
client = OpenAI(
  api_key=""
)
#api key koymamız lazım bende var github a puslayamıyorum izin vermiyo

VOICE_CHEF_SYSTEM = """
You are Voice Chef, a friendly cooking and kitchen assistant running inside a HoloLens app.
The user is speaking in English. You must:
- Help with cooking, kitchen tasks, food questions, and simple smalltalk if needed.
- When the user asks for actions like "set a timer", "start a timer", "remind me", etc.,
  you must emit a structured action so the HoloLens app can react.

You MUST respond as a single JSON object with this exact schema:

{
  "assistant_role": "voice_chef",
  "response_text": "What you will say out loud to the user in English.",
  "actions": [
    {
      "type": "string, e.g. 'set_timer'",
      "parameters": {
        "duration_seconds": number (integer, optional, only for timers),
        "raw_text": "original user intent or extra info if needed"
      }
    }
  ]
}

Rules:
- Always include "assistant_role" and set it to "voice_chef".
- Always include "response_text" as a natural English sentence.
- Always include "actions" as an array (use [] if no action).
- For a timer request like "set a timer for 5 minutes", add ONE action:
  {
    "type": "set_timer",
    "parameters": {
      "duration_seconds": 300,
      "raw_text": "set a timer for 5 minutes"
    }
  }
- Do NOT include any explanation, comments, markdown, or code fences.
- Output MUST be valid JSON ONLY.
"""

def ask_gpt_structured(user_text: str) -> dict:
    """Call GPT and parse its JSON response into a Python dict."""
    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": VOICE_CHEF_SYSTEM},
            {"role": "user", "content": user_text},
        ],
    )

    # SDK'nin sağladığı helper varsa:
    try:
        raw = response.output_text
    except AttributeError:
        # Eski biçim: output[0].content[0].text gibi olabilir
        raw = response.output[0].content[0].text

    raw = raw.strip()
    print("RAW GPT OUTPUT:", raw)  # debug için

    # JSON'a parse et
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Model JSON dışına çıkarsa, minimum düzeltme: hiçbir action yok, text raw olsun
        print("JSON parse error, falling back.")
        data = {
            "assistant_role": "voice_chef",
            "response_text": raw,
            "actions": [],
        }

    return data


# ---------- Whisper / SR / TTS ----------
model = whisper.load_model("small")

r = sr.Recognizer()
r.pause_threshold = 1.2

def speak(text: str):
    """Create a fresh TTS engine each time and speak."""
    if not text:
        return

    print("Voice Chef:", text)

    engine = pyttsx3.init()  # new engine each call

    # optional: pick English voice
    voices = engine.getProperty("voices")
    for v in voices:
        if "English" in v.name or "en-" in v.id.lower():
            engine.setProperty("voice", v.id)
            break

    engine.say(text)
    engine.runAndWait()
    engine.stop()


def record_text() -> str:
    while True:
        try:
            with sr.Microphone() as source2:
                print("\nCalibrating microphone, please stay silent for 1 second...")
                r.adjust_for_ambient_noise(source2, duration=1.0)

                print("Listening...")
                audio2 = r.listen(source2)

                wav_path = "temp.wav"
                with open(wav_path, "wb") as f:
                    f.write(audio2.get_wav_data())

                result = model.transcribe(
                    wav_path,
                    language="en",
                    fp16=False
                )
                my_text = result["text"].strip()
                print("You said:", my_text)

                os.remove(wav_path)
                return my_text
        
        except Exception as e:
            print("Error while recording:", repr(e))

print("Voice Chef ready. Say 'goodbye' to exit.\n")

while True:
    user_text = record_text()

    if user_text.lower() in ["goodbye", "exit", "quit", "stop"]:
        speak("Goodbye, see you later!")
        break

    result = ask_gpt_structured(user_text)

    # Text to speak
    response_text = result.get("response_text", "")
    speak(response_text)

    # Actions for Unity/HoloLens
    actions = result.get("actions", [])
    print("Actions JSON:", actions)   # burada Unity'ye gönderilecek datayı görüyorsun
