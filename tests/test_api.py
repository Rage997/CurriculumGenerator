import base64
from pathlib import Path

from fastapi.testclient import TestClient

from curriculum_generator.api.app import create_app
from curriculum_generator.api.deps import get_service
from curriculum_generator.config import Settings
from curriculum_generator.llm import LLMConnectionError
from curriculum_generator.service import CurriculumService

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def make_client(settings, llm=None):
    app = create_app(settings)
    if llm is not None:
        app.dependency_overrides[get_service] = lambda: CurriculumService(settings, llm=llm)
    return TestClient(app)


def test_health(settings):
    client = make_client(settings)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_generate_returns_pdfs(settings, profile, fake_llm, cv_json, cover_json):
    llm = fake_llm([cv_json, cover_json])
    client = make_client(settings, llm=llm)
    payload = {
        "job_description": "Job Title: Backend Engineer\nCompany: Acme\nSkills: Python",
        "profile": profile.model_dump(),
    }
    resp = client.post("/generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert base64.b64decode(data["cv_pdf"]).startswith(b"%PDF")
    assert base64.b64decode(data["cover_pdf"]).startswith(b"%PDF")
    assert data["job_data"]["title"] == "Backend Engineer"


def test_generate_rejects_invalid_profile(settings):
    client = make_client(settings)
    payload = {"job_description": "x", "profile": {"skills": "not-a-list"}}
    resp = client.post("/generate", json=payload)
    assert resp.status_code == 422


def test_generate_requires_auth_when_key_set(profile, fake_llm, cv_json, cover_json):
    settings = Settings(templates_dir=str(TEMPLATES_DIR), service_api_key="secret")
    llm = fake_llm([cv_json, cover_json])
    client = make_client(settings, llm=llm)
    payload = {"job_description": "x", "profile": profile.model_dump()}
    assert client.post("/generate", json=payload).status_code == 401
    assert client.post(
        "/generate", json=payload, headers={"Authorization": "Bearer wrong"}
    ).status_code == 401
    ok = client.post("/generate", json=payload, headers={"Authorization": "Bearer secret"})
    assert ok.status_code == 200


def test_generate_maps_llm_error_to_502(settings, profile):
    class FailingLLM:
        def check(self):
            raise LLMConnectionError("backend down")

        def chat(self, prompt):
            raise LLMConnectionError("backend down")

    client = make_client(settings, llm=FailingLLM())
    payload = {"job_description": "x", "profile": profile.model_dump()}
    resp = client.post("/generate", json=payload)
    assert resp.status_code == 502
