#!/usr/bin/env python3
"""
Test script for Text-to-Speech (TTS).

This script tests TTS by:
1. Testing text generation from the backend (tts_message)
2. Optionally playing audio using pyttsx3

Usage:
    python3 test_tts.py                    # Test text generation only
    python3 test_tts.py --play              # Also play audio with pyttsx3
    python3 test_tts.py "Hello world"       # Test specific text
"""

import sys
import requests
import json

# Configuration
API_URL = "http://localhost:8000"


def test_text_generation():
    """Test that backend generates TTS messages correctly."""
    print("=" * 60)
    print("🔊 VoiceChef TTS (Text-to-Speech) Test")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get(f"{API_URL}/", timeout=2)
        if response.status_code == 200:
            print("✅ Server is running\n")
        else:
            print("⚠️  Server responded but with unexpected status\n")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running!")
        print(f"   Start it with: cd VoicechefBE && uvicorn app.main:app --reload --port 8000\n")
        return
    
    # Test 1: Start a recipe (should generate intro TTS message)
    print("📝 Test 1: Recipe Introduction Message")
    print("-" * 60)
    try:
        response = requests.post(
            f"{API_URL}/start_recipe",
            json={"user_message": "I want to cook pasta carbonara"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            tts_message = data.get('tts_message', '')
            session_id = data.get('session_id', '')
            
            print(f"✅ Recipe created!")
            print(f"   Session ID: {session_id}")
            print(f"   TTS Message: {tts_message}\n")
            
            # Test 2: Interpret a command (should generate step TTS message)
            print("📝 Test 2: Step-by-Step Instruction Message")
            print("-" * 60)
            
            response = requests.post(
                f"{API_URL}/interpret",
                json={
                    "session_id": session_id,
                    "user_message": "next"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                tts_message = data.get('tts_message', '')
                action = data.get('action', '')
                
                print(f"✅ Command interpreted!")
                print(f"   Action: {action}")
                print(f"   TTS Message: {tts_message}\n")
                
                # Test 3: Question (should generate answer TTS message)
                print("📝 Test 3: Question Answering Message")
                print("-" * 60)
                
                response = requests.post(
                    f"{API_URL}/interpret",
                    json={
                        "session_id": session_id,
                        "user_message": "How hot should the water be?"
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    tts_message = data.get('tts_message', '')
                    
                    print(f"✅ Question answered!")
                    print(f"   TTS Message: {tts_message}\n")
                    
                    return tts_message
                else:
                    print(f"❌ Error: {response.status_code}")
                    print(f"   {response.text}\n")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   {response.text}\n")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}\n")
    
    except Exception as e:
        print(f"❌ Error: {e}\n")
    
    return None


def play_audio_pyttsx3(text):
    """Play text as speech using pyttsx3."""
    try:
        import pyttsx3
        
        print("🔊 Playing audio with pyttsx3...")
        print(f"   Text: {text[:100]}...\n")
        
        engine = pyttsx3.init()
        
        # Try to set English voice
        voices = engine.getProperty("voices")
        for v in voices:
            if "English" in v.name or "en-" in v.id.lower():
                engine.setProperty("voice", v.id)
                break
        
        # Set speech rate (words per minute)
        engine.setProperty("rate", 150)
        
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        
        print("✅ Audio playback complete!\n")
    
    except ImportError:
        print("⚠️  pyttsx3 not installed. Install with: pip install pyttsx3")
    except Exception as e:
        print(f"❌ Error playing audio: {e}")


def test_custom_text(text):
    """Test TTS with custom text."""
    print("=" * 60)
    print("🔊 Testing Custom TTS Text")
    print("=" * 60)
    print(f"📝 Text: {text}\n")
    
    # Just test pyttsx3 with custom text
    if "--play" in sys.argv or "-p" in sys.argv:
        play_audio_pyttsx3(text)
    else:
        print("💡 Tip: Use --play flag to hear the audio:")
        print("   python3 test_tts.py --play")


def main():
    """Main test function."""
    # Check for custom text argument
    custom_text = None
    for arg in sys.argv[1:]:
        if arg not in ["--play", "-p"] and not arg.startswith("-"):
            custom_text = arg
            break
    
    if custom_text:
        test_custom_text(custom_text)
    else:
        # Test full flow
        tts_message = test_text_generation()
        
        # Optionally play audio
        if tts_message and ("--play" in sys.argv or "-p" in sys.argv):
            print("=" * 60)
            play_audio_pyttsx3(tts_message)
        
        if not ("--play" in sys.argv or "-p" in sys.argv):
            print("💡 Tip: Use --play flag to hear the TTS audio:")
            print("   python3 test_tts.py --play")


if __name__ == "__main__":
    main()


