from __future__ import annotations

import re
from typing import Iterable

from app.services.skills.taxonomy import extract_skills, normalize_skill

# Section headers → required vs preferred (case-insensitive)
_REQUIRED_HEADERS = (
    r"required\s+qualifications",
    r"minimum\s+qualifications",
    r"basic\s+qualifications",
    r"\brequirements\b",
    r"what\s+you'?ll\s+need",
    r"must\s+have",
    r"you\s+have",
    r"qualifications",
)

_PREFERRED_HEADERS = (
    r"preferred\s+qualifications",
    r"nice\s+to\s+have",
    r"bonus\s+points",
    r"preferred\s+skills",
    r"preferred\s+experience",
    r"plus\s+if\s+you",
    r"good\s+to\s+have",
)


def _compile_any(patterns: Iterable[str]) -> re.Pattern[str]:
    return re.compile("(?:" + ")|(?:".join(patterns) + ")", re.IGNORECASE)


_REQ_RE = _compile_any(_REQUIRED_HEADERS)
_PREF_RE = _compile_any(_PREFERRED_HEADERS)


def _split_sections(text: str) -> tuple[str | None, str | None, str]:
    if not text or not text.strip():
        return None, None, ""
    lines = text.splitlines()
    req_parts: list[str] = []
    pref_parts: list[str] = []
    neutral: list[str] = []
    bucket: str | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        low = stripped.lstrip("#").strip()
        if _REQ_RE.search(low) and len(low) < 120:
            bucket = "req"
            continue
        if _PREF_RE.search(low) and len(low) < 120:
            bucket = "pref"
            continue
        if bucket == "req":
            req_parts.append(line)
        elif bucket == "pref":
            pref_parts.append(line)
        else:
            neutral.append(line)

    req_blob = "\n".join(req_parts).strip() or None
    pref_blob = "\n".join(pref_parts).strip() or None
    remainder = "\n".join(neutral).strip()
    return req_blob, pref_blob, remainder


def _dedupe_preserve(xs: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in xs:
        k = normalize_skill(x).lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(normalize_skill(x))
    return out


def extract_skills_sectioned(description: str) -> tuple[list[str] | None, list[str] | None]:
    req_blob, pref_blob, remainder = _split_sections(description)
    req_skills: list[str] = []
    pref_skills: list[str] = []

    if req_blob:
        req_skills.extend(extract_skills(req_blob))
    if pref_blob:
        pref_skills.extend(extract_skills(pref_blob))

    if not req_blob and not pref_blob:
        all_s = extract_skills(description)
        return (_dedupe_preserve(all_s) if all_s else None, None)

    if remainder and (not req_blob or not req_skills):
        req_skills.extend(extract_skills(remainder))
    if remainder and pref_blob and not pref_skills:
        pref_skills.extend(extract_skills(remainder))

    req_out = _dedupe_preserve(req_skills) if req_skills else None
    pref_out = _dedupe_preserve(pref_skills) if pref_skills else None
    if req_out and pref_out:
        rs = {x.lower() for x in req_out}
        pref_out = [p for p in pref_out if p.lower() not in rs]
        pref_out = pref_out or None
    return req_out, pref_out
