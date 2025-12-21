"""Configuration management for VoiceChef backend."""

from typing import List
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "VoiceChef HoloGuide Backend"
    debug: bool = True
    
    # CORS Settings
    cors_origins: List[str] = ["*"]  # Allow all origins for development
    
    # OpenAI Configuration (optional / legacy)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    
    # Groq Configuration (preferred - faster and has free tier)
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"  # Fast and free tier available
    
    # Whisper settings
    whisper_model: str = "small"  # Options: tiny, base, small, medium, large
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance (singleton)."""
    return Settings()

