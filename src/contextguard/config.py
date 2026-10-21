"""Central configuration for ContextGuard."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    groq_api_key: str = ""
    github_token: str = ""


def get_settings() -> Settings:
    """Return settings without requiring API keys for offline use."""
    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        github_token=os.getenv("GITHUB_TOKEN", ""),
    )
