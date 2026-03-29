"""
Perknow Configuration
Loads settings from environment variables or .env file
"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with defaults"""
    
    # Paths
    DATABASE_PATH: Path = Path("data/perknow.db")
    EXPORT_PATH: Path = Path("export")
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    CHAT_MODEL: str = "qwen2.5:7b"  # Using available model (llama3.2 can be swapped in when ready)
    
    # LLM Timeouts
    LLM_TIMEOUT_SECONDS: int = 30
    EMBEDDING_TIMEOUT_SECONDS: int = 10
    
    # Gardener Worker
    WORKER_POLL_INTERVAL_SECONDS: int = 5
    MAX_RETRIES: int = 3
    
    # Export
    EXPORT_INBOX_SUBDIR: str = "inbox"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
