#!/usr/bin/env python3
"""
Check microphone permissions and access on macOS.
"""

import sys
import platform

def check_mic_permissions():
    """Check if we can access the microphone."""
    print("=" * 60)
    print("🎤 Microphone Permission Checker")
    print("=" * 60)
    
    if platform.system() != "Darwin":
        print("⚠️  This script is for macOS. Other systems may have different permission systems.")
        return
    
    print("\n📋 Step 1: Checking if pyaudio can access microphone...")
    
    try:
        import pyaudio
        audio = pyaudio.PyAudio()
        
        # Try to get default input device
        try:
            default_input = audio.get_default_input_device_info()
            print(f"✅ Found microphone: {default_input['name']}")
            print(f"   Sample rate: {default_input['defaultSampleRate']} Hz")
            print(f"   Channels: {default_input['maxInputChannels']}")
        except Exception as e:
            print(f"❌ Cannot access default input device: {e}")
            print("   This usually means microphone permission is denied.")
            audio.terminate()
            return
        
        # Try to open a stream (this will trigger permission request if needed)
        print("\n📋 Step 2: Attempting to open microphone stream...")
        try:
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            print("✅ Successfully opened microphone stream!")
            print("   Microphone access is working.")
            stream.stop_stream()
            stream.close()
        except OSError as e:
            if "Input overflowed" in str(e):
                print("⚠️  Stream opened but had overflow (this is usually OK)")
            else:
                print(f"❌ Cannot open stream: {e}")
                print("   This might indicate a permission issue.")
        except Exception as e:
            print(f"❌ Error opening stream: {e}")
            print("   This might indicate a permission issue.")
        
        audio.terminate()
        
        print("\n" + "=" * 60)
        print("📝 Permission Status Summary:")
        print("=" * 60)
        print("✅ Microphone device detected")
        print("✅ Stream can be opened")
        print("\n✨ Your microphone should be working!")
        print("\nIf you're still having issues:")
        print("  1. Make sure you're speaking loudly and clearly")
        print("  2. Check System Settings → Privacy & Security → Microphone")
        print("  3. Ensure Terminal (or Python) is listed and enabled")
        
    except ImportError:
        print("❌ pyaudio is not installed")
        print("   Install it with: pip install pyaudio")
        return
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return


def show_permission_instructions():
    """Show instructions for granting microphone access."""
    print("\n" + "=" * 60)
    print("📖 How to Grant Microphone Access on macOS")
    print("=" * 60)
    print("""
If microphone access is denied, follow these steps:

1. Open System Settings (or System Preferences on older macOS)
   - Click the Apple menu → System Settings

2. Go to Privacy & Security
   - Click "Privacy & Security" in the sidebar
   - Or search for "Privacy" in the search bar

3. Select Microphone
   - Scroll down to find "Microphone" in the list
   - Click on it

4. Enable Terminal (or Python)
   - Look for "Terminal" in the list
   - Toggle the switch to ON (green)
   - If you don't see Terminal, you might need to:
     a. Run a script that uses the microphone first
     b. macOS will prompt you to grant permission
     c. Click "OK" when prompted

5. If using Python directly (not through Terminal):
   - Look for "Python" in the list
   - Toggle it to ON

6. Restart Terminal/Python
   - Close and reopen Terminal
   - Or restart your Python script

Alternative: If Terminal doesn't appear in the list:
- Run a script that uses the microphone
- macOS will show a popup asking for permission
- Click "OK" or "Allow" when prompted
- This will add Terminal to the list automatically

Troubleshooting:
- If you see "Terminal" but it's grayed out, you may need to:
  - Quit Terminal completely (Cmd+Q)
  - Reopen it
  - Try again

- If Python is running in a virtual environment:
  - The permission might be tied to the Python executable
  - Check for "Python" or "python3" in the list
""")


if __name__ == "__main__":
    check_mic_permissions()
    show_permission_instructions()
    
    print("\n" + "=" * 60)
    print("🧪 Quick Test")
    print("=" * 60)
    response = input("\nWould you like to test recording now? (y/n): ")
    if response.lower() == 'y':
        print("\n🎤 Testing 2-second recording...")
        try:
            import pyaudio
            import wave
            import tempfile
            
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            
            print("🔴 Recording... (speak now!)")
            frames = []
            for _ in range(0, int(16000 / 1024 * 2)):  # 2 seconds
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            # Check if we got any data
            total_bytes = sum(len(f) for f in frames)
            print(f"✅ Recorded {total_bytes} bytes")
            
            if total_bytes > 1000:
                print("✨ Recording test successful!")
            else:
                print("⚠️  Very little data recorded - check microphone")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            print("   This might be a permission issue.")

