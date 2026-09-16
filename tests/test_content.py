import pytest

from curriculum_generator.content import modified_skills, parse_llm_json
from curriculum_generator.llm import LLMResponseError
from curriculum_generator.models import JobData, Profile


def test_parse_llm_json_clean():
    assert parse_llm_json('{"body": "hello"}') == {"body": "hello"}


def test_parse_llm_json_markdown_fenced():
    assert parse_llm_json('```json\n{"body": "hello"}\n```') == {"body": "hello"}


def test_parse_llm_json_embedded_in_prose():
    text = 'Sure! Here is the JSON you asked for:\n{"body": "hello"}\nHope that helps.'
    assert parse_llm_json(text) == {"body": "hello"}


def test_parse_llm_json_invalid_raises():
    with pytest.raises(LLMResponseError):
        parse_llm_json("this is not json at all")


def test_modified_skills_folds_in_job_skills():
    profile = Profile(skills=["Python"])
    job_data = JobData(technologies=["Django", "Flask", "PostgreSQL"])
    # level 0.5 of 3 skills -> first job skill (Django) is folded in
    assert modified_skills(profile, job_data, 0.5) == ["Python", "Django"]


def test_modified_skills_avoids_duplicates():
    profile = Profile(skills=["Python"])
    job_data = JobData(technologies=["Python", "Django"])
    assert modified_skills(profile, job_data, 1.0) == ["Python", "Django"]


def test_modified_skills_level_zero_keeps_profile_only():
    profile = Profile(skills=["Python"])
    job_data = JobData(technologies=["Django", "Flask"])
    assert modified_skills(profile, job_data, 0.0) == ["Python"]
