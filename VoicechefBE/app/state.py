"""Session state management for cooking sessions."""

from typing import Dict, Optional
from datetime import datetime
from app.schemas import Recipe


class Timer:
    """Timer object for cooking session."""
    def __init__(self, timer_id: str, duration_seconds: int, started_at: datetime):
        self.timer_id = timer_id
        self.duration_seconds = duration_seconds
        self.started_at = started_at


class Session:
    """Cooking session state."""
    def __init__(self, session_id: str, recipe: Recipe):
        self.session_id = session_id
        self.recipe = recipe
        self.current_step_index = -1  # -1 means not started
        self.is_paused = False
        self.active_warning: Optional[str] = None  # <--- NEW: Stores "fire", "cut", etc.
        self.timers: list[Timer] = []
        self.interaction_log: list[dict] = []
        self.created_at = datetime.utcnow()


# In-memory session storage (for development)
# In production, use Redis or database
_sessions: Dict[str, Session] = {}


def create_session(recipe: Recipe, session_id: Optional[str] = None) -> Session:
    """Create a new cooking session."""
    import uuid
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    session = Session(session_id, recipe)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Session:
    """Get session by ID."""
    if session_id not in _sessions:
        raise KeyError(f"Session not found: {session_id}")
    return _sessions[session_id]


def update_session(session: Session) -> None:
    """Update session (currently just ensures it exists)."""
    if session.session_id not in _sessions:
        _sessions[session.session_id] = session


def delete_session(session_id: str) -> bool:
    """Delete a session."""
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


def log_interaction(session_id: str, action_type: str, user_input: str, assistant_response: str) -> None:
    """Log an interaction for research/analytics."""
    session = get_session(session_id)
    session.interaction_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "type": action_type,
        "user_input": user_input,
        "assistant_response": assistant_response
    })

