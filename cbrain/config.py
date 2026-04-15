from __future__ import annotations

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://cbrain:cbrain_dev@localhost:5432/cbrain"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    notion_api_key: str = ""
    memory_paths: str = ""
    jopedia_path: str = "/tmp/jopedia"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    agent_timezone: str = "America/Los_Angeles"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def memory_path_list(self) -> list[str]:
        if not self.memory_paths:
            return []
        return [p.strip() for p in self.memory_paths.split(",") if p.strip()]

    def get_anthropic_key(self) -> str:
        """Get Anthropic key from settings or fall back to env."""
        return self.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def get_notion_key(self) -> str:
        """Get Notion key from settings or fall back to env."""
        return self.notion_api_key or os.environ.get("NOTION_API_KEY", "")


settings = Settings()
