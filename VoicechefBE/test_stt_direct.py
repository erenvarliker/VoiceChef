#!/usr/bin/env python3
"""
Direct STT test - records and shows detailed transcription info.

This helps diagnose transcription issues.
"""

import sys
import requests
import tempfile
import os
import wave
import struct
import math

try:
    import pyaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("❌ pyaudio not installed")

API_URL = "http://localhost:8000"


def record_audio(duration=5):
    """Record with detailed diagnostics."""
    if not AUDIO_AVAILABLE:
        return None
    
    print(f"🎤 Recording {duration} seconds...")
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
        
        # Save file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_path = temp_file.name
        temp_file.close()
        
        wf = wave.open(temp_path, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        # Analyze audio
        file_size = os.path.getsize(temp_path)
        print(f"✅ Saved: {file_size} bytes")
        
        with wave.open(temp_path, 'rb') as wf:
            frames_data = wf.readframes(wf.getnframes())
            audio_data = struct.unpack(f'<{len(frames_data)//2}h', frames_data)
            rms = math.sqrt(sum(x*x for x in audio_data) / len(audio_data))
            max_amp = max(abs(x) for x in audio_data)
            avg_amp = sum(abs(x) for x in audio_data) / len(audio_data)
            
            print(f"\n📊 Audio Analysis:")
            print(f"   Duration: {wf.getnframes() / wf.getframerate():.2f}s")
            print(f"   Sample rate: {wf.getframerate()} Hz")
            print(f"   Channels: {wf.getnchannels()}")
            print(f"   RMS level: {rms:.0f}")
            print(f"   Max amplitude: {max_amp}")
            print(f"   Avg amplitude: {avg_amp:.0f}")
            
            if rms < 500:
                print("\n⚠️  AUDIO IS TOO QUIET!")
                print("   - Speak MUCH louder")
                print("   - Get closer to microphone")
                print("   - Check mic volume in system settings")
            elif rms < 2000:
                print("\n⚠️  Audio is quiet - try speaking louder")
            else:
                print("\n✅ Audio levels look good")
        
        return temp_path
    
    except Exception as e:
        print(f"❌ Error: {e}")
        audio.terminate()
        return None


def transcribe(audio_path):
    """Transcribe with detailed output."""
    print(f"\n📤 Transcribing...")
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'audio_file': ('test.wav', f, 'audio/wav')}
            response = requests.post(f"{API_URL}/transcribe", files=files, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            text = data.get('text', '').strip()
            lang = data.get('language', '')
            
            print(f"\n📝 Transcription Result:")
            print(f"   Language: {lang}")
            print(f"   Text: '{text}'")
            
            if not text or len(text) < 3:
                print("\n❌ Transcription is too short or empty!")
                print("   This usually means:")
                print("   1. Audio was too quiet")
                print("   2. No speech detected")
                print("   3. Background noise")
                print("\n   Try:")
                print("   - Speaking louder and clearer")
                print("   - Recording in a quiet room")
                print("   - Getting closer to microphone")
            elif text.lower() in ['you', 'you.', 'you,']:
                print("\n⚠️  Only got 'you' - likely audio quality issue")
            else:
                print(f"\n✅ Got transcription: '{text}'")
            
            return text
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    print("=" * 60)
    print("🎤 Direct STT Diagnostic Test")
    print("=" * 60)
    
    # Check server
    try:
        requests.get(f"{API_URL}/", timeout=2)
        print("✅ Server is running\n")
    except:
        print("❌ Server not running!\n")
        return
    
    duration = 5
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except:
            pass
    
    print(f"Recording for {duration} seconds...")
    print("IMPORTANT: Speak clearly, loudly, and close to the microphone!\n")
    
    input("Press Enter to start recording...")
    
    audio_path = record_audio(duration)
    if audio_path:
        text = transcribe(audio_path)
        
        # Clean up
        if os.path.exists(audio_path):
            os.remove(audio_path)
        
        if text and len(text) > 3 and text.lower() not in ['you', 'you.', 'you,']:
            print("\n✨ Success! Transcription is working.")
        else:
            print("\n💡 Tips to improve:")
            print("   1. Speak louder and clearer")
            print("   2. Get closer to microphone")
            print("   3. Reduce background noise")
            print("   4. Try recording for 10 seconds")
            print("   5. Check macOS microphone permissions")


if __name__ == "__main__":
    main()


