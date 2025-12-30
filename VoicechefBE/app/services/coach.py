"""Cooking coach service for interpreting user commands during cooking."""

import re
import uuid
import json
from datetime import datetime
from app.config import get_settings
from app.state import Session, Timer
from app.schemas import ActionType, StepData, TimerData, RecipeStep

# Try to import Groq and OpenAI with fallback
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


VOICE_CHEF_SYSTEM = """
You are Voice Chef, a friendly, simple, and conversational cooking coach running inside a HoloLens AR app.
You guide users through cooking recipes step-by-step with detailed, helpful instructions.

Your personality:
- Warm, friendly, and encouraging (like a helpful friend in the kitchen)
- Use standard English grammar.
- Do NOT use slang, "cool" words, or casual fillers.
- Do NOT use emojis.
- Prioritize clarity and brevity over friendliness.
- Understand natural language and context - you don't need exact commands

When interacting with users:
- Be  natural (speak like you're right there with them)
- Understand their intent from natural language, not just keywords
- If they want to move forward, advance to the next step naturally
- If they're tired or need a break, pause empathetically
- If the user asks a question, answer factually and briefly.
- Keep responses concise but informative (2-3 sentences for TTS)

You MUST respond as a single JSON object with this exact schema:
{
  "assistant_role": "voice_chef",
  "response_text": "What you will say out loud to the user in English (conversational, detailed, helpful).",
  "action_type": "ONE OF: next_step | repeat_step | set_timer | pause | resume | answer_question | continue_conversation | recipe_complete",
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
- Always include "response_text" as natural, conversational English (2-4 sentences).
- Always include "action_type" to indicate what should happen in the system.
- Always include "actions" as an array (use [] if no structured action needed).
- For "next_step": user wants to advance to the next recipe step
- For "repeat_step": user wants to hear the current step again
- For "set_timer": user wants to set a timer (include duration_seconds in actions)
- For "pause": user wants to pause/take a break
- For "resume": user wants to resume after pausing
- For "answer_question": user asked a question, just answer it
- For "continue_conversation": natural conversation, no specific action needed
- For "recipe_complete": all steps are done
- Do NOT include any explanation, comments, markdown, or code fences.
- Output MUST be valid JSON ONLY.
"""

STEP_DETAILER_SYSTEM = """
You are a cooking coach breaking down recipe steps into detailed, conversational instructions.

Given a recipe step, create a detailed, step-by-step explanation that:
1. Explains what the user needs to do in clear, simple terms
2. Breaks down complex actions into smaller sub-steps
3. Provides helpful tips and context
4. Mentions what to look for or how to know when it's done
5. Is conversational and encouraging (like a friend helping in the kitchen)

Keep it concise but detailed (2-4 sentences). Make it natural for voice/TTS.

Respond ONLY with the detailed instruction text, nothing else. No JSON, no markdown, just the conversational instruction.
"""

