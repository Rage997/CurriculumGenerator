"""FastAPI application factory.

``create_app`` builds a configured app so tests can inject their own
``Settings`` (and, via dependency overrides, a fake LLM). The module-level
``app`` is what ``uvicorn curriculum_generator.api.app:app`` serves.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..config import Settings
from ..llm import LLMConfigError, LLMConnectionError, LLMError
from .routes import router

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="Curriculum Generator API",
        version="0.1.0",
        description=(
            "Generate tailored CVs and cover letters from a job description "
            "and a candidate profile, using a local llama.cpp backend."
        ),
    )
    app.state.settings = settings
    app.include_router(router)

    @app.exception_handler(LLMError)
    async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
        # Log the real error server-side; return a generic message to callers.
        logger.error("LLM error on %s: %s", request.url.path, exc)
        if isinstance(exc, LLMConfigError):
            status, detail = 503, "Service is misconfigured"
        elif isinstance(exc, LLMConnectionError):
            status, detail = 502, "LLM backend is unavailable"
        else:
            status, detail = 502, "LLM returned an unexpected response"
        return JSONResponse(status_code=status, content={"detail": detail})

    return app


app = create_app()
