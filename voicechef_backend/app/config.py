"""Configuration and environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    app_name: str = "VoiceChef Backend"
    debug: bool = False
    
    # OpenAI Configuration (optional / legacy)
    openai_api_key: str = ""
    openai_model: str = "gpt-4"

    # Groq Configuration (preferred for this project)
    groq_api_key: str = ""
    groq_model: str = "llama3-8b-8192"
    
    # CORS Settings
    cors_origins: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

