"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class ActionType(str, Enum):
    """Action types returned to Unity."""
    RECIPE_CREATED = "recipe_created"
    NEXT_STEP = "next_step"
    REPEAT_STEP = "repeat_step"
    ANSWER_QUESTION = "answer_question"
    TIMER_SET = "timer_set"
    TIMER_QUERY = "timer_query"
    PAUSE = "pause"
    RESUME = "resume"
    RECIPE_COMPLETE = "recipe_complete"
    ERROR = "error"
    EMERGENCY = "emergency"


# ============= REQUEST MODELS =============

class StartRecipeRequest(BaseModel):
    """Request to start a new recipe from Unity."""
    user_message: str = Field(..., description="User's spoken message (e.g., 'I want to cook pasta')")
    session_id: Optional[str] = Field(None, description="Optional session ID from Unity")


class InterpretRequest(BaseModel):
    """Request to interpret user command during cooking."""
    session_id: str = Field(..., description="Session ID")
    user_message: str = Field(..., description="User's spoken command (e.g., 'next', 'repeat', 'can I use olive oil?')")


# ============= RECIPE MODELS =============

class RecipeStep(BaseModel):
    """A single step in a recipe with safety flags."""
    step_number: int
    instruction: str
    estimated_time: Optional[str] = None
    requires_heat: bool = False
    requires_knife: bool = False
    safety_confirmation: Optional[str] = None


class Recipe(BaseModel):
    """Complete recipe structure."""
    dish_name: str
    total_steps: int
    ingredients: List[str]
    steps: List[RecipeStep]


class StepData(BaseModel):
    """Current step information for Unity."""
    step_number: int
    instruction: str
    estimated_time: Optional[str] = None
    requires_heat: bool = False
    requires_knife: bool = False
    safety_confirmation: Optional[str] = None


# ============= TIMER MODELS =============

class TimerData(BaseModel):
    """Timer information."""
    timer_id: str
    duration_seconds: int
    label: Optional[str] = None
    started_at: Optional[str] = None


# ============= RESPONSE MODELS =============

class StartRecipeResponse(BaseModel):
    """Response after creating a recipe."""
    session_id: str
    action: ActionType
    recipe: Recipe
    tts_message: str = Field(..., description="Message for Unity to speak via TTS")


class InterpretResponse(BaseModel):
    """Response to user command interpretation."""
    session_id: str
    action: ActionType
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    step_data: Optional[StepData] = None
    tts_message: str = Field(..., description="Message for Unity to speak via TTS")
    timer_data: Optional[TimerData] = None
    actions: Optional[List[Dict[str, Any]]] = None
    recipe_complete: bool = False

