#!/usr/bin/env python3
"""
Interactive VoiceChef Conversation Test

Full conversation loop:
1. Record audio (STT)
2. Transcribe with Whisper
3. Send to backend
4. Get chef's response
5. Play TTS audio
6. Repeat until user quits

Usage:
    python3 interactive_conversation.py
"""

import sys
import requests
import tempfile
import os
import wave
import struct
import math
import subprocess
import platform

try:
    import pyaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("❌ pyaudio not installed. Install with: pip install pyaudio")

# Configuration
API_URL = "http://localhost:8000"
RECORDING_DURATION = 5  # seconds


def print_header():
    """Print welcome header."""
    print("=" * 70)
    print("🎤👨‍🍳 VoiceChef Interactive Conversation Test")
    print("=" * 70)
    print("\nThis will test the full conversation flow:")
    print("  1. Record your voice (STT)")
    print("  2. Transcribe with Whisper")
    print("  3. Send to backend")
    print("  4. Get chef's response")
    print("  5. Play TTS audio")
    print("  6. Repeat until you quit")
    print("\nCommands:")
    print("  - Press Enter to record")
    print("  - Type 'quit' or 'exit' to stop")
    print("  - Type 'skip' to skip TTS playback")
    print("=" * 70)
    print()


def check_backend():
    """Check if backend is available."""
    try:
        response = requests.get(f"{API_URL}/", timeout=2)
        if response.status_code == 200:
            print("✅ Backend is available\n")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}\n")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to backend: {e}")
        print(f"   Make sure backend is running: uvicorn app.main:app --reload --port 8000\n")
        return False


def record_audio(duration=RECORDING_DURATION):
    """Record audio from microphone."""
    if not AUDIO_AVAILABLE:
        print("❌ Cannot record: pyaudio not available")
        return None
    
    print(f"🎤 Recording for {duration} seconds...")
    print("   SPEAK CLEARLY AND LOUDLY!\n")
    
    audio = pyaudio.PyAudio()
    sample_rate = 16000
    channels = 1
    chunk = 1024
    
    try:
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk
        )
        
        frames = []
        print("🔴 RECORDING NOW - SPEAK!\n")
        for _ in range(0, int(sample_rate / chunk * duration)):
            data = stream.read(chunk, exception_on_overflow=False)
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
        
        # Analyze audio levels
        file_size = os.path.getsize(temp_path)
        with wave.open(temp_path, 'rb') as wf:
            frames_data = wf.readframes(wf.getnframes())
            audio_data = struct.unpack(f'<{len(frames_data)//2}h', frames_data)
            rms = math.sqrt(sum(x*x for x in audio_data) / len(audio_data))
            max_amp = max(abs(x) for x in audio_data)
            
            print(f"✅ Audio saved ({file_size} bytes)")
            print(f"   Audio levels: RMS={rms:.0f}, Max={max_amp}")
            
            if rms < 1000:
                print("⚠️  Warning: Audio seems quiet - speak louder next time")
        
        return temp_path
    
    except Exception as e:
        print(f"❌ Recording error: {e}")
        audio.terminate()
        return None


