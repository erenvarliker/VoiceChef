"""Cooking coach service for interpreting user commands during cooking."""

import re
import uuid
import json
from datetime import datetime
from groq import Groq
from app.config import get_settings
from app.state import Session, Timer
from app.schemas import ActionType, StepData, TimerData


VOICE_CHEF_SYSTEM = """
You are Voice Chef, a friendly cooking and kitchen assistant running inside a HoloLens app.
The user is speaking in English. You must:
- Help with cooking, kitchen tasks, food questions, and simple smalltalk if needed.
- When the user asks for actions like "set a timer", "start a timer", "remind me", etc.,
  you must emit a structured action so the HoloLens app can react.

You MUST respond as a single JSON object with this exact schema:
{
  "assistant_role": "voice_chef",
  "response_text": "What you will say out loud to the user in English.",
  "actions": [
    {
      "type": "string, e.g. 'set_timer'",
      "parameters": {
        "duration_seconds": number (integer, optional, only for timers),
        "raw_text": "original user intent or extra info if needed"
      }
    }
  ]
}

Rules:
- Always include "assistant_role" and set it to "voice_chef".
- Always include "response_text" as a natural English sentence.
- Always include "actions" as an array (use [] if no action).
- For a timer request like "set a timer for 5 minutes", add ONE action:
  {
    "type": "set_timer",
    "parameters": {
      "duration_seconds": 300,
      "raw_text": "set a timer for 5 minutes"
    }
  }
- Do NOT include any explanation, comments, markdown, or code fences.
- Output MUST be valid JSON ONLY.
"""

INTENT_CLASSIFIER_SYSTEM = """
You are an intent classifier for a voice-controlled cooking assistant.
Your task is to look ONLY at the latest user message and classify it into ONE of these intents:

- NEXT: user wants to move to the next recipe step (e.g. "next", "continue", "I'm done").
- REPEAT: user wants to hear the current step again.
- TIMER: user wants to set or adjust a timer (e.g. "set a timer for 5 minutes").
- PAUSE: user wants to pause the cooking flow.
- RESUME: user wants to resume after a pause.
- QUESTION: user is asking a cooking-related question or for clarification.
- EMERGENCY: user mentions injury, danger, or urgent safety issue (e.g. "I burned my hand").
- UNKNOWN: anything else that does not clearly match the above.

Respond ONLY with a single JSON object in this schema:
{
  "intent": "ONE OF: NEXT | REPEAT | TIMER | PAUSE | RESUME | QUESTION | EMERGENCY | UNKNOWN",
  "reason": "short natural language explanation of why you chose this intent"
}

Do NOT include any extra keys, comments, markdown, or text outside the JSON.
"""


