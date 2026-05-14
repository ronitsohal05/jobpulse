from __future__ import annotations

import re


# Small, editable baseline skill taxonomy. Expand over time.
CANONICAL_SKILLS: set[str] = {
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "C",
    "C++",
    "Swift",
    "Kotlin",
    "Go",
    "Rust",
    "SQL",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "Docker",
    "Kubernetes",
    "AWS",
    "GCP",
    "Azure",
    "React",
    "GraphQL",
    "REST APIs",
    "Next.js",
    "Node.js",
    "FastAPI",
    "Flask",
    "Django",
    "Spring",
    "Terraform",
    "Linux",
    "Git",
    "CI/CD",
    "Pandas",
    "NumPy",
    "scikit-learn",
    "PyTorch",
    "TensorFlow",
    "LangChain",
    "OpenAI API",
    "LLM",
    "RAG",
    "FAISS",
    "Spark",
    "Kafka",
}

SYNONYMS: dict[str, str] = {
    "JS": "JavaScript",
    "TS": "TypeScript",
    "Postgres": "PostgreSQL",
    "K8s": "Kubernetes",
    "NextJS": "Next.js",
    "Node": "Node.js",
    "CI CD": "CI/CD",
    "CICD": "CI/CD",
}


def normalize_skill(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    if s in SYNONYMS:
        return SYNONYMS[s]
    # Case-normalize common tokens
    for k, v in SYNONYMS.items():
        if s.lower() == k.lower():
            return v
    # Match canonical by case-insensitive equality
    for c in CANONICAL_SKILLS:
        if s.lower() == c.lower():
            return c
    return s


def extract_skills(text: str) -> list[str]:
    if not text:
        return []
    found: set[str] = set()
    hay = text

    # "C" as a language token (avoid C++ false positives handled by C++ match order below).
    if re.search(r"(?<![A-Za-z0-9+])C(?![+A-Za-z0-9])", hay):
        found.add("C")

    # Synonym-first so e.g. "JS" becomes JavaScript even if "JS" isn't canonical.
    for syn, canonical in SYNONYMS.items():
        pat = r"(?<![A-Za-z0-9])" + re.escape(syn) + r"(?![A-Za-z0-9])"
        if re.search(pat, hay, flags=re.IGNORECASE):
            found.add(canonical)

    for skill in CANONICAL_SKILLS:
        if skill == "C":
            continue
        pat = r"(?<![A-Za-z0-9])" + re.escape(skill) + r"(?![A-Za-z0-9])"
        if re.search(pat, hay, flags=re.IGNORECASE):
            found.add(skill)

    return sorted(found)

