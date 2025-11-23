"""
Configuration Management Module
Handles environment variables and application settings
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMConfig(BaseModel):
    """LLM Provider Configuration"""
    provider: str = Field(default="groq", description="LLM provider: groq, openai, claude")
    model: str = Field(default="openai/gpt-oss-20b", description="Model name")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=100, le=32000)
    api_key: Optional[str] = None

class BrowserConfig(BaseModel):
    """Browser Automation Configuration"""
    headless: bool = Field(default=True, description="Run browser in headless mode")
    timeout: int = Field(default=30000, description="Default timeout in milliseconds")
    viewport_width: int = Field(default=1920)
    viewport_height: int = Field(default=1080)
    slow_mo: int = Field(default=100, description="Slow down operations by ms")

class AppConfig(BaseModel):
    """Application Configuration"""
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DB_PATH: Path = BASE_DIR / "bdd_tests.db"
    LOGS_DIR: Path = BASE_DIR / "logs"
    OUTPUTS_DIR: Path = BASE_DIR / "outputs"
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    DEBUG: bool = False
    
    # LLM Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Default LLM Configuration
    DEFAULT_LLM_PROVIDER: str = "groq"
    
    # Model mappings
    MODELS: dict = {
        "groq": [
            "openai/gpt-oss-20b",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant"
        ],
        "openai": [
            "gpt-4-turbo-preview",
            "gpt-4",
            "gpt-3.5-turbo"
        ],
        "claude": [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307"
        ]
    }
    
    # Browser Settings
    PLAYWRIGHT_BROWSERS: list = ["chromium"]
    
    # Feature Generation Settings
    MAX_HOVER_ELEMENTS: int = 20
    MAX_POPUP_ELEMENTS: int = 10
    HOVER_DELAY_MS: int = 500
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global configuration instance
config = AppConfig()

# Ensure directories exist
config.LOGS_DIR.mkdir(exist_ok=True)
config.OUTPUTS_DIR.mkdir(exist_ok=True)