def transcribe_audio(audio_path):
    """Transcribe audio using backend."""
    print(f"\n📤 Transcribing audio...")
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'audio_file': ('audio.wav', f, 'audio/wav')}
            response = requests.post(f"{API_URL}/transcribe", files=files, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            text = data.get('text', '').strip()
            lang = data.get('language', '')
            
            if not text or len(text) < 2:
                print("⚠️  Transcription is empty or too short")
                return None
            
            print(f"✅ Transcribed: '{text}'")
            if lang:
                print(f"   Language: {lang}")
            
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


def start_recipe(user_message):
    """Start a new recipe."""
    print(f"\n📝 Starting recipe with: '{user_message}'")
    
    try:
        response = requests.post(
            f"{API_URL}/start_recipe",
            json={"user_message": user_message},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            recipe = data.get('recipe', {})
            tts_message = data.get('tts_message', '')
            
            print(f"✅ Recipe created!")
            print(f"   Session ID: {session_id}")
            print(f"   Dish: {recipe.get('dish_name', 'Unknown')}")
            print(f"   Steps: {recipe.get('total_steps', 0)}")
            print(f"   Ingredients: {len(recipe.get('ingredients', []))}")
            
            if recipe.get('ingredients'):
                print(f"\n📋 Ingredients:")
                for ing in recipe['ingredients']:
                    print(f"   - {ing}")
            
            return session_id, tts_message
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   {error_detail}")
            except:
                print(f"   {response.text}")
            return None, None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None


def interpret_command(session_id, user_message):
    """Interpret user command."""
    print(f"\n💬 Interpreting: '{user_message}'")
    
    try:
        response = requests.post(
            f"{API_URL}/interpret",
            json={
                "session_id": session_id,
                "user_message": user_message
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            action = data.get('action', '')
            tts_message = data.get('tts_message', '')
            current_step = data.get('current_step')
            total_steps = data.get('total_steps')
            step_data = data.get('step_data')
            recipe_complete = data.get('recipe_complete', False)
            
            print(f"✅ Command processed!")
            print(f"   Action: {action}")
            
            if current_step and total_steps:
                print(f"   Step: {current_step}/{total_steps}")
            
            if step_data:
                print(f"   Instruction: {step_data.get('instruction', '')}")
                if step_data.get('estimated_time'):
                    print(f"   Time: {step_data.get('estimated_time')}")
            
            if recipe_complete:
                print(f"   🎉 Recipe complete!")
            
            return tts_message
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   {error_detail}")
            except:
                print(f"   {response.text}")
            return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def play_tts(text, skip=False):
    """Play TTS audio."""
    if skip:
        print("\n⏭️  Skipping TTS playback")
        return
    
    if not text:
        print("\n⚠️  No TTS message to play")
        return
    
    print(f"\n🔊 Playing chef's response...")
    print(f"💬 Chef: {text}\n")
    
    # Use macOS 'say' command (works reliably)
    if platform.system() == "Darwin":
        try:
            # Clean text for command line (remove emojis and special chars)
            clean_text = text.encode('ascii', 'ignore').decode('ascii')
            subprocess.run(['say', clean_text], check=True)
            print("✅ Audio playback complete!\n")
        except subprocess.CalledProcessError:
            print("⚠️  TTS playback failed")
        except Exception as e:
            print(f"⚠️  Error playing audio: {e}")
    else:
        print("⚠️  TTS playback only supported on macOS (using 'say' command)")
        print("   Install pyttsx3 for other platforms")


def main():
    """Main conversation loop."""
    print_header()
    
    # Check backend
    if not check_backend():
        return
    
    # Check audio
    if not AUDIO_AVAILABLE:
        print("❌ Cannot proceed without pyaudio")
        print("   Install with: pip install pyaudio")
        return
    
    session_id = None
    conversation_count = 0
    
    print("Ready to start conversation!\n")
    print("Press Enter to record, or type 'quit' to exit\n")
    
    while True:
        try:
            # Get user input
            user_input = input("🎤 Press Enter to record (or 'quit'/'exit' to stop, 'skip' to skip TTS): ").strip().lower()
            
            if user_input in ['quit', 'exit', 'q']:
                print("\n👋 Ending conversation. Goodbye!")
                break
            
            skip_tts = (user_input == 'skip')
            
            # Record audio
            audio_path = record_audio()
            if not audio_path:
                print("❌ Recording failed. Try again.\n")
                continue
            
            # Transcribe
            transcribed_text = transcribe_audio(audio_path)
            
            # Clean up audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            if not transcribed_text:
                print("❌ Transcription failed. Try again.\n")
                continue
            
            # Check for quit commands in transcription
            if transcribed_text.lower() in ['quit', 'exit', 'stop', 'end']:
                print("\n👋 Ending conversation. Goodbye!")
                break
            
            conversation_count += 1
            print(f"\n{'='*70}")
            print(f"Conversation Turn #{conversation_count}")
            print(f"{'='*70}")
            
            # Send to backend
            if session_id is None:
                # Start new recipe
                new_session_id, tts_message = start_recipe(transcribed_text)
                if new_session_id:
                    session_id = new_session_id
                else:
                    print("❌ Failed to start recipe. Try again.\n")
                    continue
            else:
                # Interpret command
                tts_message = interpret_command(session_id, transcribed_text)
                if not tts_message:
                    print("❌ Failed to interpret command. Try again.\n")
                    continue
            
            # Play TTS
            play_tts(tts_message, skip=skip_tts)
            
            print(f"{'='*70}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print("   Continuing...\n")
            continue
    
    # Summary
    print(f"\n{'='*70}")
    print(f"Conversation Summary")
    print(f"{'='*70}")
    print(f"Total turns: {conversation_count}")
    if session_id:
        print(f"Session ID: {session_id}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

