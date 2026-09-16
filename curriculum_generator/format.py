"""Turn plain-text CV sections (produced by the LLM) into HTML fragments.

Each formatter takes the raw text for one section and returns a
:class:`markupsafe.Markup` fragment that the Jinja2 CV template interpolates.
The text is inserted without HTML escaping to match the original behavior;
escaping untrusted LLM output is a hardening item for the API layer.
"""

from markupsafe import Markup


def format_education(text: str) -> Markup:
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
    return Markup(text)


def format_experience(text: str) -> Markup:
    jobs = text.split('\n\n')
    result = ""
    for job in jobs:
        lines = [line.strip() for line in job.split('\n') if line.strip()]
        if len(lines) >= 2:
            title = lines[0]
            company_dates = lines[1]
            parts = company_dates.split(', ')
            if len(parts) >= 2:
                company = parts[0]
                dates = ', '.join(parts[1:])
            else:
                company = company_dates
                dates = ''
            location = 'Remote'
            description = ' '.join(lines[2:])
            items = [item.strip() for item in description.split('. ') if item.strip()]
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


def format_projects(text: str) -> Markup:
    projects = text.split('\n\n')
    result = ""
    for proj in projects:
        lines = [line.strip() for line in proj.split('\n') if line.strip()]
        if len(lines) >= 2:
            name = lines[0]
            year = lines[1]
            description = ' '.join(lines[2:])
            items = [item.strip() for item in description.split('. ') if item.strip()]
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


def format_skills(text: str) -> Markup:
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
