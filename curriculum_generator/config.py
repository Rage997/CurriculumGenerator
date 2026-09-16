"""Process configuration.

All settings come from environment variables (optionally seeded from a local
``.env`` file for CLI/dev use). The service never mutates configuration on
disk; per-request values are passed in with each request.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server and generation settings.

    LLM-related keys use the ``LLM_`` prefix; project paths do not. A local
    ``.env`` file (relative to the working directory) is read when present,
    which is what the CLI relies on. In a container the variables are set
    directly and no ``.env`` file is needed.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str = Field(default="http://localhost:8080", validation_alias="LLM_BASE_URL")
    model: str = Field(default="", validation_alias="LLM_MODEL")
    api_key: str = Field(default="", validation_alias="LLM_API_KEY")
    max_tokens: int = Field(default=2048, validation_alias="LLM_MAX_TOKENS")
    timeout: int = Field(default=300, validation_alias="LLM_TIMEOUT")
    enable_thinking: bool = Field(default=False, validation_alias="LLM_ENABLE_THINKING")
    output_dir: str = Field(default="output")
    templates_dir: str = Field(default="templates")
    # Optional bearer key for authenticating callers of the HTTP API. Empty
    # disables auth (local dev only); set it in any real deployment.
    service_api_key: str = Field(default="", validation_alias="SERVICE_API_KEY")