class CookingCoach:
    """Interprets user commands and manages cooking session state."""
    
    def __init__(self):
        settings = get_settings()
        # Prefer Groq, fall back to OpenAI config if needed
        api_key = settings.groq_api_key or settings.openai_api_key
        model = settings.groq_model or settings.openai_model

        self.client = Groq(api_key=api_key) if api_key else None
        self.model = model
    
    def interpret_command(self, session: Session, user_message: str) -> dict:
        """
        Interpret user command and return appropriate action.
        
        Args:
            session: Current cooking session
            user_message: User's spoken command from Unity
        
        Returns:
            dict: Response data for Unity
        """
        # Detect intent (LLM-based with fallback)
        intent = self._detect_intent_llm(user_message)
        
        # Handle based on intent
        if intent == "next":
            return self._handle_next_step(session)
        elif intent == "repeat":
            return self._handle_repeat_step(session)
        elif intent == "timer":
            return self._handle_timer_command(session, user_message)
        elif intent == "pause":
            return self._handle_pause(session)
        elif intent == "resume":
            return self._handle_resume(session)
        elif intent == "question":
            return self._handle_question(session, user_message)
        elif intent == "emergency":
            return self._handle_emergency(session, user_message)
        else:
            return self._handle_unclear(session, user_message)
    
    def _detect_intent(self, user_message: str) -> str:
        """
        Detect user intent from message.
        
        Returns:
            str: Intent type (next, repeat, timer, pause, resume, question, unclear)
        """
        msg_lower = user_message.lower().strip()
        
        # Next step
        if any(word in msg_lower for word in ["next", "continue", "done", "ready", "ok", "finished"]):
            return "next"
        
        # Repeat
        if any(word in msg_lower for word in ["repeat", "again", "what was that", "say that again"]):
            return "repeat"
        
        # Timer
        if any(word in msg_lower for word in ["timer", "set timer", "alarm", "remind"]):
            return "timer"
        
        # Pause
        if any(word in msg_lower for word in ["pause", "wait", "stop", "hold"]):
            return "pause"
        
        # Resume
        if any(word in msg_lower for word in ["resume", "start again", "continue"]):
            return "resume"
        
        # Question (has question words or ends with ?)
        if any(word in msg_lower for word in ["how", "why", "what", "when", "can i", "should i", "is it"]) or "?" in msg_lower:
            return "question"
        
        return "unclear"

    def _detect_intent_llm(self, user_message: str) -> str:
        """
        LLM-based intent classification with fallback to simple keyword rules.
        Returns: "next", "repeat", "timer", "pause", "resume", "question", "emergency", or "unclear".
        """
        # If no LLM client is configured, fall back immediately
        if not self.client:
            return self._detect_intent(user_message)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": INTENT_CLASSIFIER_SYSTEM},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.0,
                max_tokens=150,
            )
            raw = response.choices[0].message.content.strip()
            print("RAW GPT OUTPUT (intent classifier):", raw)
            data = json.loads(raw)
            intent_label = data.get("intent", "UNKNOWN").upper().strip()
        except Exception as e:
            print("[CookingCoach] Error in _detect_intent_llm, falling back:", repr(e))
            return self._detect_intent(user_message)

        mapping = {
            "NEXT": "next",
            "REPEAT": "repeat",
            "TIMER": "timer",
            "PAUSE": "pause",
            "RESUME": "resume",
            "QUESTION": "question",
            "EMERGENCY": "emergency",
            "UNKNOWN": "unclear",
        }
        return mapping.get(intent_label, "unclear")
    
    def _handle_next_step(self, session: Session) -> dict:
        """Handle moving to next step."""
        # Check if already complete
        if session.current_step_index >= len(session.recipe.steps):
            return {
                "action": ActionType.RECIPE_COMPLETE,
                "tts_message": f"Congratulations! You've completed the {session.recipe.dish_name}. Enjoy your meal!",
                "recipe_complete": True
            }
        
        # Move to next step
        session.current_step_index += 1
        
        # Check if now complete
        if session.current_step_index >= len(session.recipe.steps):
            return {
                "action": ActionType.RECIPE_COMPLETE,
                "tts_message": f"Congratulations! You've completed the {session.recipe.dish_name}. Enjoy your meal!",
                "recipe_complete": True
            }
        
        # Get current step
        step = session.recipe.steps[session.current_step_index]
        
        # Build TTS message
        tts_msg = f"Step {step.step_number}: {step.instruction}"
        if step.estimated_time:
            tts_msg += f". This should take about {step.estimated_time}"
        if step.safety_confirmation:
            tts_msg += f". {step.safety_confirmation}"
        
        return {
            "action": ActionType.NEXT_STEP,
            "current_step": session.current_step_index + 1,
            "total_steps": len(session.recipe.steps),
            "step_data": StepData(
                step_number=step.step_number,
                instruction=step.instruction,
                estimated_time=step.estimated_time,
                requires_heat=step.requires_heat,
                requires_knife=step.requires_knife,
                safety_confirmation=step.safety_confirmation
            ),
            "tts_message": tts_msg,
            "recipe_complete": False
        }
    
    def _handle_repeat_step(self, session: Session) -> dict:
        """Handle repeating current step."""
        # Check if we've started
        if session.current_step_index < 0 or session.current_step_index >= len(session.recipe.steps):
            return {
                "action": ActionType.REPEAT_STEP,
                "tts_message": "We haven't started cooking yet. Say 'next' to begin the first step!",
                "recipe_complete": False
            }
        
        # Get current step
        step = session.recipe.steps[session.current_step_index]
        
        tts_msg = f"Sure! Step {step.step_number}: {step.instruction}"
        if step.estimated_time:
            tts_msg += f". This should take about {step.estimated_time}"
        
        return {
            "action": ActionType.REPEAT_STEP,
            "current_step": session.current_step_index + 1,
            "total_steps": len(session.recipe.steps),
            "step_data": StepData(
                step_number=step.step_number,
                instruction=step.instruction,
                estimated_time=step.estimated_time,
                requires_heat=step.requires_heat,
                requires_knife=step.requires_knife,
                safety_confirmation=step.safety_confirmation
            ),
            "tts_message": tts_msg,
            "recipe_complete": False
        }
    
    def _handle_timer_command(self, session: Session, user_message: str) -> dict:
        """Handle timer-related commands."""
        # Extract duration from message
        duration_seconds = self._extract_timer_duration(user_message)
        
        if duration_seconds is None:
            return {
                "action": ActionType.ERROR,
                "tts_message": "I didn't understand the timer duration. Try saying 'set timer for 3 minutes'.",
                "recipe_complete": False
            }
        
        # Create timer
        timer_id = str(uuid.uuid4())
        timer = Timer(
            timer_id=timer_id,
            duration_seconds=duration_seconds,
            started_at=datetime.utcnow()
        )
        session.timers.append(timer)
        
        # Format duration for TTS
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        duration_str = ""
        if minutes > 0:
            duration_str += f"{minutes} minute{'s' if minutes > 1 else ''}"
        if seconds > 0:
            if minutes > 0:
                duration_str += " and "
            duration_str += f"{seconds} second{'s' if seconds > 1 else ''}"
        
        return {
            "action": ActionType.TIMER_SET,
            "current_step": session.current_step_index + 1 if session.current_step_index >= 0 else 0,
            "total_steps": len(session.recipe.steps),
            "timer_data": TimerData(
                timer_id=timer_id,
                duration_seconds=duration_seconds,
                started_at=timer.started_at.isoformat()
            ),
            "tts_message": f"Timer set for {duration_str}. I'll let you know when it's done!",
            "recipe_complete": False
        }
    
    def _extract_timer_duration(self, message: str) -> int:
        """
        Extract timer duration in seconds from user message.
        
        Returns:
            int: Duration in seconds, or None if not found
        """
        msg_lower = message.lower()
        
        # Pattern: "X minutes Y seconds"
        minutes = 0
        seconds = 0
        
        # Extract minutes
        minute_match = re.search(r'(\d+)\s*minute', msg_lower)
        if minute_match:
            minutes = int(minute_match.group(1))
        
        # Extract seconds
        second_match = re.search(r'(\d+)\s*second', msg_lower)
        if second_match:
            seconds = int(second_match.group(1))
        
        # If no minutes/seconds found, look for just a number
        if minutes == 0 and seconds == 0:
            number_match = re.search(r'(\d+)', msg_lower)
            if number_match:
                # Assume minutes if no unit specified
                minutes = int(number_match.group(1))
        
        total_seconds = (minutes * 60) + seconds
        return total_seconds if total_seconds > 0 else None
    
    def _handle_pause(self, session: Session) -> dict:
        """Handle pause command."""
        session.is_paused = True
        return {
            "action": ActionType.PAUSE,
            "tts_message": "Okay, I've paused. Say 'resume' or 'continue' when you're ready to continue.",
            "recipe_complete": False
        }
    
    def _handle_resume(self, session: Session) -> dict:
        """Handle resume command."""
        session.is_paused = False
        
        if session.current_step_index < 0 or session.current_step_index >= len(session.recipe.steps):
            tts_msg = "Welcome back! Say 'next' to start the first step."
        else:
            step = session.recipe.steps[session.current_step_index]
            tts_msg = f"Welcome back! We're on step {step.step_number}: {step.instruction}"
        
        return {
            "action": ActionType.RESUME,
            "tts_message": tts_msg,
            "recipe_complete": False
        }
    
    def _handle_question(self, session: Session, question: str) -> dict:
        """Handle user questions using structured JSON actions via LLM."""
        actions_data = self._ask_gpt_structured(question)
        answer = actions_data.get("response_text", "I'm having trouble answering right now.")
        actions = actions_data.get("actions", [])

        return {
            "action": ActionType.ANSWER_QUESTION,
            "current_step": session.current_step_index + 1 if session.current_step_index >= 0 else 0,
            "total_steps": len(session.recipe.steps),
            "tts_message": answer,
            "actions": actions,
            "recipe_complete": False
        }
    
    def _handle_unclear(self, session: Session, user_message: str) -> dict:
        """Handle unclear commands."""
        return {
            "action": ActionType.ERROR,
            "tts_message": """I'm not sure what you want me to do. You can say:
'next' to move to the next step,
'repeat' to hear the current step again,
'set timer for X minutes' to start a timer,
or ask me a question about the recipe.""",
            "recipe_complete": False
        }

    def _handle_emergency(self, session: Session, user_message: str) -> dict:
        """Handle emergency situations (e.g., user burned their hand)."""
        # Pause the cooking flow so nothing progresses silently
        session.is_paused = True

        # Let the LLM generate a calm, supportive response + optional actions
        actions_data = self._ask_gpt_structured(user_message)
        answer = actions_data.get(
            "response_text",
            "It sounds like you may be hurt. Please stop cooking and take care of your hand. If needed, seek medical help."
        )
        actions = actions_data.get("actions", []) or []

        # Ensure there is at least one explicit warning action for Unity
        has_warning = any(a.get("type") == "show_warning" for a in actions)
        if not has_warning:
            actions.append(
                {
                    "type": "show_warning",
                    "parameters": {
                        "severity": "high",
                        "raw_text": user_message,
                    },
                }
            )

        return {
            "action": ActionType.EMERGENCY,
            "current_step": session.current_step_index + 1 if session.current_step_index >= 0 else 0,
            "total_steps": len(session.recipe.steps),
            "tts_message": answer,
            "actions": actions,
            "recipe_complete": False,
        }

    def _ask_gpt_structured(self, user_text: str) -> dict:
        """Call LLM and parse its JSON response into a Python dict."""
        if not self.client:
            # If no LLM client configured, just echo back plain text with no actions
            return {
                "assistant_role": "voice_chef",
                "response_text": user_text,
                "actions": [],
            }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": VOICE_CHEF_SYSTEM},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.6,
                max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()
            print("RAW GPT OUTPUT (structured actions):", raw)
            data = json.loads(raw)
        except Exception as e:
            print("[CookingCoach] Error in _ask_gpt_structured:", repr(e))
            # Fallback: no structured actions
            data = {
                "assistant_role": "voice_chef",
                "response_text": user_text,
                "actions": [],
            }
        return data
