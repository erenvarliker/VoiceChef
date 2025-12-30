"""FastAPI application for VoiceChef HoloGuide backend."""
from datetime import datetime, timezone  # <-- add this
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import whisper
import tempfile
import os
from app.config import get_settings
from app.schemas import (
    StartRecipeRequest,
    StartRecipeResponse,
    InterpretRequest,
    InterpretResponse,
    TranscribeResponse,
    ActionType,
)
from app import state
from app.services.planner import RecipePlanner
from app.services.coach import CookingCoach

# Initialize FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.2.0",
    description="AI backend for VoiceChef HoloGuide - Voice-controlled AR cooking assistant"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
recipe_planner = RecipePlanner()
cooking_coach = CookingCoach()

# Load Whisper model (lazy loading)
_whisper_model = None

def get_whisper_model():
    """Lazy load Whisper model."""
    global _whisper_model
    if _whisper_model is None:
        print(f"[STT] Loading Whisper model: {settings.whisper_model}")
        _whisper_model = whisper.load_model(settings.whisper_model)
    return _whisper_model


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "0.2.0",
        "description": "VoiceChef HoloGuide Backend - AI cooking assistant for HoloLens"
    }


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """
    Transcribe audio to text using Whisper.
    
    Unity sends audio file (WAV, MP3, etc.)
    Returns transcribed text.
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            content = await audio_file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Transcribe with Whisper
            model = get_whisper_model()
            result = model.transcribe(
                tmp_path,
                language="en",
                fp16=False
            )
            
            transcribed_text = result["text"].strip()
            detected_language = result.get("language", "en")
            
            return TranscribeResponse(
                text=transcribed_text,
                language=detected_language
            )
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@app.post("/start_recipe", response_model=StartRecipeResponse)
async def start_recipe(request: StartRecipeRequest):
    """
    Start a new cooking session from natural language input.
    
    Unity sends: {"user_message": "I want to cook pasta carbonara", "session_id": "optional"}
    
    Returns: Recipe with ingredients, steps, safety flags, and TTS message
    """
    try:
        # Extract dish name from natural language
        dish_name = recipe_planner.extract_dish_name(request.user_message)
        
        # Generate recipe with safety detection
        recipe = recipe_planner.create_recipe(dish_name)
        
        # Create session
        session = state.create_session(recipe, session_id=request.session_id)
        
        # Build conversational TTS message for Unity
        tts_message = cooking_coach.generate_recipe_intro_message(recipe)
        
        # Log interaction
        state.log_interaction(
            session.session_id,
            "start_recipe",
            request.user_message,
            tts_message
        )
        
        return StartRecipeResponse(
            session_id=session.session_id,
            action=ActionType.RECIPE_CREATED,
            recipe=recipe,
            tts_message=tts_message
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create recipe: {str(e)}"
        )


@app.post("/interpret", response_model=InterpretResponse)
async def interpret_command(request: InterpretRequest):
    """
    Interpret user command during cooking.
    
    Unity sends: {"session_id": "abc-123", "user_message": "next"}
    
    Returns: Action, step data, TTS message, and optional timer data
    """
    # Verify session exists
    try:
        session = state.get_session(request.session_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {request.session_id}"
        )
    
    try:
        # Interpret command
        response_data = cooking_coach.interpret_command(session, request.user_message)
        
        # Update session state
        state.update_session(session)
        
        # Log interaction
        state.log_interaction(
            session.session_id,
            response_data["action"],
            request.user_message,
            response_data["tts_message"]
        )
        
        # Build response
        return InterpretResponse(
            session_id=request.session_id,
            action=response_data["action"],
            current_step=response_data.get("current_step"),
            total_steps=response_data.get("total_steps"),
            step_data=response_data.get("step_data"),
            tts_message=response_data["tts_message"],
            timer_data=response_data.get("timer_data"),
            actions=response_data.get("actions"),
            recipe_complete=response_data.get("recipe_complete", False)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process command: {str(e)}"
        )


@app.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """
    Get current session status with full details for Unity UI.
    """
    try:
        session = state.get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 1. Get Current Step Details
    current_step_data = None
    if 0 <= session.current_step_index < len(session.recipe.steps):
        step = session.recipe.steps[session.current_step_index]
        current_step_data = {
            "step_number": step.step_number,
            "title": step.title,   # <--- ADD THIS
            "instruction": step.instruction,
            "estimated_time": step.estimated_time
        }
    
    # 2. Calculate Active Timers (Remaining Time)
    active_timers_data = []
    
    now = datetime.now(timezone.utc)
    for t in session.timers:
        start_time = t.started_at
        
        # SAFETY FIX: Ensure start_time is also timezone-aware
        # If the timer was created with naive utcnow(), we simply tag it as UTC.
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
            
        elapsed = (now - start_time).total_seconds()
        remaining = max(0, t.duration_seconds - elapsed)
        
        if remaining > 0:
            active_timers_data.append({
                "timer_id": t.timer_id,
                "remaining_seconds": remaining,
                "total_seconds": t.duration_seconds
            })

    return {
        "session_id": session.session_id,
        "dish_name": session.recipe.dish_name,
        "current_step_index": session.current_step_index,
        "total_steps": len(session.recipe.steps),
        "is_paused": session.is_paused,

        "active_warning": session.active_warning,  # <--- NEW FIELD
        "current_step": current_step_data,
        
        # New Fields for your UI:
        "ingredients": session.recipe.ingredients, 
        "timers": active_timers_data
    }


@app.get("/session/{session_id}/analytics")
async def get_session_analytics(session_id: str):
    """
    Get detailed analytics for research (NASA-TLX, completion time, etc.).
    
    Returns: Full interaction log, timestamps, error counts
    """
    try:
        session = state.get_session(session_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )
    
    # Calculate metrics
    total_interactions = len(session.interaction_log)
    
    interaction_types = {}
    for log in session.interaction_log:
        action = log["type"]
        interaction_types[action] = interaction_types.get(action, 0) + 1
    
    # Calculate completion time if recipe is complete
    completion_time = None
    if session.interaction_log:
        start_time = session.interaction_log[0]["timestamp"]
        end_time = session.interaction_log[-1]["timestamp"]
        # You can calculate duration here if needed
    
    return {
        "session_id": session.session_id,
        "recipe": session.recipe.dish_name,
        "total_steps": len(session.recipe.steps),
        "current_step": session.current_step_index,
        "total_interactions": total_interactions,
        "interaction_breakdown": interaction_types,
        "is_complete": session.current_step_index >= len(session.recipe.steps),
        "interaction_log": session.interaction_log
    }


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a cooking session.
    """
    if not state.delete_session(session_id):
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )
    
    return {"message": "Session deleted successfully", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


