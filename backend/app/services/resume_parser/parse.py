from __future__ import annotations

import re

from app.services.skills.taxonomy import extract_skills


def estimate_experience_years(text: str) -> int | None:
    # Heuristic: look for patterns like "3+ years" or "5 years".
    m = re.search(r"(\d{1,2})\s*\+?\s*years", text, flags=re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


def extract_education(text: str) -> list[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    edu: list[str] = []
    for l in lines:
        if re.search(r"\b(BS|B\.S\.|BA|B\.A\.|MS|M\.S\.|MA|M\.A\.|PhD|MEng|MBA)\b", l):
            edu.append(l)
    return edu[:5]


def parse_resume_text(text: str) -> dict:
    skills = extract_skills(text)
    experience_years = estimate_experience_years(text)
    education = extract_education(text)

    # Minimal structured output; expand with section parsing over time.
    return {
        "skills": skills,
        "experience_years": experience_years,
        "education": education,
        "projects": [],
        "experience": [],
        "certifications": [],
        "technologies": skills,
    }

