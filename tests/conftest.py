"""Shared fixtures and test doubles for the test suite.

The LLM is never called for real: tests inject a :class:`FakeLLM` (which
satisfies the ``LLMBackend`` protocol) with canned JSON responses.
"""

from pathlib import Path

import pytest

from curriculum_generator.config import Settings
from curriculum_generator.models import Profile

PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"

CV_JSON = (
    '{"education": "Bachelor of Science in Computer Science\\n'
    'University of Technology\\n2015\\nZurich", '
    '"experience": "Senior Python Developer\\n'
    'Tech Innovations Inc., Jan 2020 - Present\\n'
    'Led the development of scalable web applications.", '
    '"projects": "E-commerce Platform\\n2023\\n'
    'Built a full-featured e-commerce platform.", '
    '"skills": "Programming Languages: Python, JavaScript\\n'
    'Web Frameworks: Django, Flask"}'
)

COVER_JSON = '{"body": "Dear Hiring Manager, I am writing to express my interest."}'


class FakeLLM:
    """Implements the LLMBackend protocol with canned responses."""

    def __init__(self, responses):
        self._responses = iter(responses)
        self.prompts = []

    def check(self):
        pass

    def chat(self, prompt):
        self.prompts.append(prompt)
        return next(self._responses)


@pytest.fixture
def settings():
    return Settings(templates_dir=str(TEMPLATES_DIR))


@pytest.fixture
def profile():
    return Profile(
        name="Test Candidate",
        email="test@example.com",
        phone="+123456789",
        address="Test City",
        skills=["Python", "Django"],
        experience_summary="5 years in web development",
        education="Bachelor in CS",
        experiences=[{
            "title": "Senior Developer",
            "company": "Acme",
            "dates": "2020 - Present",
            "description": "Built web apps.",
        }],
        projects=[{
            "name": "Demo App",
            "year": "2023",
            "description": "A demo.",
        }],
    )


@pytest.fixture
def fake_llm():
    """Factory: ``fake_llm([cv_json, cover_json])`` -> a FakeLLM."""
    def _make(responses):
        return FakeLLM(responses)
    return _make


@pytest.fixture
def cv_json():
    return CV_JSON


@pytest.fixture
def cover_json():
    return COVER_JSON
