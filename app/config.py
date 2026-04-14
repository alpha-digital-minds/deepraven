from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis — kept for distributed locking only
    redis_url: str

    # Supabase
    supabase_url: str
    supabase_secret_key: str    # sb_secret_... key — never expose to clients
    supabase_management_token: str = ""  # only needed for running migrations

    # LLM
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Tuning
    max_conversations_context: int = 20
    # Seconds to wait after the last conversation before running LLM extraction.
    # New conversations arriving within this window are batched together.
    extraction_delay_seconds: int = 60

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