INTENT_CLASSIFIER_SYSTEM = """
You are an intent classifier for a voice-controlled cooking assistant.
Your task is to look ONLY at the latest user message and classify it into ONE of these intents:

- NEXT: user wants to move to the next recipe step (e.g. "next", "continue", "I'm done", "ready", "finished").
- REPEAT: user wants to hear the current step again (e.g. "repeat", "say that again", "what was that").
- TIMER: user wants to set or adjust a timer (e.g. "set a timer for 5 minutes", "timer 3 minutes").
- PAUSE: user wants to pause, take a break, or rest (e.g. "pause", "wait", "I'm tired", "need a break", "hold on", "slow down").
- RESUME: user wants to resume after a pause (e.g. "resume", "continue", "ready to continue", "let's go").
- QUESTION: user is asking a cooking-related question or for clarification (e.g. "how do I...", "what should I...", "why...").
- EMERGENCY: user mentions injury, danger, or urgent safety issue (e.g. "I burned my hand", "I cut myself").
- UNKNOWN: anything else that does not clearly match the above.

IMPORTANT: Be generous with PAUSE intent - if user mentions being tired, needing a break, wanting to wait, or slowing down, classify as PAUSE.

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
        
        # Prefer Groq, fall back to OpenAI
        self.client = None
        self.model = None
        
        if GROQ_AVAILABLE and settings.groq_api_key:
            try:
                self.client = Groq(api_key=settings.groq_api_key)
                self.model = settings.groq_model
                print("[CookingCoach] Using Groq API")
            except Exception as e:
                print(f"[CookingCoach] Failed to initialize Groq: {e}")
        
        if self.client is None and OPENAI_AVAILABLE and settings.openai_api_key:
            try:
                self.client = OpenAI(api_key=settings.openai_api_key)
                self.model = settings.openai_model
                print("[CookingCoach] Using OpenAI API")
            except Exception as e:
                print(f"[CookingCoach] Failed to initialize OpenAI: {e}")
        
        if self.client is None:
            print("[CookingCoach] WARNING: No LLM client configured. Using fallback keyword matching.")
    
    def interpret_command(self, session: Session, user_message: str) -> dict:
        """
        Interpret user command using conversational LLM approach.
        This creates a natural flow instead of rigid keyword matching.
        
        Args:
            session: Current cooking session
            user_message: User's spoken command from Unity
        
        Returns:
            dict: Response data for Unity
        """
        # If no LLM, fall back to simple keyword matching
        if not self.client:
            return self._interpret_with_keywords(session, user_message)
        
        # Use LLM to understand context and respond naturally
        return self._interpret_conversational(session, user_message)
    
    def _interpret_conversational(self, session: Session, user_message: str) -> dict:
        """
        Use LLM to understand user intent in context and respond naturally.
        This creates a healthy conversational flow.
        """
        try:
            # ====================================================
            # 1. SAFETY OVERRIDE (NEW CODE)
            # Check this FIRST to guarantee warning triggers
            # ====================================================
            msg_lower = user_message.lower()
            if any(w in msg_lower for w in ["fire", "smoke", "cut", "bleed", "hurt", "injury", "emergency", "911"]):
                print("[CookingCoach] SAFETY OVERRIDE TRIGGERED")
                return self._handle_emergency(session, user_message)

            # ====================================================
            # 2. BUILD CONTEXT (YOUR ORIGINAL CODE)
            # ====================================================
            context = self._build_conversation_context(session)
            
            # Create prompt for natural understanding
            prompt = f"""{context}

User says: "{user_message}"

Understand what the user wants and respond naturally. Consider:
- Are they ready for the next step? (say "next", "done", "ready", "finished", "all set", etc.)
- Do they want to hear the current step again? (say "repeat", "what was that", "again", etc.)
- Do they need a timer? (mention "timer", "set timer", "remind me", etc.)
- Are they tired or need a break? (say "tired", "rest", "pause", "wait", "break", etc.)
- Are they ready to continue after a break? (say "resume", "continue", "ready", etc.)
- Are they asking a question? (questions, clarifications, "how", "what", "why", etc.)
- Is there an emergency? (injury, danger, "burned", "cut", etc.)
- Or are they just making conversation or comments?

