# Curriculum AI Generator

A tool to generate customized CVs and cover letters using a local LLM served by [llama.cpp](https://github.com/ggml-org/llama.cpp) (OpenAI-compatible API) based on job descriptions and user profiles.

It can be used two ways, both built on the same core:

- a **CLI** for local use, and
- an **HTTP API** (FastAPI) so other services can call it.

## How it works

1. A job description and a candidate profile are combined into prompts.
2. The LLM produces tailored CV sections and a cover-letter body (as JSON).
3. The content is rendered through Jinja2 HTML templates.
4. [WeasyPrint](https://doc.courtbouillon.org/weasyprint/) converts the HTML to PDF.

## Installation

1. Install [uv](https://docs.astral.sh/uv/), then install dependencies (this also installs the `curriculum-generator` CLI):
   ```bash
   uv sync
   ```

2. Install WeasyPrint's system libraries (for PDF rendering):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
       libffi-dev shared-mime-info fonts-dejavu-core
   ```

3. Start a llama.cpp server with your model:
   ```bash
   # Install llama.cpp from https://github.com/ggml-org/llama.cpp
   llama-server -m /path/to/your/model.gguf --port 8080
   ```

## Configuration

All settings come from environment variables, optionally seeded from a local `.env` file (see the example below for the full list):

```bash
# llama.cpp server (OpenAI-compatible API)
LLM_BASE_URL=http://localhost:8080
LLM_MODEL=dolphin3:8b
# Optional API key, only needed if the LLM server requires auth
LLM_API_KEY=
# Generation settings
LLM_MAX_TOKENS=2048
# Shared server: requests can queue behind other clients, so keep this generous
LLM_TIMEOUT=1800
# Set to true to let thinking models (e.g. Qwen3) reason before answering
LLM_ENABLE_THINKING=false

# Project settings
OUTPUT_DIR=output
TEMPLATES_DIR=templates

# HTTP API (optional; empty disables auth)
SERVICE_API_KEY=
```

The user profile (name, skills, experiences, projects, ...) lives in `candidate_config.yaml` for the CLI. The API takes the profile in the request body instead.

## CLI usage

All commands run through uv: `uv run curriculum-generator ...`

### Configure user profile and server settings
```bash
uv run curriculum-generator configure \
  --name "John Doe" \
  --email "john.doe@example.com" \
  --phone "+123456789" \
  --address "123 Main St, Springfield" \
  --skills "Python,C++,JavaScript,SQL,Django" \
  --experience-summary "5 years in realtime rendering" \
  --education "Bachelor in Informatics, Master in Computational Science" \
  --model qwen3:8b \
  --base-url http://localhost:8080
```

Profile fields are written to `candidate_config.yaml`; `--model` and `--base-url` are written to `.env`.

### List available models
```bash
uv run curriculum-generator models
```

### Generate CV and cover letter
```bash
uv run curriculum-generator generate job_description.txt --output my_application
```

For testing without AI generation:
```bash
uv run curriculum-generator generate job_description.txt --output test --dry-run
```

This creates `my_application.html` and `my_application.pdf` in the `output/cv/` and `output/cover_letter/` directories.

## HTTP API

The same core is exposed as a FastAPI service. Start it with:

```bash
uv run uvicorn curriculum_generator.api.app:app --host 0.0.0.0 --port 8000
# or
uv run python -m curriculum_generator.api   # host/port from HOST / PORT env vars
```

Interactive OpenAPI docs are served at `http://localhost:8000/docs`.

### Endpoints

- `GET /health` — liveness check (no auth; safe to expose to load balancers).
- `POST /generate` — generate a CV and cover letter.

`POST /generate` accepts a `GenerateRequest`:

```json
{
  "job_description": "Senior Backend Engineer at Acme...",
  "profile": {
    "name": "John Doe",
    "email": "john.doe@example.com",
    "skills": ["Python", "Django"],
    "experience_summary": "5+ years in web development",
    "education": "Bachelor in Computer Science",
    "experiences": [
      { "title": "Senior Developer", "company": "Acme", "dates": "2020 - Present", "description": "..." }
    ],
    "projects": [ { "name": "Demo", "year": "2023", "description": "..." } ]
  },
  "skill_modification_level": 0.5,
  "dry_run": false
}
```

and returns the rendered documents (PDFs as base64) plus the HTML and parsed job data:

```json
{
  "cv_pdf": "<base64>",
  "cover_pdf": "<base64>",
  "cv_html": "...",
  "cover_html": "...",
  "job_data": { "title": "Senior Backend Engineer", "company": "Acme", "location": "..." }
}
```

### Authentication

Set `SERVICE_API_KEY` to require a bearer token on `/generate`:

```bash
curl -X POST http://localhost:8000/generate \
  -H "Authorization: Bearer $SERVICE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @payload.json
```

When `SERVICE_API_KEY` is empty, auth is disabled — fine for local development, not for a real deployment.

> **Note:** `POST /generate` is synchronous — it blocks until the LLM calls and PDF rendering finish (which can take a while on a local model). For concurrent, long-running workloads the next step is a job pattern (submit → poll → download).

## Project structure

- `curriculum_generator/` — the package
  - `config.py` — settings (environment variables)
  - `models.py` — Pydantic models (profile, request, result)
  - `parser.py` — job-description parsing and skill extraction
  - `content.py` — prompt building and LLM-response parsing
  - `format.py` — CV section HTML formatters
  - `llm.py` — llama.cpp client and typed errors
  - `render.py` — Jinja2 + WeasyPrint rendering (returns PDF bytes)
  - `service.py` — orchestrator (`GenerateRequest` → `GenerationResult`)
  - `cli.py` — the Click CLI (thin wrapper over the service)
  - `api/` — the FastAPI service (app factory, routes, dependencies)
- `templates/cv/`, `templates/cover_letter/` — HTML templates
- `tests/` — unit and integration tests (LLM is mocked)
- `output/cv/`, `output/cover_letter/` — generated files (CLI)
- `.env` — server and generation settings
- `candidate_config.yaml` — user profile (CLI)

The core (`service.py` and below) has no CLI, API, or disk dependencies: it takes a `GenerateRequest` and returns rendered bytes. The CLI and the API are two thin consumers of that core.

## Running the tests

```bash
uv run pytest
```

## TODOs

- [ ] Reliable CV HTML template (the current one works but could be improved)
- [ ] Improve the AI prompts (generated data quality)
- [ ] Bundle Font Awesome locally so PDF rendering works offline (the CV template currently pulls it from a CDN)
- [ ] Move `POST /generate` to an async job pattern (submit → poll → download) for concurrent/long-running workloads
