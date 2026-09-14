#!/usr/bin/env python3
"""
Curriculum AI Generator using a local llama.cpp server (OpenAI-compatible API)
"""

import click
import yaml
import os
import json
import logging
from pathlib import Path
import requests
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

def escape_latex(text):
    """Escape LaTeX special characters in text."""
    return (text.replace('\\', '\\\\')
                .replace('{', '\\{')
                .replace('}', '\\}')
                .replace('&', '\\&')
                .replace('%', '\\%')
                .replace('$', '\\$')
                .replace('#', '\\#')
                .replace('_', '\\_')
                .replace('^', '\\^{}')
                .replace('~', '\\~{}'))

# Set up logging
logging.basicConfig(
    filename=Path(__file__).parent / 'curriculum_generator.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load configuration: .env for server/generation settings, YAML for the user profile
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / '.env')

ENV_FILE = BASE_DIR / '.env'
CONFIG_FILE = BASE_DIR / 'candidate_config.yaml'


def get_config():
    """Server and generation settings from environment variables (see .env)."""
    return {
        'base_url': os.environ.get('LLM_BASE_URL', 'http://localhost:8080').rstrip('/'),
        'model': os.environ.get('LLM_MODEL', ''),
        'api_key': os.environ.get('LLM_API_KEY', ''),
        'max_tokens': int(os.environ.get('LLM_MAX_TOKENS', '2048')),
        'timeout': int(os.environ.get('LLM_TIMEOUT', '300')),
        'enable_thinking': os.environ.get('LLM_ENABLE_THINKING', 'false').lower() == 'true',
        'output_dir': os.environ.get('OUTPUT_DIR', 'output'),
        'templates_dir': os.environ.get('TEMPLATES_DIR', 'templates'),
    }


def load_profile():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            profile = yaml.safe_load(f)
        logging.info(f"Loaded profile from {CONFIG_FILE}")
        return profile or {}
    logging.info("Profile file not found")
    return {}


def save_profile(profile):
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(profile, f)
    logging.info(f"Saved profile to {CONFIG_FILE}")


def set_env_value(key, value):
    """Set a key in .env, preserving comments and existing entries."""
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

@click.group()
def cli():
    pass

@cli.command()
@click.option('--model', help='Model name served by llama.cpp (LLM_MODEL)')
@click.option('--base-url', help='llama.cpp server URL (LLM_BASE_URL)')
@click.option('--templates-dir', help='Directory for LaTeX templates (TEMPLATES_DIR)')
@click.option('--output-dir', help='Directory for generated files (OUTPUT_DIR)')
@click.option('--name', help='Your full name')
@click.option('--email', help='Your email address')
@click.option('--phone', help='Your phone number')
@click.option('--address', help='Your address')
@click.option('--skills', help='Your skills (comma-separated)')
@click.option('--experience-summary', help='Your experience summary')
@click.option('--education', help='Your education')
def configure(model, base_url, templates_dir, output_dir, name, email, phone, address, skills, experience_summary, education):
    """Configure the curriculum generator (.env for server settings, YAML for profile)"""
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
    """List models served by llama.cpp"""
    if not check_llama():
        return
    available_models = list_models()
    if available_models:
        click.echo("Available models:")
        for model in available_models:
            click.echo(f"  - {model}")
    else:
        click.echo("No models found.")

@cli.command()
@click.argument('job_description', type=click.File('r'))
@click.option('--output', '-o', help='Output file prefix')
@click.option('--dry-run', is_flag=True, help='Generate templates without AI content')
@click.option('--skill-modification-level', type=float, default=0.5, help='Level of skill modification based on job description (0.0 to 1.0)')
def generate(job_description, output, dry_run, skill_modification_level):
    """Generate CV and cover letter from job description"""
    config = get_config()
    profile = load_profile()
    job_text = job_description.read()
    logging.info(f"Generating documents for job: {job_description.name}")
    logging.debug(f"Job text: {job_text[:500]}...")  # Log first 500 chars

    if dry_run:
        cv_content = "Education:\nSample education\n\nExperience:\nSample experience\n\nSkills:\nSample skills"
        cover_content = "Sample cover letter content."
    else:
        # Generate CV
        click.echo("Generating CV...")
        cv_content = generate_cv(job_text, config, profile, skill_modification_level)
        if cv_content is None:
            return
        click.echo("CV generated.")

        # Generate cover letter
        click.echo("Generating cover letter...")
        cover_content = generate_cover_letter(job_text, config, profile, skill_modification_level)
        if cover_content is None:
            return
        click.echo("Cover letter generated.")

    # Parse job description for personalization
    job_data = parse_job_description(job_text)
    logging.debug(f"Parsed job data: {job_data}")

    # Render HTML and generate PDFs
    click.echo("Rendering HTML and generating PDFs...")
    logging.info("Rendering HTML templates and generating PDFs")
    render_html(cv_content, cover_content, job_data, output or 'generated', config, profile)

    click.echo(f"Generated CV and cover letter in {config['output_dir']}/cv and {config['output_dir']}/cover_letter")
    logging.info(f"Generation completed. Output in {config['output_dir']}")