Respond naturally and helpfully. If they want to advance, guide them to the next step. If they're tired, be empathetic and pause. If they ask questions, answer them. Be conversational, not robotic."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": VOICE_CHEF_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=400,
            )
            
            raw = response.choices[0].message.content.strip()
            print("RAW GPT OUTPUT (conversational):", raw)
            
            # Parse JSON response
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            
            data = json.loads(raw)
            response_text = data.get("response_text", "")
            action_type = data.get("action_type", "continue_conversation").lower()
            actions = data.get("actions", [])
            
            # Handle the action based on LLM's decision
            if action_type == "next_step":
                return self._handle_next_step(session, response_text)
            elif action_type == "repeat_step":
                return self._handle_repeat_step(session, response_text)
            elif action_type == "set_timer":
                # Extract timer from actions
                timer_action = next((a for a in actions if a.get("type") == "set_timer"), None)
                if timer_action:
                    duration = timer_action.get("parameters", {}).get("duration_seconds")
                    if duration:
                        return self._handle_timer_command(session, user_message, duration, response_text)
                # Fallback: try to extract from message
                return self._handle_timer_command(session, user_message, None, response_text)
            elif action_type == "pause":
                return self._handle_pause(session, response_text)
            elif action_type == "resume":
                return self._handle_resume(session, response_text)
            elif action_type == "emergency": # <--- NEW HANDLER
                return self._handle_emergency(session, user_message)
            elif action_type == "recipe_complete":
                return {
                    "action": ActionType.RECIPE_COMPLETE,
                    "tts_message": response_text or self._generate_completion_message(session),
                    "recipe_complete": True
                }
            elif action_type == "answer_question":
                return self._handle_question(session, user_message, response_text)
            else:  # continue_conversation or unknown
                # Check for emergency keywords (Backup check)
                if any(word in user_message.lower() for word in ["burned", "cut", "hurt", "injury", "emergency", "help"]):
                    return self._handle_emergency(session, user_message)
                # Otherwise, just continue conversation
                return {
                    "action": ActionType.ANSWER_QUESTION,
                    "tts_message": response_text or "I'm here to help! What would you like to do?",
                    "recipe_complete": False
                }
                
        except json.JSONDecodeError as e:
            print(f"[CookingCoach] JSON parse error in conversational mode: {repr(e)}")
            print(f"[CookingCoach] Raw output: {raw}")
            # Fallback to keyword matching
            return self._interpret_with_keywords(session, user_message)
        except Exception as e:
            print(f"[CookingCoach] Error in conversational mode: {repr(e)}")
            # Fallback to keyword matching
            return self._interpret_with_keywords(session, user_message)
    
    def _interpret_with_keywords(self, session: Session, user_message: str) -> dict:
        """Fallback: simple keyword-based interpretation when LLM is unavailable."""
        intent = self._detect_intent(user_message)
        
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
    
    def _build_conversation_context(self, session: Session) -> str:
        """Build rich context for conversational understanding."""
        context = f"We're cooking {session.recipe.dish_name}. "
        
        if session.is_paused:
            context += "The session is currently PAUSED. "
        
        if session.current_step_index < 0:
            context += "We haven't started the steps yet. "
        elif session.current_step_index >= len(session.recipe.steps):
            context += f"We've completed all {len(session.recipe.steps)} steps! "
        else:
            current_step = session.recipe.steps[session.current_step_index]
            context += f"We're currently on step {session.current_step_index + 1} of {len(session.recipe.steps)}: {current_step.instruction}. "
            
            if session.current_step_index > 0:
                prev_step = session.recipe.steps[session.current_step_index - 1]
                context += f"We just finished: {prev_step.instruction}. "
        
        if session.timers:
            context += f"There are {len(session.timers)} active timer(s). "
        
        return context
    
    def _detect_intent(self, user_message: str) -> str:
        """
        Detect user intent from message.
        
        Returns:
            str: Intent type (next, repeat, timer, pause, resume, question, unclear)
        """
        msg_lower = user_message.lower().strip()
        
        # Next step
        if any(word in msg_lower for word in ["next", "continue", "done", "ready", "ok", "finished", "completed", "all set"]):
            return "next"
        
        # Repeat
        if any(word in msg_lower for word in ["repeat", "again", "what was that", "say that again", "replay", "one more time"]):
            return "repeat"
        
        # Timer
        if any(word in msg_lower for word in ["timer", "set timer", "alarm", "remind", "countdown"]):
            return "timer"
        
        # Pause - handle tired, need break, etc.
        if any(word in msg_lower for word in ["pause", "wait", "stop", "hold", "tired", "rest", "break", "need a break", 
                                               "take a break", "slow down", "hold on", "wait a minute", "give me a moment",
                                               "i need to rest", "i'm tired", "too tired", "exhausted"]):
            return "pause"
        
        # Resume
        if any(word in msg_lower for word in ["resume", "start again", "continue", "ready to continue", "let's continue", 
                                               "i'm ready", "back", "let's go", "proceed"]):
            return "resume"
        
        # Question (has question words or ends with ?)
        if any(word in msg_lower for word in ["how", "why", "what", "when", "can i", "should i", "is it", "do i", "will it"]) or "?" in msg_lower:
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
    
    # ... inside CookingCoach class ...

    def _handle_next_step(self, session: Session, custom_message: str = None) -> dict:
        """Handle moving to next step with detailed, conversational guidance + AUTO TIMER."""
        
        # 1. NEW: CLEAR SAFETY WARNINGS (So the red window disappears)
        session.active_warning = None
        session.is_paused = False

        # 1. NEW: Clear all previous timers when moving to a new step
        session.timers = []

        # 1. Check if recipe is already done
        if session.current_step_index >= len(session.recipe.steps):
             return {
                "action": ActionType.RECIPE_COMPLETE,
                "tts_message": self._generate_completion_message(session),
                "recipe_complete": True
            }

        # 2. Advance Step
        session.current_step_index += 1
        
        # 3. Check if we just finished
        if session.current_step_index >= len(session.recipe.steps):
            return {
                "action": ActionType.RECIPE_COMPLETE,
                "tts_message": self._generate_completion_message(session),
                "recipe_complete": True
            }
        
        # 4. Get the new step data
        step = session.recipe.steps[session.current_step_index]
        
        # 5. Generate the base instruction text
        if custom_message:
            # Use LLM's natural response, but enhance with step details
            detailed_instruction = custom_message
            if step.estimated_time and step.estimated_time not in detailed_instruction.lower():
                detailed_instruction += f" This should take about {step.estimated_time}."
        else:
            detailed_instruction = self._generate_detailed_step_instruction(
                session, step, session.current_step_index + 1, len(session.recipe.steps)
            )

        # ====================================================
        # NEW LOGIC: AUTO-START TIMER
        # ====================================================
        timer_data = None
        auto_timer_msg = ""
        
        # If the step has a time duration (e.g., "10 minutes"), start a timer automatically
        if step.estimated_time:
            seconds = self._parse_duration_from_text(step.estimated_time)
            
            # Only auto-start if it's a valid duration (e.g. > 10 seconds)
            if seconds > 10: 
                # Create the timer
                timer_id = str(uuid.uuid4())
                new_timer = Timer(
                    timer_id=timer_id,
                    duration_seconds=seconds,
                    started_at=datetime.utcnow()
                )
                session.timers.append(new_timer)
                
                # Create return data
                timer_data = TimerData(
                    timer_id=timer_id,
                    duration_seconds=seconds,
                    started_at=new_timer.started_at.isoformat()
                )
                
                # Append to speech so user knows
                auto_timer_msg = f" I've started a {step.estimated_time} timer for you."
                detailed_instruction += auto_timer_msg

        return {
            "action": ActionType.NEXT_STEP,
            "current_step": session.current_step_index + 1,
            "total_steps": len(session.recipe.steps),
            "step_data": StepData(
                step_number=step.step_number,
                title=step.title,
                instruction=step.instruction,
                estimated_time=step.estimated_time,
                requires_heat=step.requires_heat,
                requires_knife=step.requires_knife,
                safety_confirmation=step.safety_confirmation
            ),
            "tts_message": detailed_instruction,
            "timer_data": timer_data,  # Return the new timer immediately
            "recipe_complete": False
        }

    def _parse_duration_from_text(self, text: str) -> int:
        """Helper to parse '10 minutes' or '30 seconds' into int seconds."""
        if not text: return 0
        import re
        text = text.lower()
        
        minutes = 0
        seconds = 0
        
        # Regex for "X minutes"
        min_match = re.search(r'(\d+)\s*min', text)
        if min_match:
            minutes = int(min_match.group(1))
            
        # Regex for "X seconds"
        sec_match = re.search(r'(\d+)\s*sec', text)
        if sec_match:
            seconds = int(sec_match.group(1))
            
        return (minutes * 60) + seconds
    
    def _handle_repeat_step(self, session: Session, custom_message: str = None) -> dict:
        """Handle repeating current step with detailed explanation."""
        # 1. NEW: CLEAR SAFETY WARNINGS
        session.active_warning = None
        session.is_paused = False

        # Check if we've started
        if session.current_step_index < 0 or session.current_step_index >= len(session.recipe.steps):
            return {
                "action": ActionType.REPEAT_STEP,
                "tts_message": "We haven't started cooking yet. Say 'next' when you're ready to begin the first step!",
                "recipe_complete": False
            }
        
        # Get current step
        step = session.recipe.steps[session.current_step_index]
        
        # Generate detailed instruction again
        if custom_message:
            detailed_instruction = custom_message
        else:
            detailed_instruction = self._generate_detailed_step_instruction(
                session, step, session.current_step_index + 1, len(session.recipe.steps), is_repeat=True
            )
        
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
            "tts_message": detailed_instruction,
            "recipe_complete": False
        }
    
    def _handle_timer_command(self, session: Session, user_message: str, duration_seconds: int = None, custom_message: str = None) -> dict:
        """Handle timer-related commands."""


        # 1. NEW: CLEAR SAFETY WARNINGS
        session.active_warning = None
        session.is_paused = False

        # Extract duration from message if not provided
        if duration_seconds is None:
            duration_seconds = self._extract_timer_duration(user_message)
        
        if duration_seconds is None:
            return {
                "action": ActionType.ERROR,
                "tts_message": custom_message or "I didn't understand the timer duration. Try saying 'set timer for 3 minutes'.",
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
            "tts_message": custom_message or f"Timer set for {duration_str}. I'll let you know when it's done!",
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
    
    def _handle_pause(self, session: Session, custom_message: str = None) -> dict:
        """Handle pause command with empathetic, professional response."""
        session.is_paused = True
        
        if custom_message:
            pause_message = custom_message
            if "resume" not in pause_message.lower() and "continue" not in pause_message.lower():
                pause_message += " Just say 'resume' or 'continue' when you're ready!"
        else:
            # Fallback - more empathetic
            pause_message = "Of course! Take your time and rest. Cooking should be enjoyable, not rushed. When you're ready to continue, just say 'resume' or 'continue' and I'll be right here to help you finish. No rush at all!"
        
        return {
            "action": ActionType.PAUSE,
            "tts_message": pause_message,
            "recipe_complete": False
        }
    
    def _handle_resume(self, session: Session, custom_message: str = None) -> dict:
        """Handle resume command."""
        session.is_paused = False
        session.active_warning = None  # <--- NEW: Clear the warning
        
        if custom_message:
            tts_msg = custom_message
        elif session.current_step_index < 0 or session.current_step_index >= len(session.recipe.steps):
            tts_msg = "Welcome back! Say 'next' to start the first step."
        else:
            step = session.recipe.steps[session.current_step_index]
            tts_msg = f"Welcome back! We're on step {step.step_number}: {step.instruction}"
        
        return {
            "action": ActionType.RESUME,
            "tts_message": tts_msg,
            "recipe_complete": False
        }
    
    def _handle_question(self, session: Session, question: str, custom_message: str = None) -> dict:
        """Handle user questions with contextual, conversational answers."""
        if custom_message:
            answer = custom_message
            actions = []
        else:
            # Build context about current recipe and step
            context = self._build_question_context(session)
            
            # Generate contextual answer
            contextual_question = f"{context}\n\nUser asks: {question}"
            actions_data = self._ask_gpt_structured(contextual_question)
            answer = actions_data.get("response_text", "I'm having trouble answering right now. Could you rephrase that?")
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
        """Handle unclear commands with professional, helpful response."""
        if not self.client:
            # More conversational fallback
            return {
                "action": ActionType.ERROR,
                "tts_message": "I want to make sure I understand you correctly. You can say things like 'next' to move forward, 'repeat' to hear the step again, 'set timer for 5 minutes' to start a timer, or just ask me any question about what you're cooking. What would you like to do?",
                "recipe_complete": False
            }
        
        try:
            # Use LLM to understand and respond professionally
            context = ""
            if session.current_step_index >= 0 and session.current_step_index < len(session.recipe.steps):
                current_step = session.recipe.steps[session.current_step_index]
                context = f"We're cooking {session.recipe.dish_name} and currently on step {session.current_step_index + 1}. "
            
            prompt = f"""{context}The user said: "{user_message}"

This doesn't clearly match a standard command (next, repeat, timer, etc.), but it might be:
- A request to pause or take a break
- A question about cooking
- A statement about how they're feeling
- Something else entirely

Respond professionally and helpfully (2-3 sentences). Be understanding and guide them on what they can do. If it sounds like they need a break or are tired, suggest pausing. If it's a question, answer it. Be warm and supportive."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are Voice Chef, a professional and empathetic cooking coach. You understand natural language and help users even when they don't use exact commands. Be warm, understanding, and helpful."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=200,
            )
            
            helpful_response = response.choices[0].message.content.strip()
            
            return {
                "action": ActionType.ANSWER_QUESTION,  # Treat as helpful answer, not error
                "tts_message": helpful_response,
                "recipe_complete": False
            }
        except Exception as e:
            print(f"[CookingCoach] Error handling unclear command: {repr(e)}")
            # Fallback - more conversational
            return {
                "action": ActionType.ERROR,
                "tts_message": "I want to make sure I understand you correctly. You can say things like 'next' to move forward, 'repeat' to hear the step again, or 'set timer for 5 minutes' to start a timer. Or just tell me what you need - I'm here to help!",
                "recipe_complete": False
            }

    def _handle_emergency(self, session: Session, user_message: str) -> dict:
        """
        Handle emergency situations.
        1. Sets the visual warning flag immediately for Unity.
        2. Asks AI for specific medical/safety advice.
        """
        # Pause the cooking flow so nothing progresses silently
        session.is_paused = True

        # 1. IMMEDIATE VISUAL TRIGGER (For Unity)
        msg_lower = user_message.lower()
        if any(w in msg_lower for w in ["fire", "smoke", "burn"]):
            session.active_warning = "fire"
        elif any(w in msg_lower for w in ["cut", "bleed", "knife", "hurt"]):
            session.active_warning = "cut"
        else:
            session.active_warning = "general"

        # 2. INTELLIGENT ADVICE (The "Smart" part)
        # We still ask GPT so the user gets specific advice (e.g., "Run cold water on the burn")
        # instead of a generic hardcoded string.
        try:
            actions_data = self._ask_gpt_structured(user_message)
            answer = actions_data.get(
                "response_text",
                "Please stop cooking immediately and focus on your safety. Call for help if needed."
            )
            actions = actions_data.get("actions", []) or []
        except Exception:
            # Fallback if GPT fails, but the visual warning will still work!
            answer = "Please stop cooking and ensure your safety."
            actions = []

        return {
            "action": ActionType.EMERGENCY,
            "current_step": session.current_step_index + 1 if session.current_step_index >= 0 else 0,
            "total_steps": len(session.recipe.steps),
            "tts_message": answer, # AI generated advice
            "actions": actions,
            "recipe_complete": False,
        }

    def _generate_detailed_step_instruction(
        self, 
        session: Session, 
        step: RecipeStep, 
        current_step_num: int, 
        total_steps: int,
        is_repeat: bool = False
    ) -> str:
        """
        Generate detailed, conversational step instruction using LLM.
        
        Args:
            session: Current cooking session
            step: The recipe step to explain
            current_step_num: Current step number (1-indexed)
            total_steps: Total number of steps
            is_repeat: Whether this is a repeat request
        
        Returns:
            Detailed conversational instruction
        """
        if not self.client:
            # More chatty fallback
            if is_repeat:
                prefix = "Of course! "
            elif current_step_num == 1:
                prefix = "Great! Let's start with "
            else:
                prefix = "Perfect! Now let's "
            
            msg = f"{prefix}Step {current_step_num} of {total_steps}: {step.instruction}"
            if step.estimated_time:
                msg += f". This should take about {step.estimated_time}"
            if step.safety_confirmation:
                msg += f". {step.safety_confirmation}"
            return msg
        
        try:
            # Build context about the recipe and progress
            progress_context = f"We're making {session.recipe.dish_name}. "
            progress_context += f"You're on step {current_step_num} of {total_steps}. "
            
            if current_step_num > 1:
                previous_step = session.recipe.steps[session.current_step_index - 1]
                progress_context += f"You just finished: {previous_step.instruction}. "
            
            # Build prompt for detailed instruction
            prompt = f"""{progress_context}

Now, let's do this step: {step.instruction}"""
            
            if step.estimated_time:
                prompt += f"\nEstimated time: {step.estimated_time}"
            
            if step.requires_heat:
                prompt += "\nThis step involves using heat (stove/oven)."
            if step.requires_knife:
                prompt += "\nThis step involves using a knife or sharp object."
            
            prompt += "\n\nProvide a detailed, conversational explanation of how to do this step. Break it down into clear sub-steps if needed. Be encouraging and helpful."
            
            if is_repeat:
                prompt += " The user asked to repeat this step, so make sure to explain it clearly again."
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": STEP_DETAILER_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=200,
            )
            
            detailed_text = response.choices[0].message.content.strip()
            
            # Add safety confirmation if needed
            if step.safety_confirmation and not is_repeat:
                detailed_text += f" {step.safety_confirmation}"
            
            return detailed_text
            
        except Exception as e:
            print(f"[CookingCoach] Error generating detailed instruction: {repr(e)}")
            # Fallback
            prefix = "Sure! " if is_repeat else ""
            msg = f"{prefix}Step {current_step_num} of {total_steps}: {step.instruction}"
            if step.estimated_time:
                msg += f". This should take about {step.estimated_time}"
            if step.safety_confirmation:
                msg += f". {step.safety_confirmation}"
            return msg
    
    def _build_question_context(self, session: Session) -> str:
        """Build context string for answering questions."""
        context = f"We're cooking {session.recipe.dish_name}. "
        
        if session.current_step_index >= 0 and session.current_step_index < len(session.recipe.steps):
            current_step = session.recipe.steps[session.current_step_index]
            context += f"Currently on step {session.current_step_index + 1} of {len(session.recipe.steps)}: {current_step.instruction}. "
            
            # Add ingredients context
            if session.recipe.ingredients:
                context += f"The recipe uses ingredients like {', '.join(session.recipe.ingredients[:3])}"
                if len(session.recipe.ingredients) > 3:
                    context += f" and {len(session.recipe.ingredients) - 3} more"
                context += ". "
        else:
            context += "We haven't started the steps yet. "
        
        return context
    
    def generate_recipe_intro_message(self, recipe) -> str:
        """
        Generate a warm, conversational introduction message when starting a recipe.
        
        Args:
            recipe: The Recipe object
        
        Returns:
            Conversational introduction message
        """
        # Calculate total cooking time
        total_minutes = 0
        for step in recipe.steps:
            if step.estimated_time:
                # Extract numbers from time strings like "5 minutes", "30 seconds"
                import re
                time_str = step.estimated_time.lower()
                mins = re.search(r'(\d+)\s*minute', time_str)
                secs = re.search(r'(\d+)\s*second', time_str)
                if mins:
                    total_minutes += int(mins.group(1))
                if secs:
                    total_minutes += int(secs.group(1)) / 60
        
        total_time_str = f"{int(total_minutes)} minutes" if total_minutes >= 1 else f"{int(total_minutes * 60)} seconds"
        
        if not self.client:
            # More chatty fallback - ingredients already shown in chat, so just be conversational
            return f"""Perfect! I'm so excited to help you make {recipe.dish_name}! 🍳

This recipe has {recipe.total_steps} steps and will take about {total_time_str} total. Don't worry, I'll guide you through each step - we'll take it nice and easy!

Ready to start? Just say 'next' when you're ready!"""
        
        try:
            # Calculate total time
            total_minutes = 0
            for step in recipe.steps:
                if step.estimated_time:
                    import re
                    time_str = step.estimated_time.lower()
                    mins = re.search(r'(\d+)\s*minute', time_str)
                    secs = re.search(r'(\d+)\s*second', time_str)
                    if mins:
                        total_minutes += int(mins.group(1))
                    if secs:
                        total_minutes += int(secs.group(1)) / 60
            
            total_time_str = f"{int(total_minutes)} minutes" if total_minutes >= 1 else f"{int(total_minutes * 60)} seconds"
            
            prompt = f"""The user wants to cook {recipe.dish_name}. 

I've prepared a complete recipe with {len(recipe.ingredients)} ingredients (they're listed above).
The recipe has {recipe.total_steps} steps and will take about {total_time_str} total.

Give them a warm, friendly, clear, and enthusiastic introduction message. 
- Be excited and encouraging (like a friend helping in the kitchen)
- DON'T repeat the ingredients list (they're already shown)
- Mention the total time and number of steps
- Let them know you'll guide them step-by-step
- Be natural (2-3 sentences)
- Do not use emojis
- Keep responses concise (maximum 2 sentences)

Make it feel like you're right there with them, ready to help!"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are Voice Chef, a friendly, clear, and enthusiastic cooking coach. You're like a helpful friend in the kitchen - warm, encouraging, and excited to help. Be conversational and natural."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.9,
                max_tokens=300,
            )
            
            intro = response.choices[0].message.content.strip()
            # Ensure it ends with instruction to say 'next'
            if "next" not in intro.lower():
                intro += " Say 'next' when you're ready to begin!"
            
            return intro
        except Exception as e:
            print(f"[CookingCoach] Error generating intro message: {repr(e)}")
            # Fallback
            ingredients_text = ", ".join(recipe.ingredients[:3])
            if len(recipe.ingredients) > 3:
                ingredients_text += f", and {len(recipe.ingredients) - 3} more"
            return f"Great! I've prepared a recipe for {recipe.dish_name}. You'll need {ingredients_text}. There are {recipe.total_steps} steps in total. Say 'next' when you're ready to start!"
    
    def _generate_completion_message(self, session: Session) -> str:
        """Generate a celebratory completion message."""
        if not self.client:
            return f"Congratulations! You've completed the {session.recipe.dish_name}. Enjoy your meal!"
        
        try:
            prompt = f"""The user just finished cooking {session.recipe.dish_name}. 
