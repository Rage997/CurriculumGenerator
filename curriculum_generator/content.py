"""Prompt building, LLM-response parsing, and CV / cover-letter generation.

The prompt text and the response-parsing logic live here, separated from the
network call (which is delegated to the injected :class:`~.llm.LLMBackend`).
That split is what makes the generation logic unit-testable without a server.
"""

import json
import logging

from markupsafe import Markup

from .format import format_education, format_experience, format_projects, format_skills
from .llm import LLMBackend, LLMResponseError
from .models import JobData, Profile

logger = logging.getLogger(__name__)


def modified_skills(profile: Profile, job_data: JobData, level: float) -> list[str]:
    """Blend the candidate's skills with skills found in the job description.

    ``level`` (0.0-1.0) controls how many job skills are folded in. Shared by
    the CV and cover-letter prompts (previously duplicated in both).
    """
    job_skills = job_data.technologies
    user_skills = list(profile.skills)
    num_to_add = int(len(job_skills) * level)
    skills_to_add = job_skills[:num_to_add]
    return user_skills + [s for s in skills_to_add if s not in user_skills]


def build_cv_prompt(profile: Profile, job_text: str, skills: list[str]) -> str:
    experiences_text = '\n'.join(
        f"- {exp.title} at {exp.company} ({exp.dates}): {exp.description}"
        for exp in profile.experiences
    )
    projects_text = '\n'.join(
        f"- {proj.name} ({proj.year}): {proj.description}"
        for proj in profile.projects
    )
    return rf"""Based on this job description and the user's profile, generate professional CV content tailored to the job. Select and adapt the user's experiences and projects to best match the job requirements.

    User Profile:
    - Skills: {', '.join(skills)}
    - Experience Summary: {profile.experience_summary}
    - Experiences:
    {experiences_text}
    - Projects:
    {projects_text}
    - Education: {profile.education}

    Job Description:
    {job_text}

    Reply with a valid JSON object containing the following keys:
    - "education": Plain text for the education section (e.g., "Bachelor of Science in Computer Science\nUniversity of Technology\n2015\nComputer Science")
    - "experience": Plain text for the experience section (e.g., "Senior Python Developer\nTech Innovations Inc., Jan 2020 – Present\nLed the development...")
    - "projects": Plain text for the projects section (e.g., "E-commerce Platform\n2023\nDeveloped a full-featured e-commerce platform...")
    - "skills": Plain text for the skills section (e.g., "Programming Languages: Python, JavaScript, PHP\nWeb Frameworks: Django, Flask\n...")

    Do not wrap the JSON in markdown code blocks. Output only the JSON object.

    Focus on tailoring content to match the job requirements. Use professional language and quantify achievements where possible."""


def build_cover_letter_prompt(profile: Profile, job_data: JobData, skills: list[str]) -> str:
    experiences_text = '\n'.join(
        f"- {exp.title} at {exp.company} ({exp.dates}): {exp.description}"
        for exp in profile.experiences
    )
    return f"""Write a compelling, personalized cover letter for the {job_data.title} position at {job_data.company}.

    User Profile:
    - Name: {profile.name}
    - Skills: {', '.join(skills)}
    - Experience Summary: {profile.experience_summary}
    - Experiences:
    {experiences_text}
    - Education: {profile.education}

    Job Details:
    - Position: {job_data.title}
    - Company: {job_data.company}
    - Location: {job_data.location}
    - Key Requirements: {', '.join(job_data.requirements[:3]) if job_data.requirements else 'Python development experience'}
    - Key Responsibilities: {', '.join(job_data.responsibilities[:2]) if job_data.responsibilities else 'Web application development'}

    Reply with a valid JSON object containing the key "body" with the cover letter body text (2-3 paragraphs). Do not include salutation or closing. Do not wrap the JSON in markdown code blocks. Output only the JSON object. Make it highly personalized by:

    1. First paragraph: Formally express enthusiasm for the specific role and company.
    2. Second paragraph: Connect your specific experience and skills to the job requirements and responsibilities
    3. Third paragraph: Explain why you're interested in this company specifically and what you can contribute

    Use professional, conversational language that sounds natural, not like a template. Reference specific technologies, requirements, and company details from the job description. Show genuine interest and specific knowledge about the role."""


def parse_llm_json(text: str) -> dict:
    """Robustly extract a JSON object from a raw LLM response.

    Handles the common failure modes: markdown code fences, surrounding
    prose, and stray control characters. Raises :class:`LLMResponseError` if
    no valid JSON object can be recovered.
    """
    text = text.strip()
    if text.startswith('```json'):
        text = text[7:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()
    # Drop control characters except newline and tab.
    text = ''.join(c for c in text if ord(c) >= 32 or c in '\n\t')
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end > start:
        text = text[start:end]
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMResponseError(f"LLM did not return valid JSON: {e}") from e


def generate_cv_content(
    job_text: str,
    profile: Profile,
    job_data: JobData,
    skill_modification_level: float,
    llm: LLMBackend,
) -> Markup:
    """Generate the CV body as an HTML fragment."""
    logger.info("Starting CV generation")
    skills = modified_skills(profile, job_data, skill_modification_level)
    prompt = build_cv_prompt(profile, job_text, skills)
    response = llm.chat(prompt)
    data = parse_llm_json(response)
    logger.info("CV JSON parsed successfully")
    cv_content = f"""
        <div class="section">
            <div class="section-title">EDUCATION</div>
            {format_education(data['education'])}
        </div>

        <div class="section">
            <div class="section-title">EXPERIENCE</div>
            {format_experience(data['experience'])}
        </div>

        <div class="section">
            <div class="section-title">PROJECTS</div>
            {format_projects(data['projects'])}
        </div>

        <div class="section">
            <div class="section-title">SKILLS</div>
            {format_skills(data['skills'])}
        </div>
    """
    logger.info("CV content generated")
    return Markup(cv_content)


def generate_cover_letter_content(
    job_text: str,
    profile: Profile,
    job_data: JobData,
    skill_modification_level: float,
    llm: LLMBackend,
) -> str:
    """Generate the cover letter body text."""
    logger.info("Starting cover letter generation")
    skills = modified_skills(profile, job_data, skill_modification_level)
    prompt = build_cover_letter_prompt(profile, job_data, skills)
    response = llm.chat(prompt)
    data = parse_llm_json(response)
    logger.info("Cover letter JSON parsed successfully")
    return data['body']