def llama_headers():
    """Headers for llama.cpp requests, including auth when an API key is set."""
    headers = {'Content-Type': 'application/json'}
    api_key = os.environ.get('LLM_API_KEY', '')
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    return headers


def check_llama():
    """Check if the llama.cpp server is running and accessible"""
    config = get_config()
    if not config['model']:
        click.echo("No model configured. Set LLM_MODEL in .env or run: curriculum configure --model <name>")
        return False
    try:
        requests.get(f"{config['base_url']}/v1/models", headers=llama_headers(), timeout=10)
        return True
    except Exception as e:
        click.echo(f"Error connecting to llama.cpp at {config['base_url']}: {e}")
        click.echo("Make sure the llama.cpp server is running (e.g. llama-server -m model.gguf).")
        return False


def list_models():
    """List models served by llama.cpp"""
    config = get_config()
    try:
        resp = requests.get(f"{config['base_url']}/v1/models", headers=llama_headers(), timeout=10)
        resp.raise_for_status()
        return [m['id'] for m in resp.json().get('data', [])]
    except Exception as e:
        click.echo(f"Error listing models: {e}")
        return []


def llama_chat(prompt, config):
    """Send a prompt to the llama.cpp server via the OpenAI-compatible chat API."""
    payload = {
        'model': config['model'],
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': config['max_tokens'],
        'temperature': 0.2,
    }
    if not config['enable_thinking']:
        # Qwen3-style thinking models burn the token budget on hidden reasoning
        payload['chat_template_kwargs'] = {'enable_thinking': False}
    resp = requests.post(
        f"{config['base_url']}/v1/chat/completions",
        headers=llama_headers(),
        json=payload,
        timeout=config['timeout'],
    )
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content']

def format_education(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) >= 3:
        degree = lines[0]
        university = lines[1]
        year = lines[2]
        location = lines[3] if len(lines) > 3 else 'Location'
        education_html = f"""
            <div class="education-item">
                <div class="education-subheading">
                    <div class="education-row">
                        <div class="education-university">{university}</div>
                        <div class="education-year">{year}</div>
                    </div>
                    <div class="education-row">
                        <div class="education-degree">{degree}</div>
                        <div class="education-location">{location}</div>
                    </div>
                </div>
            </div>
        """.strip()
        return Markup(education_html)
    return Markup(text)  # Return as Markup even if simple text

def format_experience(text):
    jobs = text.split('\n\n')
    result = ""
    for job in jobs:
        lines = [line.strip() for line in job.split('\n') if line.strip()]
        if len(lines) >= 2:
            title = lines[0]
            company_dates = lines[1]
            # Parse company and dates
            parts = company_dates.split(', ')
            if len(parts) >= 2:
                company = parts[0]
                dates = ', '.join(parts[1:])
            else:
                company = company_dates
                dates = ''
            location = 'Remote'  # Default location
            description = ' '.join(lines[2:])
            items = [item.strip() for item in description.split('. ') if item.strip()]
            # Clean up bullet points that start with "- "
            cleaned_items = []
            for item in items:
                if item.startswith('- '):
                    item = item[2:]
                cleaned_items.append(item)
            item_str = ''.join(f"<li>{item}</li>" for item in cleaned_items)
            result += f"""
                <div class="experience-item">
                    <div class="experience-subheading">
                        <div class="experience-row">
                            <div class="experience-company">{company}</div>
                            <div class="experience-dates">{dates}</div>
                        </div>
                        <div class="experience-row">
                            <div class="experience-title">{title}</div>
                            <div class="experience-location">{location}</div>
                        </div>
                    </div>
                    <div class="experience-description">
                        <ul>{item_str}</ul>
                    </div>
                </div>
            """.strip()
    return Markup(f'<div class="experience-list">{result}</div>')

