"""
Application configuration settings.
Loads environment variables and provides typed access.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Optional
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "MedGemma Clinical Suite API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS: str = '["*"]'

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string to list."""
        try:
            return json.loads(self.CORS_ORIGINS)
        except json.JSONDecodeError:
            return ["*"]

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # JWT Authentication
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # AI Service (MedGemma)
    MEDGEMMA_API_URL: Optional[str] = None
    MEDGEMMA_API_KEY: Optional[str] = None

    # RunPod Serverless
    RUNPOD_ENDPOINT_ID: Optional[str] = None
    RUNPOD_API_KEY: Optional[str] = None

    # AI Service Mode override: set to "debug" to inspect payloads without calling RunPod
    AI_SERVICE_MODE: Optional[str] = None

    # Demo patient business IDs — conversations/messages are ephemeral for these
    DEMO_PATIENT_IDS: str = '["13011", "16997", "17523", "24163", "40207", "44669"]'

    @property
    def demo_patient_ids_set(self) -> set:
        """Parse DEMO_PATIENT_IDS string to a set."""
        try:
            return set(json.loads(self.DEMO_PATIENT_IDS))
        except json.JSONDecodeError:
            return set()

    # Storage
    STORAGE_BUCKET: str = "medical-images"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
