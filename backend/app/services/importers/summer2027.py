from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import httpx
from sqlalchemy.orm import Session

from app.db.models import JobPosting
from app.services.embeddings.pipeline import embed_job_by_id
from app.services.jobs.normalize import normalize_url


RAW_README_URL = "https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/refs/heads/dev/README.md"
REPO_URL = "https://github.com/vanshb03/Summer2027-Internships"


@dataclass(frozen=True)
class Summer2027Row:
    company: str
    role: str
    location: str | None
    application_url: str | None
    date_posted_raw: str | None


def _clean_md_text(s: str) -> str:
    s = s.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]+)\*", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _extract_markdown_link(cell: str) -> str | None:
    """
    Handles:
    - [Apply](https://...)
    - [![Apply](img)](https://...)
    - plain https://...
    """
    cell = cell.strip()
    if not cell:
        return None

    m = re.search(r"\[!\[[^\]]*]\([^)]*\)\]\(([^)]+)\)", cell)
    if m:
        return m.group(1).strip()

    m = re.search(r"\[[^\]]*]\(([^)]+)\)", cell)
    if m:
        return m.group(1).strip()

    m = re.search(r"(https?://\S+)", cell)
    if m:
        return m.group(1).rstrip(").,")

    return None


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    raw = _clean_md_text(s)
    raw = raw.replace("—", "-").replace("–", "-").strip()
    if not raw:
        return None

    # ISO-ish
    m = re.match(r"^(\d{4}-\d{2}-\d{2})$", raw)
    if m:
        try:
            return datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    # mm/dd/yyyy or mm/dd/yy
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    return None


def _split_md_row(line: str) -> list[str]:
    # Basic pipe split; resilient to leading/trailing pipes.
    parts = [p.strip() for p in line.strip().strip("|").split("|")]
    return parts


def _find_table_block(md: str) -> tuple[list[str], int] | None:
    """
    Returns (table_lines, start_line_index) for the internship table.
    We find a header containing the expected columns and then capture until
    the table ends (non-pipe line).
    """
    lines = md.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "|" not in line:
            continue
        cols = [c.lower() for c in _split_md_row(line)]
        if {"company", "role", "location"}.issubset(set(cols)) and any(
            "application" in c or "link" in c for c in cols
        ):
            # Next line should be the markdown separator like |---|---|
            if i + 1 < len(lines) and re.search(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
                header_idx = i
                break

    if header_idx is None:
        return None

    table_lines: list[str] = []
    for j in range(header_idx, len(lines)):
        l = lines[j]
        if "|" not in l and table_lines:
            break
        if "|" in l:
            table_lines.append(l)
        elif table_lines:
            break

    return table_lines, header_idx


def parse_summer2027_readme(md: str) -> list[Summer2027Row]:
    found = _find_table_block(md)
    if not found:
        return []
    table_lines, _ = found
    if len(table_lines) < 3:
        return []

    header = _split_md_row(table_lines[0])
    header_l = [h.lower() for h in header]

    def idx_of(name: str) -> int | None:
        for i, h in enumerate(header_l):
            if h == name:
                return i
        return None

    company_i = idx_of("company")
    role_i = idx_of("role")
    location_i = idx_of("location")
    date_i = None
    app_i = None

    for i, h in enumerate(header_l):
        if "date" in h:
            date_i = i
        if "application" in h or h == "link":
            app_i = i

    if company_i is None or role_i is None:
        return []

    rows: list[Summer2027Row] = []
    last_company: str | None = None

    for line in table_lines[2:]:
        parts = _split_md_row(line)
        if len(parts) < max(company_i, role_i, location_i or 0, app_i or 0, date_i or 0) + 1:
            continue

        company_raw = parts[company_i]
        company_clean = _clean_md_text(company_raw)
        if "↳" in company_clean or company_clean.strip() == "↳":
            company = last_company or company_clean.replace("↳", "").strip() or "Unknown"
        else:
            company = company_clean or "Unknown"
            last_company = company

        role = _clean_md_text(parts[role_i]) or "Internship"
        location = _clean_md_text(parts[location_i]) if location_i is not None else ""
        location = location or None

        application_url = _extract_markdown_link(parts[app_i]) if app_i is not None else None
        date_raw = _clean_md_text(parts[date_i]) if date_i is not None else None
        date_raw = date_raw or None

        rows.append(
            Summer2027Row(
                company=company[:400],
                role=role[:400],
                location=location[:400] if location else None,
                application_url=application_url,
                date_posted_raw=date_raw,
            )
        )

    return rows


def fetch_summer2027_readme(raw_url: str = RAW_README_URL) -> str:
    with httpx.Client(timeout=20.0, follow_redirects=True, headers={"User-Agent": "jobpulse/1.0"}) as c:
        r = c.get(raw_url)
        r.raise_for_status()
        return r.text


def import_summer2027_internships(
    db: Session,
    *,
    raw_url: str = RAW_README_URL,
    embed: bool = True,
    source_name: str = "summer2027_internships",
) -> dict:
    md = fetch_summer2027_readme(raw_url=raw_url)
    rows = parse_summer2027_readme(md)

    created = 0
    duplicates = 0
    embedded = 0

    now = datetime.now(timezone.utc)

    for r in rows:
        source_url = r.application_url or REPO_URL
        if not r.application_url:
            # Make synthetic URL stable-ish across reruns for dedupe.
            h = hashlib.sha256(f"{r.company}|{r.role}|{r.location}|{r.date_posted_raw}".encode("utf-8")).hexdigest()[:16]
            source_url = f"{REPO_URL}#row-{h}"

        normalized = normalize_url(source_url)
        description = (
            f"Imported from {REPO_URL}.\n\n"
            f"Company: {r.company}\n"
            f"Role: {r.role}\n"
            f"Location: {r.location or ''}\n"
            f"Date posted: {r.date_posted_raw or ''}\n"
            f"Application: {r.application_url or ''}\n"
        ).strip()

        job_hash = JobPosting.compute_job_hash(r.company, r.role, r.location, description)
        existing = (
            db.query(JobPosting)
            .filter((JobPosting.normalized_url == normalized) | (JobPosting.job_hash == job_hash))
            .one_or_none()
        )
        if existing:
            duplicates += 1
            continue

        jp = JobPosting(
            source=source_name,
            source_url=source_url,
            normalized_url=normalized,
            title=r.role,
            company=r.company,
            location=r.location,
            description=description,
            required_skills_raw=None,
            preferred_skills_raw=None,
            employment_type="internship",
            experience_level=None,
            salary=None,
            date_posted=_parse_date(r.date_posted_raw),
            crawled_at=now,
            job_hash=job_hash,
            raw_html=None,
        )
        db.add(jp)
        db.flush()
        created += 1

        if embed:
            embed_job_by_id(db=db, job_id=jp.id)
            embedded += 1

    return {
        "source": source_name,
        "raw_url": raw_url,
        "rows_parsed": len(rows),
        "created": created,
        "duplicates_skipped": duplicates,
        "embedded": embedded,
    }

