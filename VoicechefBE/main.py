import os
import shutil
import speech_recognition as sr
import whisper
import pyttsx3
from openai import OpenAI

# ---------- CONFIG ----------
# ffmpeg location (you already have this)
os.environ["PATH"] += os.pathsep + r"C:\ffmpg\bin"
print("ffmpeg path:", shutil.which("ffmpeg"))

# OpenAI client (API key must be in OPENAI_API_KEY env var)
client = OpenAI(
  api_key=""
)

#api key yazan yere api key koymak lazım hardcopy yazınca githubdan pushlatmıyo bende 5 dolarlık var atabilirim denemek isterseniz

# ---------- MODELS ----------
# Whisper STT model
model = whisper.load_model("small")  # or "base"/"tiny" if needed

# SpeechRecognition recognizer
r = sr.Recognizer()
r.pause_threshold = 1.2

# pyttsx3 TTS engine
engine = pyttsx3.init()

# Try to select an English voice if available
voices = engine.getProperty("voices")
for v in voices:
    if "English" in v.name or "en-" in v.id.lower():
        engine.setProperty("voice", v.id)
        break

# ---------- FUNCTIONS ----------

def speak(text: str):
    """Read GPT's answer out loud."""
    print("Voice Chef:", text)
    engine.say(text)
    engine.runAndWait()

def record_text() -> str:
    """Listen from microphone and return transcribed English text."""
    while True:
        try:
            with sr.Microphone() as source2:
                print("\nCalibrating microphone, please stay silent for 1 second...")
                r.adjust_for_ambient_noise(source2, duration=1.0)

                print("Listening...")
                audio2 = r.listen(source2)

                # Save temporary wav
                wav_path = "temp.wav"
                with open(wav_path, "wb") as f:
                    f.write(audio2.get_wav_data())

                # Transcribe with Whisper (English)
                result = model.transcribe(
                    wav_path,
                    language="en",   # listening in English
                    fp16=False
                )
                my_text = result["text"].strip()
                print("You said:", my_text)

                os.remove(wav_path)
                return my_text
        
        except Exception as e:
            print("An error occurred while recording:", repr(e))

def ask_gpt(prompt: str) -> str:
    """Send text to GPT-4o mini and return the model's reply."""
    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )
        # If your SDK has output_text helper:
        try:
            return response.output_text.strip()
        except AttributeError:
            # Fallback to raw structure
            return response.output[0].content[0].text.strip()
    except Exception as e:
        print("Error while calling GPT:", repr(e))
        return "Sorry, I had a problem talking to my brain."

def log_text(role: str, text: str):
    """Save conversation to a log file."""
    with open("conversation_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{role}: {text}\n")

# ---------- MAIN LOOP ----------

print("Voice Chef is ready. Say 'goodbye' to exit.\n")

while True:
    user_text = record_text()

    if user_text.lower() in ["goodbye", "exit", "quit", "stop"]:
        speak("Goodbye, see you later!")
        break

    log_text("User", user_text)

    gpt_reply = ask_gpt(user_text)
    log_text("Assistant", gpt_reply)

    speak(gpt_reply)
