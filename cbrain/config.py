from __future__ import annotations

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://cbrain:cbrain_dev@localhost:5432/cbrain"

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Notion
    notion_api_key: str = ""

    # Memory paths (comma-separated)
    memory_paths: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Agent scheduling
    agent_timezone: str = "America/Los_Angeles"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def memory_path_list(self) -> list[str]:
        if not self.memory_paths:
            return []
        return [p.strip() for p in self.memory_paths.split(",") if p.strip()]


settings = Settings()
