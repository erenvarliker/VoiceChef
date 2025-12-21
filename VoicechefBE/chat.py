#!/usr/bin/env python3
"""
Direct terminal chat with VoiceChef.
Just talk naturally - no commands needed!
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"
session_id = None
recipe_started = False

def check_server():
    """Check if server is running."""
    try:
        r = requests.get(f"{BASE_URL}/", timeout=2)
        return r.status_code == 200
    except:
        return False

def start_recipe(message):
    """Start a recipe."""
    global session_id, recipe_started
    try:
        r = requests.post(f"{BASE_URL}/start_recipe", json={"user_message": message})
        data = r.json()
        session_id = data["session_id"]
        recipe_started = True
        
        recipe = data['recipe']
        print(f"\n🍳 {recipe['dish_name'].upper()}")
        print(f"📋 {recipe['total_steps']} steps")
        
        # Show ingredients
        if recipe.get('ingredients'):
            print(f"\n📦 Ingredients:")
            for ing in recipe['ingredients']:
                print(f"   • {ing}")
        
        # Calculate and show total time
        total_min = 0
        for step in recipe.get('steps', []):
            if step.get('estimated_time'):
                import re
                time_str = step['estimated_time'].lower()
                mins = re.search(r'(\d+)\s*minute', time_str)
                secs = re.search(r'(\d+)\s*second', time_str)
                if mins:
                    total_min += int(mins.group(1))
                if secs:
                    total_min += int(secs.group(1)) / 60
        if total_min > 0:
            print(f"\n⏱️  Total time: ~{int(total_min)} minutes")
        
        print(f"\n💬 Chef: {data['tts_message']}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")

def talk_to_chef(message):
    """Send message to chef."""
    global session_id
    if not session_id:
        # Try to start recipe
        if any(word in message.lower() for word in ["cook", "make", "prepare", "recipe", "want"]):
            start_recipe(message)
        else:
            print("💬 Chef: Hi! What would you like to cook today?\n")
        return
    
    try:
        r = requests.post(f"{BASE_URL}/interpret", json={"session_id": session_id, "user_message": message})
        data = r.json()
        
        # Show step info if available
        if data.get("step_data"):
            step = data["step_data"]
            print(f"📝 Step {data.get('current_step', '?')}/{data.get('total_steps', '?')}: {step.get('instruction', '')}")
        
        # Show timer if set
        if data.get("timer_data"):
            timer = data["timer_data"]
            secs = timer.get("duration_seconds", 0)
            mins = secs // 60
            print(f"⏰ Timer: {mins} minutes")
        
        # Show chef's response
        print(f"💬 Chef: {data['tts_message']}\n")
        
        if data.get("recipe_complete"):
            print("🎉 Recipe complete! Great job!\n")
            session_id = None
            recipe_started = False
            
    except Exception as e:
        print(f"❌ Error: {e}\n")

# Main chat loop
print("\n" + "="*50)
print("🍳 VoiceChef - Terminal Chat")
print("="*50)
print("\n💬 Chef: Hi! I'm your cooking assistant. What would you like to cook?\n")

if not check_server():
    print("❌ Server not running! Start it with:")
    print("   cd VoicechefBE && uvicorn app.main:app --reload --port 8000\n")
    sys.exit(1)

while True:
    try:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ["quit", "exit", "bye", "q"]:
            print("\n💬 Chef: Goodbye! Happy cooking! 👋\n")
            break
        talk_to_chef(user_input)
    except KeyboardInterrupt:
        print("\n\n💬 Chef: Goodbye! 👋\n")
        break
    except EOFError:
        print("\n\n💬 Chef: Goodbye! 👋\n")
        break

