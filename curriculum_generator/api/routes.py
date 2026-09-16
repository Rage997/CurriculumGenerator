"""API routes.

``POST /generate`` is a synchronous endpoint: FastAPI runs it in a worker
thread (it is a plain ``def``), so the blocking LLM + PDF work does not stall
the event loop. The long-running job pattern (submit -> poll -> download) is
the next step once concurrency/latency demands it.
"""

import base64

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..models import GenerateRequest, GenerationResult, JobData
from ..service import CurriculumService
from .deps import get_service, verify_api_key

router = APIRouter()


class GenerationResponse(BaseModel):
    cv_pdf: str  # base64-encoded PDF
    cover_pdf: str  # base64-encoded PDF
    cv_html: str
    cover_html: str
    job_data: JobData


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post(
    "/generate",
    response_model=GenerationResponse,
    dependencies=[Depends(verify_api_key)],
)
def generate(
    request: GenerateRequest,
    service: CurriculumService = Depends(get_service),
) -> GenerationResponse:
    result: GenerationResult = service.generate(request)
    return GenerationResponse(
        cv_pdf=base64.b64encode(result.cv_pdf).decode("ascii"),
        cover_pdf=base64.b64encode(result.cover_pdf).decode("ascii"),
        cv_html=result.cv_html,
        cover_html=result.cover_html,
        job_data=result.job_data,
    )
