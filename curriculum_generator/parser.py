"""Heuristic parsing of raw job descriptions.

These are keyword/section heuristics, not a real NLP pipeline — they extract
enough structure (company, title, location, requirements, technologies) to
personalize the cover letter and to seed the skill-modification logic. They
are pure functions and trivially unit-testable.
"""

from .models import JobData

# Common tech keywords used to seed the "technologies" field. Deliberately a
# flat, dependency-free list so parsing works offline and stays fast.
_COMMON_SKILLS = [
    'Python', 'Java', 'JavaScript', 'C++', 'C#', 'Ruby', 'PHP', 'Go', 'Rust', 'Swift', 'Kotlin',
    'Django', 'Flask', 'React', 'Angular', 'Vue', 'Node.js', 'Express', 'Spring', 'Laravel',
    'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'SQLite', 'Oracle', 'SQL Server',
    'AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes', 'Terraform', 'Ansible',
    'Git', 'GitHub', 'GitLab', 'Jenkins', 'Travis CI', 'CircleCI',
    'Linux', 'Ubuntu', 'CentOS', 'Windows', 'macOS',
    'HTML', 'CSS', 'SASS', 'SCSS', 'Bootstrap', 'Tailwind',
    'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy', 'Matplotlib',
    'REST', 'GraphQL', 'API', 'Microservices', 'SOA',
    'Agile', 'Scrum', 'Kanban', 'TDD', 'BDD',
]

# Section names that map to list fields on JobData.
_LIST_SECTIONS = ('requirements', 'responsibilities', 'benefits', 'technologies')


def extract_skills_from_text(text: str) -> list[str]:
    """Return the known tech keywords present in ``text`` (order not guaranteed)."""
    text_lower = text.lower()
    found = {skill for skill in _COMMON_SKILLS if skill.lower() in text_lower}
    return list(found)


def parse_job_description(job_text: str) -> JobData:
    """Parse a job description into structured :class:`JobData`."""
    job_data = JobData()
    lines = job_text.split('\n')

    # Try to extract the company from the first meaningful line.
    for line in lines[:5]:
        line = line.strip()
        if line and not line.lower().startswith('about') and len(line) > 10:
            words = line.split()
            if words and words[0].isupper() and len(words[0]) > 3:
                job_data.company = words[0]
                break

    current_section = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('Job Title:'):
            job_data.title = line.replace('Job Title:', '').strip()
        elif line.startswith('Company:'):
            job_data.company = line.replace('Company:', '').strip()
        elif line.startswith('Location:'):
            job_data.location = line.replace('Location:', '').strip()
        elif 'responsibilities' in line.lower():
            current_section = 'responsibilities'
        elif 'requirements' in line.lower():
            current_section = 'requirements'
        elif 'nice to have' in line.lower():
            current_section = 'requirements'
        elif 'benefits' in line.lower():
            current_section = 'benefits'
        elif 'technologies' in line.lower() or 'skills' in line.lower():
            current_section = 'technologies'
        elif current_section in _LIST_SECTIONS and line.startswith('-'):
            getattr(job_data, current_section).append(line[1:].strip())

    # Skill extraction runs over the whole text and overrides any section hits.
    job_data.technologies = extract_skills_from_text(job_text)
    return job_data
