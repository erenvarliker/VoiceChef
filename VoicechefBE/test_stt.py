#!/usr/bin/env python3
"""
Test script for Speech-to-Text (STT) using Whisper.

This script tests the /transcribe endpoint by:
1. Recording audio from microphone, OR
2. Using an existing audio file

Usage:
    python3 test_stt.py                    # Record from microphone
    python3 test_stt.py audio.wav          # Use audio file
"""

import sys
import requests
import tempfile
import os
from pathlib import Path

# Try to import audio recording libraries
try:
    import pyaudio
    import wave
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️  pyaudio not installed. Install with: pip install pyaudio")
    print("   For macOS: brew install portaudio && pip install pyaudio")

# Configuration
API_URL = "http://localhost:8000"
TRANSCRIBE_ENDPOINT = f"{API_URL}/transcribe"


def record_audio(duration=5, sample_rate=16000, channels=1, chunk=1024):
    """Record audio from microphone."""
    if not AUDIO_AVAILABLE:
        print("❌ Cannot record: pyaudio not available")
        return None
    
    print(f"🎤 Recording for {duration} seconds... (speak now!)")
    
    audio = pyaudio.PyAudio()
    
    try:
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk
        )
        
        frames = []
        for _ in range(0, int(sample_rate / chunk * duration)):
            data = stream.read(chunk)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        # Save to temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_path = temp_file.name
        temp_file.close()
        
        wf = wave.open(temp_path, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"✅ Audio saved to: {temp_path}")
        return temp_path
    
    except Exception as e:
        print(f"❌ Recording error: {e}")
        audio.terminate()
        return None


def transcribe_audio_file(audio_path):
    """Send audio file to /transcribe endpoint."""
    print(f"\n📤 Sending audio to {TRANSCRIBE_ENDPOINT}...")
    
    try:
        with open(audio_path, 'rb') as audio_file:
            files = {'audio_file': (os.path.basename(audio_path), audio_file, 'audio/wav')}
            response = requests.post(TRANSCRIBE_ENDPOINT, files=files, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            transcribed_text = data.get('text', '')
            detected_language = data.get('language', 'en')
            
            print(f"\n✅ Transcription successful!")
            print(f"   Language: {detected_language}")
            print(f"   Text: {transcribed_text}")
            return transcribed_text
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return None
    
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {API_URL}")
        print("   Make sure the server is running: uvicorn app.main:app --reload --port 8000")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_with_file(audio_path):
    """Test transcription with an audio file."""
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return
    
    print(f"📁 Using audio file: {audio_path}")
    transcribed = transcribe_audio_file(audio_path)
    
    if transcribed:
        print(f"\n✨ Test complete! Transcribed: '{transcribed}'")


def test_with_microphone():
    """Test transcription by recording from microphone."""
    if not AUDIO_AVAILABLE:
        print("❌ Cannot test microphone recording: pyaudio not installed")
        print("\n💡 Alternative: Use an audio file:")
        print("   python3 test_stt.py your_audio.wav")
        return
    
    print("🎤 Testing STT with microphone recording...")
    print("   (Make sure your microphone is working)\n")
    
    # Record audio
    audio_path = record_audio(duration=5)
    
    if audio_path:
        # Transcribe
        transcribed = transcribe_audio_file(audio_path)
        
        # Clean up
        if os.path.exists(audio_path):
            os.remove(audio_path)
        
        if transcribed:
            print(f"\n✨ Test complete! You said: '{transcribed}'")


def main():
    """Main test function."""
    print("=" * 60)
    print("🎤 VoiceChef STT (Speech-to-Text) Test")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get(f"{API_URL}/", timeout=2)
        if response.status_code == 200:
            print("✅ Server is running\n")
        else:
            print("⚠️  Server responded but with unexpected status\n")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running!")
        print(f"   Start it with: cd VoicechefBE && uvicorn app.main:app --reload --port 8000\n")
        return
    
    # Filter out comments and flags from arguments
    args = [arg for arg in sys.argv[1:] if not arg.startswith('#') and not arg.startswith('-')]
    
    # Check if audio file provided
    if len(args) > 0:
        audio_file = args[0]
        test_with_file(audio_file)
    else:
        test_with_microphone()


if __name__ == "__main__":
    main()

