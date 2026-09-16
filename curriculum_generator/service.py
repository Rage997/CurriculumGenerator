"""The orchestrator: turn a :class:`GenerateRequest` into a
:class:`GenerationResult`.

This is the seam the CLI and (later) the API both call into. It is pure with
respect to delivery — it returns bytes and never writes to disk or prints.
Errors from the LLM layer propagate as typed :class:`~.llm.LLMError`
subclasses for the caller to translate into exit codes / HTTP status codes.
"""

import logging

from .config import Settings
from .content import generate_cover_letter_content, generate_cv_content
from .llm import LLMBackend, LLMClient
from .models import GenerateRequest, GenerationResult
from .parser import parse_job_description
from .render import render_cover_letter, render_cv

logger = logging.getLogger(__name__)

_DRY_RUN_CV = (
    "Education:\nSample education\n\n"
    "Experience:\nSample experience\n\n"
    "Skills:\nSample skills"
)
_DRY_RUN_COVER = "Sample cover letter content."


class CurriculumService:
    def __init__(self, config: Settings, llm: LLMBackend | None = None):
        self.config = config
        self.llm = llm or LLMClient(config)

    def generate(self, request: GenerateRequest) -> GenerationResult:
        profile = request.profile
        job_data = parse_job_description(request.job_description)
        logger.info("Parsed job: %s @ %s", job_data.title, job_data.company)

        if request.dry_run:
            cv_content = _DRY_RUN_CV
            cover_content = _DRY_RUN_COVER
        else:
            self.llm.check()
            cv_content = generate_cv_content(
                request.job_description, profile, job_data,
                request.skill_modification_level, self.llm,
            )
            cover_content = generate_cover_letter_content(
                request.job_description, profile, job_data,
                request.skill_modification_level, self.llm,
            )

        cv_html, cv_pdf = render_cv(cv_content, profile, job_data, self.config.templates_dir)
        cover_html, cover_pdf = render_cover_letter(
            cover_content, profile, job_data, self.config.templates_dir
        )
        logger.info("Generation completed")
        return GenerationResult(
            cv_html=cv_html,
            cv_pdf=cv_pdf,
            cover_html=cover_html,
            cover_pdf=cover_pdf,
            job_data=job_data,
        )
