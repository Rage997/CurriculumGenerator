from curriculum_generator.parser import extract_skills_from_text, parse_job_description


def test_extract_skills_finds_known_keywords():
    text = "We need a Python developer with Django and PostgreSQL. Docker and Kubernetes a plus."
    skills = extract_skills_from_text(text)
    for expected in ("Python", "Django", "PostgreSQL", "Docker", "Kubernetes"):
        assert expected in skills


def test_extract_skills_case_insensitive_and_no_false_positives():
    assert extract_skills_from_text("python") == ["Python"]
    assert extract_skills_from_text("nothing technical here") == []


def test_parse_job_description_with_explicit_fields():
    text = (
        "Job Title: Senior Backend Engineer\n"
        "Company: Acme Corp\n"
        "Location: Berlin\n"
        "\n"
        "Responsibilities:\n"
        "- Design APIs\n"
        "- Mentor juniors\n"
        "\n"
        "Requirements:\n"
        "- 3+ years Python\n"
        "- Experience with PostgreSQL\n"
    )
    job = parse_job_description(text)
    assert job.title == "Senior Backend Engineer"
    assert job.company == "Acme Corp"
    assert job.location == "Berlin"
    assert "Design APIs" in job.responsibilities
    assert "Mentor juniors" in job.responsibilities
    assert "3+ years Python" in job.requirements
    assert "PostgreSQL" in job.technologies


def test_parse_job_description_defaults_for_unstructured_text():
    job = parse_job_description("We are hiring great people to join our team.")
    assert job.title == "Software Developer"
    assert job.company == "Company"
    assert job.location == "Remote"
    assert job.technologies == []
