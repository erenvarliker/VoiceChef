"""Tiny Python client that mimics Unity/HoloLens behavior (no speech).

Run this while the FastAPI server is running:

    uvicorn app.main:app --reload
    python client.py
"""

import sys
from typing import Optional

import requests


API_BASE_URL = "http://localhost:8000"


def start_recipe(user_message: str) -> Optional[str]:
    """Call /start_recipe and return session_id."""
    url = f"{API_BASE_URL}/start_recipe"
    payload = {"user_message": user_message, "session_id": None}

    try:
        resp = requests.post(url, json=payload, timeout=30)
    except Exception as e:
        print(f"[client] Network error when calling /start_recipe: {e}")
        return None

    if resp.status_code != 200:
        print(f"[client] /start_recipe failed ({resp.status_code}): {resp.text}")
        return None

    data = resp.json()
    session_id = data.get("session_id")

    print("\n=== START_RECIPE RESPONSE ===")
    print(f"session_id : {session_id}")
    print(f"action     : {data.get('action')}")
    print(f"dish_name  : {data.get('recipe', {}).get('dish_name')}")
    print(f"tts_message:\n{data.get('tts_message')}\n")

    # Show first few ingredients and steps
    recipe = data.get("recipe", {})
    ingredients = recipe.get("ingredients", [])
    steps = recipe.get("steps", [])

    if ingredients:
        print("Ingredients (first 4):")
        for ing in ingredients[:4]:
            print(f" - {ing}")
        if len(ingredients) > 4:
            print(f" ... (+{len(ingredients) - 4} more)")
        print()

    if steps:
        print("First step:")
        first = steps[0]
        print(f" Step {first.get('step_number')}: {first.get('instruction')}")
        if first.get("estimated_time"):
            print(f"  Estimated time: {first.get('estimated_time')}")
        if first.get("safety_confirmation"):
            print(f"  Safety: {first.get('safety_confirmation')}")
        print()

    return session_id


def interpret(session_id: str, user_message: str) -> bool:
    """Call /interpret and print the response. Returns False if session is gone."""
    url = f"{API_BASE_URL}/interpret"
    payload = {"session_id": session_id, "user_message": user_message}

    try:
        resp = requests.post(url, json=payload, timeout=30)
    except Exception as e:
        print(f"[client] Network error when calling /interpret: {e}")
        return True

    if resp.status_code == 404:
        print(f"[client] Session not found. Maybe it expired or server restarted.")
        return False

    if resp.status_code != 200:
        print(f"[client] /interpret failed ({resp.status_code}): {resp.text}")
        return True

    data = resp.json()

    print("\n=== INTERPRET RESPONSE ===")
    print(f"action      : {data.get('action')}")
    print(f"current_step: {data.get('current_step')}")
    print(f"total_steps : {data.get('total_steps')}")
    print(f"recipe_done : {data.get('recipe_complete')}")
    print(f"tts_message :\n{data.get('tts_message')}\n")

    step = data.get("step_data")
    if step:
        print("Step data:")
        print(f" Step {step.get('step_number')}: {step.get('instruction')}")
        if step.get("estimated_time"):
            print(f"  Estimated time: {step.get('estimated_time')}")
        if step.get("requires_heat"):
            print("  Requires heat: YES")
        if step.get("requires_knife"):
            print("  Requires knife: YES")
        if step.get("safety_confirmation"):
            print(f"  Safety: {step.get('safety_confirmation')}")
        print()

    timer = data.get("timer_data")
    if timer:
        print("Timer data:")
        print(
            f" timer_id : {timer.get('timer_id')}\n"
            f" duration : {timer.get('duration_seconds')} seconds\n"
            f" started_at: {timer.get('started_at')}"
        )
        print()

    return True


def main() -> None:
    print("VoiceChef HoloGuide - Tiny Python Client (Unity simulator)")
    print("Backend must be running at http://localhost:8000")
    print("Type 'quit' at any time to exit.\n")

    # 1) Start recipe
    user_message = input("Say something like 'I want to cook pasta': ").strip()
    if not user_message or user_message.lower() == "quit":
        print("Exiting.")
        return

    session_id = start_recipe(user_message)
    if not session_id:
        print("Could not start recipe. Exiting.")
        return

    # 2) Command loop
    print("Now you can type commands like: next, repeat, set timer for 3 minutes,")
    print("or ask questions like: can I use olive oil instead?\n")

    while True:
        cmd = input("You: ").strip()
        if not cmd:
            continue
        if cmd.lower() in {"quit", "exit"}:
            print("Goodbye.")
            break

        still_ok = interpret(session_id, cmd)
        if not still_ok:
            print("Session seems to be gone. Exiting.")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(0)





