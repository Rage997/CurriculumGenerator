#!/usr/bin/env python3
"""
Curriculum AI Generator using Ollama
"""

import click
import yaml
import os
import json
import logging
from pathlib import Path
import ollama
from jinja2 import Environment, FileSystemLoader

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

# Load configuration
CONFIG_FILE = Path(__file__).parent / 'candidate_config.yaml'


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
        logging.info(f"Loaded config from {CONFIG_FILE}")
        return config
    logging.info("Config file not found")
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f)
    logging.info(f"Saved config to {CONFIG_FILE}")

@click.group()
def cli():
    pass

@cli.command()
@click.option('--model', help='Ollama model to use')
@click.option('--templates-dir', help='Directory for LaTeX templates')
@click.option('--output-dir', help='Directory for generated files')
@click.option('--name', help='Your full name')
@click.option('--email', help='Your email address')
@click.option('--phone', help='Your phone number')
@click.option('--address', help='Your address')
@click.option('--skills', help='Your skills (comma-separated)')
@click.option('--experience-summary', help='Your experience summary')
@click.option('--education', help='Your education')
def configure(model, templates_dir, output_dir, name, email, phone, address, skills, experience_summary, education):
    """Configure the curriculum generator"""
    config = load_config()
    if 'user' not in config:
        config['user'] = {}
    if model:
        config['model'] = model
    if templates_dir:
        config['templates_dir'] = templates_dir
    if output_dir:
        config['output_dir'] = output_dir
    if name:
        config['user']['name'] = name
    if email:
        config['user']['email'] = email
    if phone:
        config['user']['phone'] = phone
    if address:
        config['user']['address'] = address
    if skills:
        config['user']['skills'] = [s.strip() for s in skills.split(',')]
    if experience_summary:
        config['user']['experience_summary'] = experience_summary
    if education:
        config['user']['education'] = education
    save_config(config)
    click.echo("Configuration saved.")

@cli.command()
def models():
    """List available Ollama models"""
    if not check_ollama():
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
def generate(job_description, output, dry_run):
    """Generate CV and cover letter from job description"""
    config = load_config()
    job_text = job_description.read()
    logging.info(f"Generating documents for job: {job_description.name}")
    logging.debug(f"Job text: {job_text[:500]}...")  # Log first 500 chars

    if dry_run:
        cv_content = "Education:\nSample education\n\nExperience:\nSample experience\n\nSkills:\nSample skills"
        cover_content = "Sample cover letter content."
    else:
        # Generate CV
        click.echo("Generating CV...")
        cv_content = generate_cv(job_text, config)
        if cv_content is None:
            return
        click.echo("CV generated.")

        # Generate cover letter
        click.echo("Generating cover letter...")
        cover_content = generate_cover_letter(job_text, config)
        if cover_content is None:
            return
        click.echo("Cover letter generated.")

    # Parse job description for personalization
    job_data = parse_job_description(job_text)
    logging.debug(f"Parsed job data: {job_data}")

    # Render LaTeX
    click.echo("Rendering LaTeX...")
    logging.info("Rendering LaTeX templates")
    render_latex(cv_content, cover_content, job_data, output or 'generated', config)

    click.echo(f"Generated CV and cover letter in {config['output_dir']}/cv and {config['output_dir']}/cover_letter")
    logging.info(f"Generation completed. Output in {config['output_dir']}")

def check_ollama():
    """Check if Ollama is running and accessible"""
    try:
        ollama.list()
        return True
    except Exception as e:
        click.echo(f"Error connecting to Ollama: {e}")
        click.echo("Make sure Ollama is installed and running.")
        return False

def list_models():
    """List available Ollama models"""
    try:
        models = ollama.list()
        return [model.model for model in models['models']]
    except Exception as e:
        click.echo(f"Error listing models: {e}")
        return []

def format_education(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) >= 3:
        degree = escape_latex(lines[0])
        university = escape_latex(lines[1])
        year = escape_latex(lines[2])
        return rf"\resumeSubHeadingListStart\resumeSubheading{{{degree}}}\resumeSubpoint{{{university}}}{{{year}}}\resumeSubHeadingListEnd"
    return escape_latex(text)

