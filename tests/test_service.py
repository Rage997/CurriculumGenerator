from curriculum_generator.models import GenerateRequest
from curriculum_generator.service import CurriculumService


def test_generate_produces_pdfs(settings, profile, fake_llm, cv_json, cover_json):
    llm = fake_llm([cv_json, cover_json])
    service = CurriculumService(settings, llm=llm)
    request = GenerateRequest(
        job_description="Job Title: Backend Engineer\nCompany: Acme\nSkills: Python, Django",
        profile=profile,
    )
    result = service.generate(request)
    assert result.cv_pdf.startswith(b"%PDF")
    assert result.cover_pdf.startswith(b"%PDF")
    assert "Test Candidate" in result.cv_html
    assert len(llm.prompts) == 2


def test_generate_dry_run_skips_llm(settings, profile, fake_llm):
    llm = fake_llm([])  # would raise StopIteration if chat() were called
    service = CurriculumService(settings, llm=llm)
    request = GenerateRequest(job_description="Any job", profile=profile, dry_run=True)
    result = service.generate(request)
    assert result.cv_pdf.startswith(b"%PDF")
    assert len(llm.prompts) == 0


def test_generate_injects_job_skills_into_prompt(settings, profile, fake_llm, cv_json, cover_json):
    llm = fake_llm([cv_json, cover_json])
    service = CurriculumService(settings, llm=llm)
    request = GenerateRequest(
        job_description="Job Title: Backend Engineer\nSkills: Python, Kubernetes, Docker",
        profile=profile,
        skill_modification_level=1.0,
    )
    service.generate(request)
    assert "Kubernetes" in llm.prompts[0]
    assert "Docker" in llm.prompts[0]
