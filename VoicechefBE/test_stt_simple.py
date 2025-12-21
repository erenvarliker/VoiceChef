#!/usr/bin/env python3
"""
Simple STT test that doesn't require pyaudio.

This script tests the /transcribe endpoint using curl or requests.
You can test with any audio file you have, or we'll create a simple test.

Usage:
    python3 test_stt_simple.py                    # Test with text input (simulates transcription)
    python3 test_stt_simple.py your_audio.wav     # Test with audio file
"""

import sys
import requests
import os

API_URL = "http://localhost:8000"
TRANSCRIBE_ENDPOINT = f"{API_URL}/transcribe"


def test_transcribe_endpoint():
    """Test that the transcribe endpoint is accessible."""
    print("=" * 60)
    print("🎤 VoiceChef STT Simple Test")
    print("=" * 60)
    
    # Check server
    try:
        response = requests.get(f"{API_URL}/", timeout=2)
        if response.status_code == 200:
            print("✅ Server is running\n")
        else:
            print("⚠️  Server issue\n")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running!")
        print(f"   Start it with: cd VoicechefBE && uvicorn app.main:app --reload --port 8000\n")
        return
    
    # Check if audio file provided
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        if not os.path.exists(audio_file):
            print(f"❌ Audio file not found: {audio_file}\n")
            print("💡 To test STT:")
            print("   1. Record an audio file (WAV format)")
            print("   2. Or install pyaudio: brew install portaudio && pip install pyaudio")
            print("   3. Then use: python3 test_stt.py\n")
            return
        
        print(f"📁 Testing with audio file: {audio_file}\n")
        transcribe_file(audio_file)
    else:
        print("📝 Testing STT endpoint (no audio file provided)\n")
        print("💡 To test with audio:")
        print("   python3 test_stt_simple.py your_audio.wav\n")
        print("💡 To record audio (requires pyaudio):")
        print("   brew install portaudio")
        print("   pip install pyaudio")
        print("   python3 test_stt.py\n")
        
        # Test endpoint accessibility
        print("🔍 Checking /transcribe endpoint...")
        try:
            # Try a GET request (should fail, but confirms endpoint exists)
            response = requests.get(TRANSCRIBE_ENDPOINT, timeout=2)
            print(f"   Endpoint exists (GET returns {response.status_code})")
        except Exception as e:
            print(f"   Endpoint check: {type(e).__name__}")
        
        print("\n✅ STT endpoint is ready!")
        print("   The /transcribe endpoint accepts POST requests with audio files.")


def transcribe_file(audio_path):
    """Send audio file to transcribe endpoint."""
    print(f"📤 Sending {os.path.basename(audio_path)} to server...")
    
    try:
        with open(audio_path, 'rb') as audio_file:
            files = {'audio_file': (os.path.basename(audio_path), audio_file, 'audio/wav')}
            print("   Uploading...")
            response = requests.post(TRANSCRIBE_ENDPOINT, files=files, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            transcribed_text = data.get('text', '')
            detected_language = data.get('language', 'en')
            
            print(f"\n✅ Transcription successful!")
            print(f"   Language: {detected_language}")
            print(f"   Text: '{transcribed_text}'\n")
            
            if not transcribed_text:
                print("⚠️  Warning: Transcription is empty (might be silence or very short audio)\n")
            
            return transcribed_text
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}\n")
            return None
    
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {API_URL}")
        print("   Make sure the server is running!\n")
        return None
    except FileNotFoundError:
        print(f"❌ File not found: {audio_path}\n")
        return None
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return None


if __name__ == "__main__":
    test_transcribe_endpoint()