def format_projects(text):
    projects = text.split('\n\n')
    result = ""
    for proj in projects:
        lines = [line.strip() for line in proj.split('\n') if line.strip()]
        if len(lines) >= 2:
            name = lines[0]
            year = lines[1]
            description = ' '.join(lines[2:])
            items = [item.strip() for item in description.split('. ') if item.strip()]
            # Clean up bullet points that start with "- "
            cleaned_items = []
            for item in items:
                if item.startswith('- '):
                    item = item[2:]
                cleaned_items.append(item)
            item_str = ''.join(f"<li>{item}</li>" for item in cleaned_items)
            result += f"""
                <div class="project-item">
                    <div class="project-subheading">
                        <div class="project-row">
                            <div class="project-name">{name} ({year})</div>
                            <div></div>
                        </div>
                    </div>
                    <div class="project-description">
                        <ul>{item_str}</ul>
                    </div>
                </div>
            """.strip()
    return Markup(f'<div class="projects-list">{result}</div>')

def format_skills(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    half = (len(lines) + 1) // 2
    col1 = ''.join(f"<li>{line}</li>" for line in lines[:half])
    col2 = ''.join(f"<li>{line}</li>" for line in lines[half:])
    skills_html = f'''
        <div class="skills">
        <ul>{col1}</ul>
        <ul>{col2}</ul>
        </div>
    '''.strip()
    return Markup(skills_html)

def generate_cv(job_text, config, profile, skill_modification_level):
    """Generate CV content using llama.cpp"""
    logging.info("Starting CV generation")
    if not check_llama():
        logging.error("llama.cpp server not available")
        return None
    user = profile
    experiences_text = '\n'.join([f"- {exp['title']} at {exp['company']} ({exp['dates']}): {exp['description']}" for exp in user.get('experiences', [])])
    projects_text = '\n'.join([f"- {proj['name']} ({proj['year']}): {proj['description']}" for proj in user.get('projects', [])])

    # Parse job to get skills
    job_data = parse_job_description(job_text)
    job_skills = job_data['technologies']
    user_skills = user.get('skills', [])
    num_to_add = int(len(job_skills) * skill_modification_level)
    skills_to_add = job_skills[:num_to_add]
    modified_skills = user_skills + [s for s in skills_to_add if s not in user_skills]

    prompt = rf"""Based on this job description and the user's profile, generate professional CV content tailored to the job. Select and adapt the user's experiences and projects to best match the job requirements.

    User Profile:
    - Skills: {', '.join(modified_skills)}
    - Experience Summary: {user.get('experience_summary', '')}
    - Experiences:
    {experiences_text}
    - Projects:
    {projects_text}
    - Education: {user.get('education', '')}

    Job Description:
    {job_text}

    Reply with a valid JSON object containing the following keys:
    - "education": Plain text for the education section (e.g., "Bachelor of Science in Computer Science\nUniversity of Technology\n2015\nComputer Science")
    - "experience": Plain text for the experience section (e.g., "Senior Python Developer\nTech Innovations Inc., Jan 2020 – Present\nLed the development...")
    - "projects": Plain text for the projects section (e.g., "E-commerce Platform\n2023\nDeveloped a full-featured e-commerce platform...")
    - "skills": Plain text for the skills section (e.g., "Programming Languages: Python, JavaScript, PHP\nWeb Frameworks: Django, Flask\n...")

    Do not wrap the JSON in markdown code blocks. Output only the JSON object.

    Focus on tailoring content to match the job requirements. Use professional language and quantify achievements where possible."""
    
    logging.debug(f"CV prompt: {prompt[:1000]}...")  # Log first 1000 chars of prompt
    response = None
    try:
        response = llama_chat(prompt, config)
        logging.debug(f"AI response: {response}")
        response_text = response.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        # Remove control characters except newline and tab
        response_text = ''.join(c for c in response_text if ord(c) >= 32 or c in '\n\t')

        # Try to extract JSON if it's embedded in text
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            response_text = response_text[start:end]

        data = json.loads(response_text)
        logging.info("CV JSON parsed successfully")
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
        
        logging.info("CV content generated")
        return Markup(cv_content)  # Return as Markup
    except Exception as e:
        logging.error(f"Error generating CV: {e}")
        if response:
            logging.error(f"Response: {response}")
        click.echo(f"Error generating CV: {e}")
        return None

def generate_cover_letter(job_text, config, profile, skill_modification_level):
    """Generate cover letter using llama.cpp"""
    logging.info("Starting cover letter generation")
    if not check_llama():
        logging.error("llama.cpp server not available")
        return None

    # Parse job data for better personalization
    job_data = parse_job_description(job_text)
    user = profile

    experiences_text = '\n'.join([f"- {exp['title']} at {exp['company']} ({exp['dates']}): {exp['description']}" for exp in user.get('experiences', [])])

    # Modify skills
    job_skills = job_data['technologies']
    user_skills = user.get('skills', [])
    num_to_add = int(len(job_skills) * skill_modification_level)
    skills_to_add = job_skills[:num_to_add]
    modified_skills = user_skills + [s for s in skills_to_add if s not in user_skills]

    prompt = f"""Write a compelling, personalized cover letter for the {job_data['title']} position at {job_data['company']}.

    User Profile:
    - Name: {user.get('name', '')}
    - Skills: {', '.join(modified_skills)}
    - Experience Summary: {user.get('experience_summary', '')}
    - Experiences:
    {experiences_text}
    - Education: {user.get('education', '')}

    Job Details:
    - Position: {job_data['title']}
    - Company: {job_data['company']}
    - Location: {job_data['location']}
    - Key Requirements: {', '.join(job_data['requirements'][:3]) if job_data['requirements'] else 'Python development experience'}
    - Key Responsibilities: {', '.join(job_data['responsibilities'][:2]) if job_data['responsibilities'] else 'Web application development'}

    Reply with a valid JSON object containing the key "body" with the cover letter body text (2-3 paragraphs). Do not include salutation or closing. Do not wrap the JSON in markdown code blocks. Output only the JSON object. Make it highly personalized by:

    1. First paragraph: Formally express enthusiasm for the specific role and company.
    2. Second paragraph: Connect your specific experience and skills to the job requirements and responsibilities
    3. Third paragraph: Explain why you're interested in this company specifically and what you can contribute

    Use professional, conversational language that sounds natural, not like a template. Reference specific technologies, requirements, and company details from the job description. Show genuine interest and specific knowledge about the role."""
    
    logging.debug(f"Cover letter prompt: {prompt[:1000]}...")  # Log first 1000 chars of prompt
    response = None
    try:
        response = llama_chat(prompt, config)
        logging.debug(f"AI response: {response}")
        response_text = response.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        # Remove control characters except newline and tab
        response_text = ''.join(c for c in response_text if ord(c) >= 32 or c in '\n\t')

        # Try to extract JSON if it's embedded in text
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            response_text = response_text[start:end]

        data = json.loads(response_text)
        logging.info("Cover letter JSON parsed successfully")
        return data['body']
    except Exception as e:
        logging.error(f"Error generating cover letter: {e}")
        if response:
            logging.error(f"Response: {response}")
        click.echo(f"Error generating cover letter: {e}")
        return None



def extract_skills_from_text(text):
    """Extract potential skills from text using common tech keywords"""
    common_skills = [
        'Python', 'Java', 'JavaScript', 'C++', 'C#', 'Ruby', 'PHP', 'Go', 'Rust', 'Swift', 'Kotlin',
        'Django', 'Flask', 'React', 'Angular', 'Vue', 'Node.js', 'Express', 'Spring', 'Laravel',
        'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'SQLite', 'Oracle', 'SQL Server',
        'AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes', 'Terraform', 'Ansible',
        'Git', 'GitHub', 'GitLab', 'Jenkins', 'Travis CI', 'CircleCI',
        'Linux', 'Ubuntu', 'CentOS', 'Windows', 'macOS',
        'HTML', 'CSS', 'SASS', 'SCSS', 'Bootstrap', 'Tailwind',
        'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy', 'Matplotlib',
        'REST', 'GraphQL', 'API', 'Microservices', 'SOA',
        'Agile', 'Scrum', 'Kanban', 'TDD', 'BDD'
    ]
    found_skills = set()
    text_lower = text.lower()
    for skill in common_skills:
        if skill.lower() in text_lower:
            found_skills.add(skill)
    return list(found_skills)

def parse_job_description(job_text):
    """Parse job description to extract key information"""
    job_data = {
        'title': 'Software Developer',
        'company': 'Company',
        'location': 'Remote',
        'requirements': [],
        'responsibilities': [],
        'benefits': [],
        'technologies': []
    }

    lines = job_text.split('\n')
    current_section = None

    # Try to extract company from the first meaningful line
    for line in lines[:5]:  # Check first 5 lines
        line = line.strip()
        if line and not line.lower().startswith('about') and len(line) > 10:
            # Look for company name patterns
            words = line.split()
            if len(words) > 0 and words[0].isupper() and len(words[0]) > 3:
                job_data['company'] = words[0]
                break

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Extract job title
        if line.startswith('Job Title:'):
            job_data['title'] = line.replace('Job Title:', '').strip()
        # Extract company
        elif line.startswith('Company:'):
            job_data['company'] = line.replace('Company:', '').strip()
        # Extract location
        elif line.startswith('Location:'):
            job_data['location'] = line.replace('Location:', '').strip()
        # Section headers
        elif 'responsibilities' in line.lower():
            current_section = 'responsibilities'
        elif 'requirements' in line.lower():
            current_section = 'requirements'
        elif 'nice to have' in line.lower():
            current_section = 'requirements'  # Add nice-to-have to requirements
        elif 'benefits' in line.lower():
            current_section = 'benefits'
        elif 'technologies' in line.lower() or 'skills' in line.lower():
            current_section = 'technologies'
        # Content lines
        elif current_section and line.startswith('-'):
            content = line[1:].strip()
            if current_section in job_data:
                job_data[current_section].append(content)

    # Extract skills from the entire job text
    job_data['technologies'] = extract_skills_from_text(job_text)

    return job_data

def render_html(cv_content, cover_content, job_data, output_prefix, config, profile):
    """Render HTML templates and generate PDFs using WeasyPrint"""
    logging.debug("Rendering CV and cover letter templates")
    try:
        from weasyprint import HTML

        templates_dir = Path(config['templates_dir'])
        env = Environment(loader=FileSystemLoader(templates_dir))

        cv_template = env.get_template('cv/cv.html')
        cover_template = env.get_template('cover_letter/cover_letter.html')

        output_dir = Path(config['output_dir'])
        cv_output_dir = output_dir / 'cv'
        cover_output_dir = output_dir / 'cover_letter'
        cv_output_dir.mkdir(parents=True, exist_ok=True)
        cover_output_dir.mkdir(parents=True, exist_ok=True)

        # Render CV
        cv_html = cv_template.render(content=cv_content, user=profile, job=job_data)
        cv_html_file = cv_output_dir / f"{output_prefix}.html"
        with open(cv_html_file, 'w') as f:
            f.write(cv_html)
        logging.info(f"CV HTML written to {cv_html_file}")

        # Generate CV PDF
        cv_pdf_file = cv_output_dir / f"{output_prefix}.pdf"
        HTML(string=cv_html).write_pdf(cv_pdf_file)
        logging.info(f"CV PDF generated: {cv_pdf_file}")

        # Add current date to job_data for cover letter
        import datetime
        job_data_with_date = job_data.copy()
        job_data_with_date['date'] = datetime.datetime.now().strftime('%B %d, %Y')

        # Render cover letter
        cover_html = cover_template.render(content=cover_content, user=profile, job=job_data_with_date)
        cover_html_file = cover_output_dir / f"{output_prefix}.html"
        with open(cover_html_file, 'w') as f:
            f.write(cover_html)
        logging.info(f"Cover letter HTML written to {cover_html_file}")

        # Generate cover letter PDF
        cover_pdf_file = cover_output_dir / f"{output_prefix}.pdf"
        HTML(string=cover_html).write_pdf(cover_pdf_file)
        logging.info(f"Cover letter PDF generated: {cover_pdf_file}")

    except Exception as e:
        print("Error in render_html:", e)
        raise

if __name__ == '__main__':
    cli()