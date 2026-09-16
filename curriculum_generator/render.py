"""Render CV / cover-letter HTML and produce PDF bytes with WeasyPrint.

The render functions return ``(html, pdf_bytes)`` and never touch the disk —
delivery (writing files, serving over HTTP) is the caller's responsibility.
WeasyPrint is imported lazily so that commands that don't render (``models``,
``configure``) don't pay its import cost.
"""

import datetime
import logging

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


def _write_pdf(html: str) -> bytes:
    from weasyprint import HTML

    return HTML(string=html).write_pdf()


def _render_template(templates_dir: str, template_path: str, **context) -> str:
    env = Environment(loader=FileSystemLoader(templates_dir))
    return env.get_template(template_path).render(**context)


def render_cv(cv_content, profile, job_data, templates_dir: str) -> tuple[str, bytes]:
    """Render the CV. Returns ``(html, pdf_bytes)``."""
    html = _render_template(
        templates_dir,
        'cv/cv.html',
        content=cv_content,
        user=profile.model_dump(),
        job=job_data.model_dump(),
    )
    pdf = _write_pdf(html)
    return html, pdf


def render_cover_letter(cover_content, profile, job_data, templates_dir: str) -> tuple[str, bytes]:
    """Render the cover letter. Returns ``(html, pdf_bytes)``.

    The current date is injected for the letter header.
    """
    job = job_data.model_dump()
    job['date'] = datetime.datetime.now().strftime('%B %d, %Y')
    html = _render_template(
        templates_dir,
        'cover_letter/cover_letter.html',
        content=cover_content,
        user=profile.model_dump(),
        job=job,
    )
    pdf = _write_pdf(html)
    return html, pdf