def format_experience(text):
    jobs = text.split('\n\n')
    result = ""
    for job in jobs:
        lines = [line.strip() for line in job.split('\n') if line.strip()]
        if len(lines) >= 2:
            title = escape_latex(lines[0])
            company_dates = escape_latex(lines[1])
            description = ' '.join(lines[2:])
            items = [item.strip() for item in description.split('. ') if item.strip()]
            item_str = ''.join(rf"\resumeItem{{{escape_latex(item)}}}" for item in items)
            result += rf"\resumeSubheading{{{title}}}\resumeSubheading{{{company_dates}}}{item_str}"
    return rf"\resumeSubHeadingListStart{result}\resumeSubHeadingListEnd"

def format_projects(text):
    projects = text.split('\n\n')
    result = ""
    for proj in projects:
        lines = [line.strip() for line in proj.split('\n') if line.strip()]
        if len(lines) >= 2:
            name = escape_latex(lines[0])
            year = escape_latex(lines[1])
            description = ' '.join(lines[2:])
            items = [item.strip() for item in description.split('. ') if item.strip()]
            item_str = ''.join(rf"\resumeSubbullet{{{escape_latex(item)}}}" for item in items)
            result += rf"\resumeSubheading{{{name} ({year})}}{item_str}"
    return rf"\resumeSubHeadingListStart{result}\resumeSubHeadingListEnd"

