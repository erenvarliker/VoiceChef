"""In-memory storage for sessions, recipes, and timers."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from app.schemas import Recipe


@dataclass
class Timer:
    """Represents a cooking timer."""
    timer_id: str
    duration_seconds: int
    label: Optional[str] = None
    started_at: Optional[datetime] = None


@dataclass
class Session:
    """Represents an active cooking session."""
    session_id: str
    recipe: Recipe
    current_step_index: int = 0
    is_paused: bool = False
    timers: List[Timer] = field(default_factory=list)
    interaction_log: List[dict] = field(default_factory=list)


# Global in-memory storage
_sessions: Dict[str, Session] = {}


def create_session(recipe: Recipe, session_id: Optional[str] = None) -> Session:
    """Create a new cooking session."""
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    session = Session(session_id=session_id, recipe=recipe)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Session:
    """Get session by ID, raises KeyError if not found."""
    if session_id not in _sessions:
        raise KeyError(f"Unknown session_id: {session_id}")
    return _sessions[session_id]


def update_session(session: Session) -> None:
    """Update session in storage."""
    _sessions[session.session_id] = session


def delete_session(session_id: str) -> bool:
    """Delete a session."""
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


def session_exists(session_id: str) -> bool:
    """Check if session exists."""
    return session_id in _sessions


def log_interaction(session_id: str, interaction_type: str, user_message: str, response: str) -> None:
    """Log user interaction for research analysis."""
    session = get_session(session_id)
    session.interaction_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "type": interaction_type,
        "user_message": user_message,
        "response": response
    })
