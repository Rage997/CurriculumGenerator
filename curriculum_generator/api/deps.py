"""FastAPI dependencies: service construction and API-key auth."""

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import Settings
from ..service import CurriculumService

# auto_error=False so a missing header yields None (handled below) instead of
# a hard 403, letting us distinguish "auth disabled" from "bad key".
_bearer = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_service(request: Request) -> CurriculumService:
    # Built per request: it only holds config + a stateless LLM client, so
    # this is cheap and keeps the app free of shared mutable state.
    return CurriculumService(request.app.state.settings)


def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    settings = request.app.state.settings
    if not settings.service_api_key:
        return  # auth disabled
    if credentials is None or credentials.credentials != settings.service_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