def format_skills(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    skills = []
    for line in lines:
        if ':' in line:
            _, s = line.split(':', 1)
            skills.extend([sk.strip() for sk in s.split(',') if sk.strip()])
    item_str = ''.join(rf"\item {escape_latex(skill)}" for skill in skills)
    return rf"\begin{{multicols}}{{2}}\begin{{itemize}}[leftmargin=0em]{item_str}\end{{itemize}}\end{{multicols}}"

def generate_cv(job_text, config):
    """Generate CV content using Ollama"""
    logging.info("Starting CV generation")
    if not check_ollama():
        logging.error("Ollama not available")
        return None
    user = config['user']
    experiences_text = '\n'.join([f"- {exp['title']} at {exp['company']} ({exp['dates']}): {exp['description']}" for exp in user.get('experiences', [])])
    projects_text = '\n'.join([f"- {proj['name']} ({proj['year']}): {proj['description']}" for proj in user.get('projects', [])])

    prompt = rf"""Based on this job description and the user's profile, generate professional CV content tailored to the job. Select and adapt the user's experiences and projects to best match the job requirements.

User Profile:
- Skills: {', '.join(user.get('skills', []))}
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
        response = ollama.generate(model=config['model'], prompt=prompt, options={'timeout': 60})
        logging.debug(f"AI response: {response['response']}")
        response_text = response['response'].strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        # Remove control characters except newline and tab
        response_text = ''.join(c for c in response_text if ord(c) >= 32 or c in '\n\t')
        data = json.loads(response_text)
        logging.info("CV JSON parsed successfully")
        cv_content = rf"""\section{{EDUCATION}}
{format_education(data['education'])}

\section{{EXPERIENCE}}
{format_experience(data['experience'])}

\section{{PROJECTS}}
{format_projects(data['projects'])}

\section{{SKILLS}}
{format_skills(data['skills'])}
"""
        logging.info("CV content generated")
        return cv_content
    except Exception as e:
        logging.error(f"Error generating CV: {e}")
        if response:
            logging.error(f"Response: {response['response']}")
        click.echo(f"Error generating CV: {e}")
        return None

def generate_cover_letter(job_text, config):
    """Generate cover letter using Ollama"""
    logging.info("Starting cover letter generation")
    if not check_ollama():
        logging.error("Ollama not available")
        return None

    # Parse job data for better personalization
    job_data = parse_job_description(job_text)
    user = config['user']

    experiences_text = '\n'.join([f"- {exp['title']} at {exp['company']} ({exp['dates']}): {exp['description']}" for exp in user.get('experiences', [])])

    prompt = f"""Write a compelling, personalized cover letter for the {job_data['title']} position at {job_data['company']}.

User Profile:
- Name: {user.get('name', '')}
- Skills: {', '.join(user.get('skills', []))}
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

1. First paragraph: Express enthusiasm for the specific role and company, mention how you found the position
2. Second paragraph: Connect your specific experience and skills to the job requirements and responsibilities
3. Third paragraph: Explain why you're interested in this company specifically and what you can contribute

Use professional, conversational language that sounds natural, not like a template. Reference specific technologies, requirements, and company details from the job description. Show genuine interest and specific knowledge about the role."""
    logging.debug(f"Cover letter prompt: {prompt[:1000]}...")  # Log first 1000 chars of prompt
    response = None
    try:
        response = ollama.generate(model=config['model'], prompt=prompt, options={'timeout': 60})
        logging.debug(f"AI response: {response['response']}")
        response_text = response['response'].strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        # Remove control characters except newline and tab
        response_text = ''.join(c for c in response_text if ord(c) >= 32 or c in '\n\t')
        data = json.loads(response_text)
        logging.info("Cover letter JSON parsed successfully")
        return data['body']
    except Exception as e:
        logging.error(f"Error generating cover letter: {e}")
        if response:
            logging.error(f"Response: {response['response']}")
        click.echo(f"Error generating cover letter: {e}")
        return None

def compile_pdf(tex_file):
    """Compile LaTeX file to PDF"""
    import subprocess
    logging.info(f"Compiling PDF for {tex_file}")
    try:
        # Try LuaTeX first (for templates that require it), fall back to PDFLaTeX
        compilers = ['lualatex', 'pdflatex']
        success = False

        for compiler in compilers:
            try:
                click.echo(f"Trying {compiler}...")
                logging.debug(f"Running {compiler} on {tex_file}")
                result = subprocess.run([compiler, '-output-directory', str(tex_file.parent), str(tex_file)],
                                      check=True, capture_output=False, timeout=60)
                click.echo(f"Compiled PDF with {compiler}: {tex_file.with_suffix('.pdf')}")
                logging.info(f"PDF compiled successfully with {compiler}: {tex_file.with_suffix('.pdf')}")
                success = True
                break
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logging.warning(f"{compiler} failed: {e}")
                continue

        if not success:
            logging.error(f"Failed to compile PDF for {tex_file}. No suitable LaTeX compiler found.")
            click.echo(f"Failed to compile PDF for {tex_file}. No suitable LaTeX compiler found.")

    except subprocess.TimeoutExpired:
        logging.error(f"PDF compilation timed out for {tex_file}")
        click.echo(f"PDF compilation timed out for {tex_file}. LaTeX may have errors.")
    except Exception as e:
        logging.error(f"Error compiling PDF for {tex_file}: {e}")
        click.echo(f"Error compiling PDF for {tex_file}: {e}")

def parse_job_description(job_text):
    """Parse job description to extract key information"""
    job_data = {
        'title': 'Position',
        'company': 'Company',
        'location': 'Location',
        'requirements': [],
        'responsibilities': [],
        'benefits': [],
        'technologies': []
    }

    lines = job_text.split('\n')
    current_section = None

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

    return job_data

def render_latex(cv_content, cover_content, job_data, output_prefix, config):
    """Render LaTeX templates"""
    logging.debug("Rendering CV and cover letter templates")
    templates_dir = Path(config['templates_dir'])
    env = Environment(loader=FileSystemLoader(templates_dir))

    cv_template = env.get_template('cv/cv.tex')
    cover_template = env.get_template('cover_letter/cover_letter.tex')

    output_dir = Path(config['output_dir'])
    cv_output_dir = output_dir / 'cv'
    cover_output_dir = output_dir / 'cover_letter'
    cv_output_dir.mkdir(parents=True, exist_ok=True)
    cover_output_dir.mkdir(parents=True, exist_ok=True)

    # Render CV
    cv_tex = cv_template.render(content=cv_content, user=config['user'], job=job_data)
    cv_file = cv_output_dir / f"{output_prefix}.tex"
    with open(cv_file, 'w') as f:
        f.write(cv_tex)
    logging.info(f"CV LaTeX written to {cv_file}")

    # Render cover letter
    cover_tex = cover_template.render(content=cover_content, user=config['user'], job=job_data)
    cover_file = cover_output_dir / f"{output_prefix}.tex"
    with open(cover_file, 'w') as f:
        f.write(cover_tex)
    logging.info(f"Cover letter LaTeX written to {cover_file}")

    # Compile PDFs
    logging.info("Compiling PDFs")
    compile_pdf(cv_file)
    compile_pdf(cover_file)

if __name__ == '__main__':
    cli()