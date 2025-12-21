#!/usr/bin/env python3
"""
Interactive test script for VoiceChef backend.
Simulates a conversation with the cooking assistant.
"""

import requests
import json
import sys
from typing import Optional

BASE_URL = "http://localhost:8000"

class VoiceChefClient:
    def __init__(self):
        self.session_id: Optional[str] = None
        self.recipe_started = False
    
    def check_health(self):
        """Check if server is running."""
        try:
            response = requests.get(f"{BASE_URL}/")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Connected to: {data['service']} v{data['version']}\n")
                return True
        except requests.exceptions.ConnectionError:
            print("❌ Error: Cannot connect to server!")
            print("   Make sure the server is running: uvicorn app.main:app --reload --port 8000\n")
            return False
        return False
    
    def start_recipe(self, user_message: str):
        """Start a new recipe."""
        try:
            response = requests.post(
                f"{BASE_URL}/start_recipe",
                json={"user_message": user_message}
            )
            response.raise_for_status()
            data = response.json()
            
            self.session_id = data["session_id"]
            self.recipe_started = True
            
            print(f"\n🍳 Recipe Created: {data['recipe']['dish_name']}")
            print(f"📋 Steps: {data['recipe']['total_steps']}")
            print(f"📦 Ingredients: {', '.join(data['recipe']['ingredients'][:3])}")
            if len(data['recipe']['ingredients']) > 3:
                print(f"   ... and {len(data['recipe']['ingredients']) - 3} more")
            
            print(f"\n💬 Voice Chef: {data['tts_message']}\n")
            return True
        except Exception as e:
            print(f"❌ Error creating recipe: {e}\n")
            return False
    
    def interpret_command(self, user_message: str):
        """Send a command to the cooking coach."""
        if not self.session_id:
            print("❌ No active session. Start a recipe first!\n")
            return
        
        try:
            response = requests.post(
                f"{BASE_URL}/interpret",
                json={
                    "session_id": self.session_id,
                    "user_message": user_message
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Display response
            action = data["action"]
            
            if action == "next_step":
                step = data.get("step_data", {})
                print(f"\n📝 Step {data.get('current_step')}/{data.get('total_steps')}: {step.get('instruction', 'N/A')}")
                if step.get('estimated_time'):
                    print(f"⏱️  Time: {step['estimated_time']}")
                if step.get('requires_heat'):
                    print("🔥 Requires heat")
                if step.get('requires_knife'):
                    print("🔪 Requires knife")
            
            elif action == "timer_set":
                timer = data.get("timer_data", {})
                duration = timer.get("duration_seconds", 0)
                minutes = duration // 60
                seconds = duration % 60
                print(f"\n⏰ Timer set: {minutes}m {seconds}s")
            
            elif action == "recipe_complete":
                print("\n🎉 Recipe Complete!")
            
            print(f"\n💬 Voice Chef: {data['tts_message']}\n")
            
            # Show session status
            if data.get("recipe_complete"):
                print("✅ You've finished the recipe! Great job!\n")
            
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    def show_status(self):
        """Show current session status."""
        if not self.session_id:
            print("❌ No active session.\n")
            return
        
        try:
            response = requests.get(f"{BASE_URL}/session/{self.session_id}/status")
            response.raise_for_status()
            data = response.json()
            
            print(f"\n📊 Session Status:")
            print(f"   Dish: {data['dish_name']}")
            print(f"   Step: {data['current_step_index'] + 1}/{data['total_steps']}")
            print(f"   Paused: {data['is_paused']}")
            print(f"   Timers: {data['active_timers']}")
            print(f"   Interactions: {data['total_interactions']}\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")


def print_help():
    """Print help message."""
    print("""
🎮 VoiceChef Interactive Test
============================

Commands:
  start <dish>     - Start a recipe (e.g., "start pasta carbonara")
  next             - Move to next step
  repeat           - Repeat current step
  timer <time>     - Set timer (e.g., "timer 5 minutes")
  pause            - Pause cooking
  resume           - Resume cooking
  status           - Show session status
  help             - Show this help
  quit/exit        - Exit

Or just type naturally:
  "I want to cook pasta"
  "next"
  "set timer for 3 minutes"
  "what should I do next?"
  
""")


def main():
    print("=" * 50)
    print("🍳 VoiceChef HoloGuide - Interactive Test")
    print("=" * 50)
    print()
    
    client = VoiceChefClient()
    
    # Check server
    if not client.check_health():
        sys.exit(1)
    
    print_help()
    
    # Main loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!\n")
                break
            
            elif user_input.lower() == "help":
                print_help()
                continue
            
            elif user_input.lower() == "status":
                client.show_status()
                continue
            
            # Check if starting a recipe
            if user_input.lower().startswith("start "):
                dish = user_input[6:].strip()
                if dish:
                    client.start_recipe(f"I want to cook {dish}")
                else:
                    print("❌ Please specify a dish: 'start pasta'\n")
                continue
            
            # If no recipe started, try to start one
            if not client.recipe_started:
                if any(word in user_input.lower() for word in ["cook", "make", "prepare", "recipe"]):
                    client.start_recipe(user_input)
                else:
                    print("💡 Tip: Start by saying what you want to cook (e.g., 'I want to cook pasta')\n")
                continue
            
            # Send command to backend
            client.interpret_command(user_input)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except EOFError:
            print("\n\n👋 Goodbye!\n")
            break


if __name__ == "__main__":
    main()


