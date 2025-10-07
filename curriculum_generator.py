#!/usr/bin/env python3
"""
Curriculum AI Generator using Ollama
"""

import click
import yaml
import os
from pathlib import Path
import ollama
from jinja2 import Environment, FileSystemLoader

# Load configuration
CONFIG_FILE = Path.home() / '.curriculum_generator.yaml'
DEFAULT_CONFIG = {
    'model': 'qwen2.5:32b',
    'templates_dir': 'templates',
    'output_dir': 'output',
    'user': {
        'name': 'Your Name',
        'email': 'your.email@example.com',
        'phone': '+123456789',
        'address': 'Your Address, City, Country',
        'skills': ['Python', 'JavaScript', 'SQL'],
        'experience': '5+ years in software development',
        'education': 'Bachelor in Computer Science'
    }
}

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f)

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
@click.option('--experience', help='Your experience summary')
@click.option('--education', help='Your education')
def configure(model, templates_dir, output_dir, name, email, phone, address, skills, experience, education):
    """Configure the curriculum generator"""
    config = load_config()
    if 'user' not in config:
        config['user'] = DEFAULT_CONFIG['user'].copy()
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
    if experience:
        config['user']['experience'] = experience
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

    # Render LaTeX
    click.echo("Rendering LaTeX...")
    render_latex(cv_content, cover_content, job_data, output or 'generated', config)

    click.echo(f"Generated CV and cover letter in {config['output_dir']}/cv and {config['output_dir']}/cover_letter")

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

def generate_cv(job_text, config):
    """Generate CV content using Ollama"""
    if not check_ollama():
        return None
    user = config['user']
    prompt = f"""Based on this job description and the user's profile, generate professional CV sections that highlight relevant skills and experience.

User Profile:
- Skills: {', '.join(user['skills'])}
- Experience: {user['experience']}
- Education: {user['education']}

Job Description:
{job_text}

Generate CV content using specific LaTeX resume commands. Structure your response with these exact commands:

\\section{{EDUCATION}}
\\resumeSubHeadingListStart
    \\resumeSubheading
        {{Institution Name}}{{City, Country}}
        {{Degree Name}}{{Start Year - End Year}}
        {{Relevant details like GPA, coursework, or achievements}}
\\resumeSubHeadingListEnd

\\section{{EXPERIENCE}}
\\resumeSubHeadingListStart
    \\resumeSubheading
        {{Company Name}}{{City, Country}}
        {{Job Title}}{{Start Date - End Date}}
        {{Key responsibilities and achievements}}
    \\resumeSubheading
        {{Another Company}}{{Location}}
        {{Another Job Title}}{{Dates}}
        {{More achievements}}
\\resumeSubHeadingListEnd

\\section{{PROJECTS}}
\\resumeSubHeadingListStart
    \\resumeProjectHeading
        {{Project Name}}{{Year}}
        \\resumeSubHeadingListStart
            \\resumeItem{{Project description and technologies}}
            \\resumeItem{{Key achievements}}
        \\resumeSubHeadingListEnd
\\resumeSubHeadingListEnd

\\section{{SKILLS}}
\\begin{{minipage}}[ht]{{0.48\\textwidth}}
\\textbf{{Programming languages:}} \\\\
{', '.join(user['skills'])}
\\vspace{{1em}}

\\textbf{{Frameworks:}} \\\\
Frameworks and libraries relevant to the job
\\end{{minipage}}
\\begin{{minipage}}[ht]{{0.48\\textwidth}}
\\textbf{{Deployments:}} \\\\
AWS, Kubernetes, Docker, etc.

\\vspace{{1em}}
\\textbf{{Languages:}} \\\\
English proficiency, other languages
\\end{{minipage}}

Focus on tailoring content to match the job requirements. Use professional language and quantify achievements where possible."""
    try:
        response = ollama.generate(model=config['model'], prompt=prompt)
        return response['response']
    except Exception as e:
        click.echo(f"Error generating CV: {e}")
        return None

def generate_cover_letter(job_text, config):
    """Generate cover letter using Ollama"""
    if not check_ollama():
        return None

    # Parse job data for better personalization
    job_data = parse_job_description(job_text)
    user = config['user']

    prompt = f"""Write a compelling, personalized cover letter for the {job_data['title']} position at {job_data['company']}.

User Profile:
- Name: {user['name']}
- Skills: {', '.join(user['skills'])}
- Experience: {user['experience']}
- Education: {user['education']}

Job Details:
- Position: {job_data['title']}
- Company: {job_data['company']}
- Location: {job_data['location']}
- Key Requirements: {', '.join(job_data['requirements'][:3]) if job_data['requirements'] else 'Python development experience'}
- Key Responsibilities: {', '.join(job_data['responsibilities'][:2]) if job_data['responsibilities'] else 'Web application development'}

Write only the body text of the cover letter (2-3 paragraphs). Do not include salutation or closing. Make it highly personalized by:

1. First paragraph: Express enthusiasm for the specific role and company, mention how you found the position
2. Second paragraph: Connect your specific experience and skills to the job requirements and responsibilities
3. Third paragraph: Explain why you're interested in this company specifically and what you can contribute

Use professional, conversational language that sounds natural, not like a template. Reference specific technologies, requirements, and company details from the job description. Show genuine interest and specific knowledge about the role."""
    try:
        response = ollama.generate(model=config['model'], prompt=prompt)
        return response['response']
    except Exception as e:
        click.echo(f"Error generating cover letter: {e}")
        return None

def compile_pdf(tex_file):
    """Compile LaTeX file to PDF"""
    import subprocess
    try:
        # Try LuaTeX first (for templates that require it), fall back to PDFLaTeX
        compilers = ['lualatex', 'pdflatex']
        success = False

        for compiler in compilers:
            try:
                click.echo(f"Trying {compiler}...")
                result = subprocess.run([compiler, '-output-directory', str(tex_file.parent), str(tex_file)],
                                      check=True, capture_output=False, timeout=60)
                click.echo(f"Compiled PDF with {compiler}: {tex_file.with_suffix('.pdf')}")
                success = True
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        if not success:
            click.echo(f"Failed to compile PDF for {tex_file}. No suitable LaTeX compiler found.")

    except subprocess.TimeoutExpired:
        click.echo(f"PDF compilation timed out for {tex_file}. LaTeX may have errors.")
    except Exception as e:
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

    # Render cover letter
    cover_tex = cover_template.render(content=cover_content, user=config['user'], job=job_data)
    cover_file = cover_output_dir / f"{output_prefix}.tex"
    with open(cover_file, 'w') as f:
        f.write(cover_tex)

    # Compile PDFs
    compile_pdf(cv_file)
    compile_pdf(cover_file)

if __name__ == '__main__':
    cli()