from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime

from app.schemas.jobs import JobIn
from app.services.jobs.normalize import normalize_url

from .skills import extract_skills_sectioned


def normalize_title(title: str) -> str:
    t = " ".join((title or "").split()).strip()
    return t[:400]


def normalize_company(company: str) -> str:
    c = " ".join((company or "").split()).strip()
    return c[:400] or "Unknown"


def normalize_location(loc: str | None) -> str | None:
    if not loc:
        return None
    s = " ".join(loc.split()).strip()
    return s[:400] if s else None


def normalize_source_url(url: str) -> str:
    return normalize_url(url)


def normalize_employment_type(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip().lower()
    mapping = {
        "full-time": "full-time",
        "fulltime": "full-time",
        "ft": "full-time",
        "part-time": "part-time",
        "parttime": "part-time",
        "pt": "part-time",
        "contract": "contract",
        "temporary": "temporary",
        "temp": "temporary",
        "internship": "internship",
        "intern": "internship",
    }
    return mapping.get(s, raw.strip()[:200] or None)


def normalize_experience_level(text: str | None) -> str | None:
    if not text:
        return None
    t = text.lower()
    order = [
        ("principal", "principal"),
        ("staff", "staff"),
        ("senior", "senior"),
        ("sr.", "senior"),
        ("junior", "junior"),
        ("jr.", "junior"),
        ("entry level", "entry level"),
        ("entry-level", "entry level"),
        ("new grad", "new grad"),
        ("graduate", "new grad"),
        ("intern", "intern"),
    ]
    for needle, label in order:
        if needle in t:
            return label
    return text.strip()[:200] or None


def normalize_salary(raw: str | None) -> str | None:
    if not raw:
        return None
    s = " ".join(str(raw).split()).strip()
    return s[:200] if s else None


def _parse_datetime(val: str | datetime | None) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(s)
        if dt and dt.tzinfo is None:
            return dt
        return dt
    except (TypeError, ValueError):
        return None


def normalize_date_posted(val: str | datetime | None) -> datetime | None:
    return _parse_datetime(val)


def normalize_job_in(job: JobIn) -> JobIn:
    req, pref = extract_skills_sectioned(job.description or "")
    req_skills = job.required_skills if job.required_skills is not None else req
    pref_skills = job.preferred_skills if job.preferred_skills is not None else pref
    return JobIn(
        title=normalize_title(job.title),
        company=normalize_company(job.company),
        location=normalize_location(job.location),
        description=" ".join((job.description or "").split()).strip() or job.title,
        source_url=job.source_url.strip(),
        source=job.source,
        date_posted=normalize_date_posted(job.date_posted),
        required_skills=req_skills,
        preferred_skills=pref_skills,
        employment_type=normalize_employment_type(job.employment_type),
        experience_level=normalize_experience_level(job.experience_level),
        salary=normalize_salary(job.salary),
    )


def strip_tracking_params(url: str) -> str:
    """Best-effort: keep query if it encodes job id; only strip common marketing params."""
    try:
        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

        p = urlparse(url)
        if not p.query:
            return url
        qs = parse_qs(p.query, keep_blank_values=True)
        drop = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid"}
        for k in list(qs.keys()):
            if k.lower() in drop:
                del qs[k]
        new_q = urlencode(qs, doseq=True)
        return urlunparse((p.scheme, p.netloc, p.path, p.params, new_q, ""))
    except Exception:
        return url