They completed all {len(session.recipe.steps)} steps successfully.

Give them a warm, encouraging, and celebratory message (2-3 sentences). 
Be proud of their accomplishment and encourage them to enjoy their meal."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are Voice Chef, a friendly cooking coach celebrating the user's success."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=150,
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[CookingCoach] Error generating completion message: {repr(e)}")
            return f"Congratulations! You've completed the {session.recipe.dish_name}. Enjoy your meal!"
    
    def _ask_gpt_structured(self, user_text: str) -> dict:
        """Call LLM and parse its JSON response into a Python dict."""
        if not self.client:
            # If no LLM client configured, just echo back plain text with no actions
            return {
                "assistant_role": "voice_chef",
                "response_text": "I'm having trouble processing that right now. Could you try again?",
                "actions": [],
            }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": VOICE_CHEF_SYSTEM},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.7,
                max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()
            print("RAW GPT OUTPUT (structured actions):", raw)
            
            # Try to extract JSON if wrapped in markdown
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"[CookingCoach] JSON parse error in _ask_gpt_structured: {repr(e)}")
            print(f"[CookingCoach] Raw output: {raw}")
            # Fallback: return the text as response
            data = {
                "assistant_role": "voice_chef",
                "response_text": raw if raw else "I'm having trouble answering that. Could you rephrase?",
                "actions": [],
            }
        except Exception as e:
            print(f"[CookingCoach] Error in _ask_gpt_structured: {repr(e)}")
            # Fallback: no structured actions
            data = {
                "assistant_role": "voice_chef",
                "response_text": "I'm having trouble processing that right now. Could you try again?",
                "actions": [],
            }
        return data

