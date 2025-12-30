"""
VoiceChef Automatic PC Client
- Detects voice activity (VAD) automatically
- Transcribes via Backend
- Manages Session State (Start vs Interpret)
- Text-to-Speech Output
"""

import pyaudio
import wave
import requests
import audioop
import time
import os
import tempfile
import platform
import subprocess
import sys

# Configuration
API_URL = "http://localhost:8000"
THRESHOLD = 1200          # Audio threshold (adjust based on mic sensitivity)
SILENCE_LIMIT = 2.0       # Seconds of silence to stop recording
PREV_AUDIO = 0.5          # Seconds of audio to keep before trigger (to catch first syllable)

class VoiceChefClient:
    def __init__(self):
        self.session_id = None
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.check_backend()

    def check_backend(self):
        try:
            requests.get(f"{API_URL}/")
            print("✅ Backend connected.")
        except:
            print(f"❌ Could not connect to {API_URL}. Is the server running?")
            sys.exit(1)

    def listen_for_speech(self):
        """
        Listens to the mic. 
        Returns filename of recorded wav when speech finishes.
        """
        if not self.stream:
            self.stream = self.p.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=16000,
                                      input=True,
                                      frames_per_buffer=1024)

        print("\n👂 Listening... (Start speaking)")
        
        audio2send = []
        cur_data = ''  # Current chunk
        rel = 0        # Silence counter
        slid_win = []  # Sliding window of audio chunks
        started = False

        while True:
            cur_data = self.stream.read(1024, exception_on_overflow=False)
            slid_win.append(cur_data)
            
            # Keep sliding window small (just pre-speech buffer)
            if len(slid_win) > int(16000/1024 * PREV_AUDIO):
                slid_win.pop(0)

            # Calculate volume (RMS)
            rms = audioop.rms(cur_data, 2)

            if rms > THRESHOLD:
                if not started:
                    print("🎤 Speech detected! Recording...")
                    started = True
                rel = 0 # Reset silence counter
            elif started:
                rel += 1

            if started:
                audio2send.append(cur_data)
                # If silence exceeds limit, stop
                if rel > int(16000/1024 * SILENCE_LIMIT):
                    print("🛑 Silence detected. Processing...")
                    break
        
        # Prepend the sliding window (to catch the start of the sentence)
        final_audio = slid_win + audio2send

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            wf = wave.open(f.name, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(16000)
            wf.writeframes(b''.join(final_audio))
            wf.close()
            return f.name

    def transcribe(self, filename):
        """Send audio to backend for Whisper transcription."""
        try:
            with open(filename, 'rb') as f:
                response = requests.post(f"{API_URL}/transcribe", files={'audio_file': f})
            
            if response.status_code == 200:
                text = response.json()['text']
                print(f"📝 You said: '{text}'")
                return text
            return None
        except Exception as e:
            print(f"Transcription error: {e}")
            return None

    def process_command(self, text):
        """Decide whether to Start Recipe or Interpret Command."""
        if not text or len(text.strip()) < 2:
            return

        try:
            # LOGIC: If no session_id, we must be starting a recipe
            if self.session_id is None:
                # FIX: Force a specific ID so Unity knows where to look
                dev_session_id = "holo-test"
                
                payload = {
                    "user_message": text,
                    "session_id": dev_session_id  # <--- WE ADD THIS LINE
                }
                
                print("🚀 Sending to /start_recipe...")
                res = requests.post(f"{API_URL}/start_recipe", json=payload)
                data = res.json()
                
                self.session_id = data['session_id']
                print(f"✅ Session Created: {self.session_id}")
                self.speak(data['tts_message'])

            # LOGIC: If session exists, we are cooking
            else:
                payload = {"session_id": self.session_id, "user_message": text}
                print("🍳 Sending to /interpret...")
                res = requests.post(f"{API_URL}/interpret", json=payload)
                
                if res.status_code == 404:
                    print("⚠️ Session expired or lost. Resetting.")
                    self.session_id = None
                    self.speak("I lost your session. Please tell me what you want to cook again.")
                    return

                data = res.json()
                print(f"🤖 Action: {data['action']}")
                
                # Check if recipe completed
                if data.get('recipe_complete'):
                    print("🎉 Recipe Complete!")
                    self.session_id = None # Reset for next dish
                
                self.speak(data['tts_message'])

        except Exception as e:
            print(f"Error processing command: {e}")

    def speak(self, text):
        """Text-to-Speech Output (Blocking, so we don't record ourselves)."""
        if not text: return
        
        # Print what is being spoken so you can read it if audio fails
        print(f"🔊 Chef: {text}")
        
        # macOS
        if platform.system() == "Darwin":
            subprocess.run(['say', text])
            
        # Windows (Powershell fallback)
        elif platform.system() == "Windows":
             # FIX: Escape single quotes for PowerShell (e.g., "you're" -> "you''re")
             safe_text = text.replace("'", "''")
             
             # Also escape double quotes just in case
             safe_text = safe_text.replace('"', '`"')
             
             subprocess.run([
                 "PowerShell", 
                 "-Command", 
                 f"Add-Type –AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe_text}');"
             ])
             
        # Linux (espeak fallback)
        else:
            try:
                subprocess.run(['espeak', text])
            except:
                print("(TTS Audio not supported on this OS without espeak)")

    def run(self):
        print("👨‍🍳 VoiceChef Client Running. speak naturally!")
        while True:
            try:
                # 1. Record
                audio_file = self.listen_for_speech()
                
                # 2. Transcribe
                text = self.transcribe(audio_file)
                
                # Cleanup file
                os.remove(audio_file)

                # 3. Process
                if text:
                    self.process_command(text)

            except KeyboardInterrupt:
                print("\n👋 Exiting...")
                break

if __name__ == "__main__":
    client = VoiceChefClient()
    client.run()