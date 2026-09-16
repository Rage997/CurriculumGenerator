"""LLM client (llama.cpp, OpenAI-compatible API) and typed errors.

This is the single network boundary of the core. Everything above it is pure
and testable; tests inject a fake implementing :class:`LLMBackend` instead of
hitting a real server.

Uses ``httpx`` (the same library the FastAPI stack uses) so migrating the
client to ``httpx.AsyncClient`` for the async service is a drop-in change.
"""

from typing import Protocol

import httpx

from .config import Settings


class LLMError(Exception):
    """Base class for all LLM-layer errors."""


class LLMConfigError(LLMError):
    """Configuration is missing or invalid (e.g. no model set)."""


class LLMConnectionError(LLMError):
    """The LLM server could not be reached or returned an HTTP error."""


class LLMResponseError(LLMError):
    """The server responded but the payload was not the expected shape."""


class LLMBackend(Protocol):
    """The interface the rest of the core depends on.

    Only ``check`` and ``chat`` are required, so a test double needs to
    implement just those two methods.
    """

    def check(self) -> None:
        ...

    def chat(self, prompt: str) -> str:
        ...


class LLMClient:
    """Synchronous client for a llama.cpp server."""

    def __init__(self, config: Settings):
        self.config = config

    def _headers(self) -> dict:
        headers = {'Content-Type': 'application/json'}
        if self.config.api_key:
            headers['Authorization'] = f'Bearer {self.config.api_key}'
        return headers

    def _get_models(self) -> list[str]:
        try:
            resp = httpx.get(
                f"{self.config.base_url}/v1/models",
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMConnectionError(
                f"Cannot reach LLM server at {self.config.base_url}: {e}"
            ) from e
        return [m['id'] for m in resp.json().get('data', [])]

    def check(self) -> None:
        """Fail fast if the model is unset or the server is unreachable."""
        if not self.config.model:
            raise LLMConfigError(
                "LLM_MODEL is not set. Set it in the environment or via "
                "`curriculum-generator configure --model <name>`."
            )
        self._get_models()

    def list_models(self) -> list[str]:
        return self._get_models()

    def chat(self, prompt: str) -> str:
        if not self.config.model:
            raise LLMConfigError("LLM_MODEL is not set")
        payload = {
            'model': self.config.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': self.config.max_tokens,
            'temperature': 0.2,
        }
        if not self.config.enable_thinking:
            # Qwen3-style thinking models burn the token budget on hidden
            # reasoning; disable it unless explicitly opted in.
            payload['chat_template_kwargs'] = {'enable_thinking': False}
        try:
            resp = httpx.post(
                f"{self.config.base_url}/v1/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.config.timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMConnectionError(f"LLM request failed: {e}") from e
        data = resp.json()
        try:
            return data['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError) as e:
            raise LLMResponseError(
                f"Unexpected LLM response shape: {str(data)[:200]}"
            ) from e
