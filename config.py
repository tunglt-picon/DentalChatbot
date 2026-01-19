"""Application configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Google Gemini API
    google_api_key: str
    google_base_model: str = "gemini-2.5-flash"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
