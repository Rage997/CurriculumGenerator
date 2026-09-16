"""Command-line interface.

A thin wrapper over the core :class:`~.service.CurriculumService`. The CLI is
a local-dev convenience: it reads the candidate profile from
``candidate_config.yaml`` and server settings from ``.env`` (both in the
working directory) and writes generated files to ``output/``. The service
itself has no knowledge of any of these files — that boundary is what makes
the same core reusable by an API.
"""

import logging
import os
from pathlib import Path

import click
import yaml

from .config import Settings
from .llm import LLMClient, LLMError
from .models import GenerateRequest, Profile
from .service import CurriculumService

ENV_FILE = Path('.env')
CONFIG_FILE = Path('candidate_config.yaml')


def load_profile() -> dict:
    if CONFIG_FILE.exists():
        return yaml.safe_load(CONFIG_FILE.read_text()) or {}
    return {}


def save_profile(profile: dict) -> None:
    CONFIG_FILE.write_text(yaml.safe_dump(profile, sort_keys=False))


def set_env_value(key: str, value: str) -> None:
    """Set a key in ``.env``, preserving comments and existing entries.

    CLI-only convenience for local development; the service never does this.
    """
    lines = ENV_FILE.read_text().splitlines() if ENV_FILE.exists() else []
    for i, line in enumerate(lines):
        if line.strip().startswith(f'{key}='):
            lines[i] = f'{key}={value}'
            ENV_FILE.write_text('\n'.join(lines) + '\n')
            return
    if lines and lines[-1] != '':
        lines.append('')
    lines.append(f'{key}={value}')
    ENV_FILE.write_text('\n'.join(lines) + '\n')
    os.environ[key] = value


def write_outputs(result, output_prefix: str, output_dir: str) -> None:
    out = Path(output_dir)
    cv_dir = out / 'cv'
    cover_dir = out / 'cover_letter'
    cv_dir.mkdir(parents=True, exist_ok=True)
    cover_dir.mkdir(parents=True, exist_ok=True)
    (cv_dir / f'{output_prefix}.html').write_text(result.cv_html)
    (cv_dir / f'{output_prefix}.pdf').write_bytes(result.cv_pdf)
    (cover_dir / f'{output_prefix}.html').write_text(result.cover_html)
    (cover_dir / f'{output_prefix}.pdf').write_bytes(result.cover_pdf)


def _setup_logging() -> None:
    # Log to stderr at INFO. The core logs only operational messages (no
    # prompts, responses, or profile data), so this is safe to leave on.
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )
    # WeasyPrint is chatty at INFO (render pipeline steps + progress); keep
    # only warnings and above so CLI output stays readable.
    logging.getLogger("weasyprint").setLevel(logging.WARNING)
    logging.getLogger("weasyprint.progress").setLevel(logging.WARNING)


@click.group()
def cli():
    """Curriculum AI generator (local llama.cpp backend)."""


@cli.command()
@click.option('--model', help='Model name served by llama.cpp (LLM_MODEL)')
@click.option('--base-url', help='llama.cpp server URL (LLM_BASE_URL)')
@click.option('--templates-dir', help='Directory for HTML templates (TEMPLATES_DIR)')
@click.option('--output-dir', help='Directory for generated files (OUTPUT_DIR)')
@click.option('--name', help='Your full name')
@click.option('--email', help='Your email address')
@click.option('--phone', help='Your phone number')
@click.option('--address', help='Your address')
@click.option('--skills', help='Your skills (comma-separated)')
@click.option('--experience-summary', help='Your experience summary')
@click.option('--education', help='Your education')
def configure(model, base_url, templates_dir, output_dir, name, email, phone,
              address, skills, experience_summary, education):
    """Configure the generator (.env for server settings, YAML for profile)."""
    if model:
        set_env_value('LLM_MODEL', model)
    if base_url:
        set_env_value('LLM_BASE_URL', base_url)
    if templates_dir:
        set_env_value('TEMPLATES_DIR', templates_dir)
    if output_dir:
        set_env_value('OUTPUT_DIR', output_dir)

    profile = load_profile()
    if name:
        profile['name'] = name
    if email:
        profile['email'] = email
    if phone:
        profile['phone'] = phone
    if address:
        profile['address'] = address
    if skills:
        profile['skills'] = [s.strip() for s in skills.split(',')]
    if experience_summary:
        profile['experience_summary'] = experience_summary
    if education:
        profile['education'] = education
    if profile:
        save_profile(profile)
    click.echo("Configuration saved.")


@cli.command()
def models():
    """List models served by llama.cpp."""
    config = Settings()
    if not config.model:
        click.echo(
            "No model configured. Set LLM_MODEL in .env or run: "
            "curriculum-generator configure --model <name>"
        )
        return
    client = LLMClient(config)
    try:
        available = client.list_models()
    except LLMError as e:
        click.echo(str(e), err=True)
        return
    if available:
        click.echo("Available models:")
        for m in available:
            click.echo(f"  - {m}")
    else:
        click.echo("No models found.")


@cli.command()
@click.argument('job_description', type=click.File('r'))
@click.option('--output', '-o', default='generated', help='Output file prefix')
@click.option('--dry-run', is_flag=True, help='Generate templates without AI content')
@click.option('--skill-modification-level', type=float, default=0.5,
              help='Skill modification level (0.0 to 1.0)')
def generate(job_description, output, dry_run, skill_modification_level):
    """Generate CV and cover letter from a job description file."""
    _setup_logging()
    config = Settings()
    try:
        profile = Profile.model_validate(load_profile())
    except Exception as e:
        click.echo(f"Invalid profile in {CONFIG_FILE}: {e}", err=True)
        raise SystemExit(1)

    request = GenerateRequest(
        job_description=job_description.read(),
        profile=profile,
        skill_modification_level=skill_modification_level,
        dry_run=dry_run,
    )
    service = CurriculumService(config)
    try:
        result = service.generate(request)
    except LLMError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    write_outputs(result, output, config.output_dir)
    click.echo(
        f"Generated CV and cover letter in "
        f"{config.output_dir}/cv and {config.output_dir}/cover_letter"
    )
