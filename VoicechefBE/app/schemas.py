"""Pydantic schemas for request/response models."""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum


class ActionType(str, Enum):
    """Action types for cooking session."""
    RECIPE_CREATED = "recipe_created"
    NEXT_STEP = "next_step"
    REPEAT_STEP = "repeat_step"
    TIMER_SET = "timer_set"
    PAUSE = "pause"
    RESUME = "resume"
    ANSWER_QUESTION = "answer_question"
    EMERGENCY = "emergency"
    ERROR = "error"
    RECIPE_COMPLETE = "recipe_complete"


class RecipeStep(BaseModel):
    """A single recipe step."""
    step_number: int
    title: str = "Instruction"  # <--- NEW FIELD
    instruction: str
    estimated_time: Optional[str] = None
    requires_heat: bool = False
    requires_knife: bool = False
    safety_confirmation: Optional[str] = None


class Recipe(BaseModel):
    """Complete recipe with ingredients and steps."""
    dish_name: str
    total_steps: int
    ingredients: List[str]
    steps: List[RecipeStep]


class StepData(BaseModel):
    """Step data for Unity display."""
    step_number: int
    title: str = ""
    instruction: str
    estimated_time: Optional[str] = None
    requires_heat: bool = False
    requires_knife: bool = False
    safety_confirmation: Optional[str] = None


class TimerData(BaseModel):
    """Timer information."""
    timer_id: str
    duration_seconds: int
    started_at: str  # ISO format timestamp


# Request Models
class StartRecipeRequest(BaseModel):
    """Request to start a new recipe."""
    user_message: str  # e.g., "I want to cook pasta carbonara"
    session_id: Optional[str] = None


class InterpretRequest(BaseModel):
    """Request to interpret user command."""
    session_id: str
    user_message: str  # Transcribed text from Unity


class TranscribeRequest(BaseModel):
    """Request to transcribe audio."""
    audio_data: bytes  # Will be handled as file upload in FastAPI


# Response Models
class StartRecipeResponse(BaseModel):
    """Response when starting a recipe."""
    session_id: str
    action: ActionType
    recipe: Recipe
    tts_message: str


class InterpretResponse(BaseModel):
    """Response to user command interpretation."""
    session_id: str
    action: ActionType
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    step_data: Optional[StepData] = None
    tts_message: str
    timer_data: Optional[TimerData] = None
    actions: Optional[List[Dict[str, Any]]] = None
    recipe_complete: bool = False


class TranscribeResponse(BaseModel):
    """Response from audio transcription."""
    text: str
    language: str = "en"


