from __future__ import annotations

import json
import logging

import httpx

from app.schemas.jobs import JobIn
from app.settings import settings

logger = logging.getLogger(__name__)


def extract_job_with_llm_optional(page_text: str, source_url: str) -> JobIn | None:
    """
    Optional LLM extraction when deterministic parsing is weak.
    Disabled unless settings.scraper_llm_enabled and OPENAI_API_KEY are set.
    """
    if not getattr(settings, "scraper_llm_enabled", False):
        return None
    api_key = getattr(settings, "openai_api_key", None)
    if not api_key:
        logger.info("scraper_llm_enabled but openai_api_key missing; skipping LLM extract")
        return None

    model = getattr(settings, "scraper_llm_model", "gpt-4o-mini")
    system = (
        "You extract structured job data from plain text. "
        "Return a single JSON object with keys exactly: "
        "title, company, location, description, source_url, source, date_posted, "
        "required_skills, preferred_skills, employment_type, experience_level, salary. "
        "Use null for unknown optional fields. date_posted must be ISO-8601 string or null. "
        "required_skills and preferred_skills are arrays of strings or null."
    )
    user = json.dumps({"source_url": source_url, "page_text": page_text}, ensure_ascii=False)

    try:
        with httpx.Client(timeout=60.0) as client:
            r = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            if r.status_code >= 400:
                logger.info("llm_extract_http status=%s body=%s", r.status_code, r.text[:500])
                return None
            payload = r.json()
            content = payload["choices"][0]["message"]["content"]
            data = json.loads(content)
            data["source_url"] = source_url
            return JobIn.model_validate(data)
    except Exception as e:
        logger.info("llm_extract_failed err=%s", e)
        return None
