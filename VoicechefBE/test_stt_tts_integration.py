#!/usr/bin/env python3
"""
Integrated test for STT → Backend → TTS flow.

This simulates the full Unity workflow:
1. Record audio (STT)
2. Send to backend
3. Get TTS message
4. Optionally play audio

Usage:
    python3 test_stt_tts_integration.py
"""

import sys
import requests
import tempfile
import os
import time
import struct
import math
import wave  # Standard library, always available

# Try to import audio libraries
try:
    import pyaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️  pyaudio not installed. Install with: pip install pyaudio")

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("⚠️  pyttsx3 not installed. Install with: pip install pyttsx3")

# Configuration
API_URL = "http://localhost:8000"


def record_audio(duration=5):
    """Record audio from microphone with better quality settings."""
    if not AUDIO_AVAILABLE:
        print("❌ Cannot record: pyaudio not available")
        return None
    
    print(f"🎤 Recording for {duration} seconds... (speak clearly and loudly!)")
    print("   (Make sure your microphone is working and not muted)\n")
    
    audio = pyaudio.PyAudio()
    
    # Use higher quality settings for better transcription
    sample_rate = 16000  # Whisper works best with 16kHz
    channels = 1
    chunk = 1024
    format = pyaudio.paInt16
    
    try:
        # List available input devices
        print("📱 Checking microphone...")
        default_input = audio.get_default_input_device_info()
        print(f"   Using: {default_input['name']}")
        print(f"   Sample rate: {sample_rate} Hz")
        print(f"   Channels: {channels}\n")
        
        # Open stream with explicit device
        stream = audio.open(
            format=format,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=None,  # Use default
            frames_per_buffer=chunk
        )
        
        print("🔴 Recording... (speak now!)\n")
        
        frames = []
        for i in range(0, int(sample_rate / chunk * duration)):
            try:
                data = stream.read(chunk, exception_on_overflow=False)
                frames.append(data)
            except Exception as e:
                print(f"⚠️  Read error: {e}")
                break
        
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        if not frames:
            print("❌ No audio data recorded!")
            return None
        
        # Save to temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_path = temp_file.name
        temp_file.close()
        
        wf = wave.open(temp_path, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(audio.get_sample_size(format))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        # Check file size and analyze audio
        file_size = os.path.getsize(temp_path)
        print(f"✅ Audio saved ({file_size} bytes)")
        
        if file_size < 1000:  # Less than 1KB is suspicious
            print("⚠️  Warning: Audio file is very small. Microphone might not be working properly.")
        
        # Analyze audio levels
        try:
            with wave.open(temp_path, 'rb') as wf:
                frames_data = wf.readframes(wf.getnframes())
                # Convert to integers
                audio_data = struct.unpack(f'<{len(frames_data)//2}h', frames_data)
                # Calculate RMS (root mean square) for volume
                rms = math.sqrt(sum(x*x for x in audio_data) / len(audio_data))
                max_amplitude = max(abs(x) for x in audio_data)
                
                print(f"   Audio levels: RMS={rms:.0f}, Max={max_amplitude}")
                
                # Check if audio is too quiet
                if rms < 1000:  # Threshold for "quiet"
                    print("⚠️  Warning: Audio seems very quiet!")
                    print("   - Speak louder and closer to microphone")
                    print("   - Check microphone volume in system settings")
                elif max_amplitude < 5000:
                    print("⚠️  Warning: Audio levels are low")
                    print("   - Try speaking louder")
        except Exception as e:
            print(f"   (Could not analyze audio levels: {e})")
        
        return temp_path
    
    except Exception as e:
        print(f"❌ Recording error: {e}")
        if audio:
            audio.terminate()
        return None


def transcribe_audio(audio_path):
    """Transcribe audio using backend."""
    print(f"\n📤 Transcribing audio...")
    
    # Check audio file first
    try:
        import wave
        with wave.open(audio_path, 'rb') as wf:
            frames = wf.getnframes()
            sample_rate = wf.getframerate()
            duration = frames / float(sample_rate)
            print(f"   Audio: {duration:.2f}s, {sample_rate}Hz, {frames} frames")
            
            # Check if audio seems too short or empty
            if duration < 0.5:
                print("⚠️  Warning: Audio is very short (< 0.5s)")
            if frames < 1000:
                print("⚠️  Warning: Very few audio frames")
    except Exception as e:
        print(f"⚠️  Could not analyze audio file: {e}")
    
    try:
        with open(audio_path, 'rb') as audio_file:
            files = {'audio_file': (os.path.basename(audio_path), audio_file, 'audio/wav')}
            print("   Sending to Whisper...")
            response = requests.post(f"{API_URL}/transcribe", files=files, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            text = data.get('text', '').strip()
            
            if not text or text.lower() in ['you', 'you.', 'you,', '']:
                print(f"⚠️  Warning: Transcription seems incorrect: '{text}'")
                print("   Possible issues:")
                print("   - Audio too quiet (speak louder)")
                print("   - Background noise")
                print("   - Microphone not picking up properly")
                print("   - Try speaking more clearly and closer to mic")
            else:
                print(f"✅ Transcribed: '{text}'")
            
            return text
        else:
            print(f"❌ Transcription error: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   {error_detail}")
            except:
                print(f"   {response.text}")
            return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def send_to_backend(text, session_id=None):
    """Send transcribed text to backend and get TTS response."""
    if not session_id:
        # Start a recipe
        print(f"\n📝 Starting recipe with: '{text}'")
        try:
            response = requests.post(
                f"{API_URL}/start_recipe",
                json={"user_message": text},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                session_id = data.get('session_id')
                tts_message = data.get('tts_message', '')
                print(f"✅ Recipe created!")
                print(f"💬 Chef: {tts_message}\n")
                return session_id, tts_message
            else:
                print(f"❌ Error: {response.status_code}")
                return None, None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None, None
    else:
        # Interpret command
        print(f"\n📝 Interpreting: '{text}'")
        try:
            response = requests.post(
                f"{API_URL}/interpret",
                json={
                    "session_id": session_id,
                    "user_message": text
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                tts_message = data.get('tts_message', '')
                action = data.get('action', '')
                print(f"✅ Command processed! (Action: {action})")
                print(f"💬 Chef: {tts_message}\n")
                return session_id, tts_message
            else:
                print(f"❌ Error: {response.status_code}")
                return session_id, None
        except Exception as e:
            print(f"❌ Error: {e}")
            return session_id, None


def play_tts(text):
    """Play TTS audio using macOS 'say' command or pyttsx3."""
    import platform
    import subprocess
    
    print("🔊 Playing chef's response...")
    
    # On macOS, use built-in 'say' command (more reliable than pyttsx3)
    if platform.system() == "Darwin":
        try:
            # Clean text for command line (remove emojis and special chars)
            clean_text = text.encode('ascii', 'ignore').decode('ascii')
            # Use macOS built-in TTS
            subprocess.run(['say', clean_text], check=True)
            print("✅ Audio playback complete!\n")
            return
        except subprocess.CalledProcessError:
            print("⚠️  macOS 'say' command failed")
        except Exception as e:
            print(f"⚠️  Error with 'say' command: {e}")
    
    # Fallback to pyttsx3 (if available and not on macOS)
    if not TTS_AVAILABLE:
        print("⚠️  Cannot play audio: pyttsx3 not available")
        print("   Install: pip install pyttsx3")
        return
    
    try:
        # Try pyttsx3 as fallback
        engine = pyttsx3.init()
        
        # Set English voice
        voices = engine.getProperty("voices")
        if voices:
            for v in voices:
                if "English" in v.name or "en-" in v.id.lower() or "en_US" in v.id:
                    engine.setProperty("voice", v.id)
                    break
        
        engine.setProperty("rate", 150)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        print("✅ Audio playback complete!\n")
    except Exception as e:
        print(f"❌ Error playing audio: {e}")
        print("   💡 Tip: Audio playback is optional. The text response is shown above.")
        if platform.system() == "Darwin":
            print("   On macOS, 'say' command should work. If not, check system permissions.")


def main():
    """Main integration test."""
    print("=" * 60)
    print("🎤🔊 VoiceChef STT → Backend → TTS Integration Test")
    print("=" * 60)
    
    # Check server
    try:
        response = requests.get(f"{API_URL}/", timeout=2)
        if response.status_code != 200:
            print("⚠️  Server issue\n")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running!")
        print(f"   Start it with: cd VoicechefBE && uvicorn app.main:app --reload --port 8000\n")
        return
    
    if not AUDIO_AVAILABLE:
        print("❌ Cannot test: pyaudio not installed")
        print("   Install with: pip install pyaudio")
        print("   For macOS: brew install portaudio && pip install pyaudio\n")
        return
    
    print("\nThis will test the full flow:")
    print("1. Record your voice (5 seconds)")
    print("2. Transcribe with Whisper")
    print("3. Send to backend")
    print("4. Get TTS response")
    print("5. Play audio (if pyttsx3 available)\n")
    
    input("Press Enter to start recording...")
    
    # Step 1: Record
    audio_path = record_audio(duration=5)
    if not audio_path:
        return
    
    # Step 2: Transcribe
    transcribed_text = transcribe_audio(audio_path)
    os.remove(audio_path)  # Clean up
    
    if not transcribed_text:
        return
    
    # Step 3 & 4: Send to backend
    session_id, tts_message = send_to_backend(transcribed_text)
    
    if tts_message:
        # Step 5: Play audio
        if TTS_AVAILABLE:
            play_audio = input("\nPlay audio? (y/n): ").lower().strip()
            if play_audio == 'y':
                play_tts(tts_message)
        else:
            print("\n💡 Install pyttsx3 to hear audio: pip install pyttsx3")
        
        # Continue conversation?
        continue_conv = input("\nContinue conversation? (y/n): ").lower().strip()
        if continue_conv == 'y' and session_id:
            while True:
                user_input = input("\nYou (or 'quit' to exit): ").strip()
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                _, tts_msg = send_to_backend(user_input, session_id)
                if tts_msg and TTS_AVAILABLE:
                    play_audio = input("Play audio? (y/n): ").lower().strip()
                    if play_audio == 'y':
                        play_tts(tts_msg)
    
    print("\n✨ Test complete!")


if __name__ == "__main__":
    main()

