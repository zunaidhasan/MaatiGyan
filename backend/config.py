"""
MaatiGyan — Application Configuration
Loads settings from environment variables / .env file
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional
import os


class Settings(BaseSettings):
    # ── Application ─────────────────────────────────────────
    app_name: str = "MaatiGyan"
    app_version: str = "1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"
    demo_mode: bool = True   # True = uses pre-loaded demo data

    # ── WhatsApp Cloud API ───────────────────────────────────
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = "matigyan_webhook_verify_2024"

    # ── Groq LLM API ────────────────────────────────────────
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.1-8b-instant"

    # ── Google Earth Engine ──────────────────────────────────
    gee_service_account: Optional[str] = None
    gee_key_file: str = "backend/gee_service_account_key.json"
    gee_service_account_json: Optional[str] = None  # Raw JSON string for cloud envs

    # ── Qdrant Vector DB ─────────────────────────────────────
    qdrant_url: str = ""
    qdrant_api_key: Optional[str] = None
    qdrant_collection: str = "srdi_recommendations"

    # ── Paths ─────────────────────────────────────────────────
    data_dir: str = Field(
        default_factory=lambda: os.path.join(os.path.dirname(__file__), "data")
    )
    audio_dir: str = Field(
        default_factory=lambda: os.path.join(os.path.dirname(__file__), "..", "audio_cache")
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def is_whatsapp_configured(self) -> bool:
        return bool(self.whatsapp_token and self.whatsapp_phone_number_id)

    @property
    def is_gee_configured(self) -> bool:
        """Checks if GEE is ready via file or environment string"""
        has_file = os.path.exists(self.gee_key_file)
        has_env_json = bool(self.gee_service_account_json)
        return bool(self.gee_service_account) and (has_file or has_env_json)

    @property
    def is_groq_configured(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def soil_coefficients_path(self) -> str:
        return os.path.join(self.data_dir, "soil_coefficients.json")

    @property
    def srdi_corpus_path(self) -> str:
        return os.path.join(self.data_dir, "srdi_recommendations.txt")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
