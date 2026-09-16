"""Pydantic data models.

These define the validated shape of a candidate profile, a generation request,
the parsed job description, and the generation result. Keeping them as models
(instead of raw dicts) is what lets the API layer validate incoming requests
for free and kills the ``KeyError``-on-malformed-profile failure mode.
"""

from pydantic import BaseModel, Field


class Experience(BaseModel):
    title: str = ""
    company: str = ""
    dates: str = ""
    description: str = ""


class Project(BaseModel):
    name: str = ""
    year: str = ""
    description: str = ""


class Profile(BaseModel):
    """A candidate's professional profile.

    Fields are optional with empty defaults so that a partial profile (as
    built up incrementally by the CLI ``configure`` command, or a minimal API
    payload) still validates. The API layer can layer stricter validation on
    top if needed.
    """

    name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    linkedin: str = ""
    website: str = ""
    skills: list[str] = Field(default_factory=list)
    experience_summary: str = ""
    education: str = ""
    experiences: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)


class JobData(BaseModel):
    """Structured information parsed out of a raw job description."""

    title: str = "Software Developer"
    company: str = "Company"
    location: str = "Remote"
    requirements: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    date: str = ""


class GenerateRequest(BaseModel):
    """Everything needed to generate a CV and cover letter for one job."""

    job_description: str
    profile: Profile
    skill_modification_level: float = Field(default=0.5, ge=0.0, le=1.0)
    dry_run: bool = False


class GenerationResult(BaseModel):
    """Rendered artifacts. PDFs are returned as bytes so the caller (CLI or
    API) decides how to deliver them — the core never writes to disk."""

    cv_html: str
    cv_pdf: bytes
    cover_html: str
    cover_pdf: bytes
    job_data: JobData
