from __future__ import annotations

import re
from urllib.parse import urlparse

from .types import JobSourceType


class JobSourceDetector:
    """Detect ATS / platform from URL and optional HTML (script tags, embedded endpoints)."""

    _GREENHOUSE_HOST = re.compile(r"(^|\.)boards\.greenhouse\.io$|(^|\.)job-boards\.greenhouse\.io$", re.I)
    _LEVER_HOST = re.compile(r"(^|\.)jobs\.lever\.co$|(^|\.)lever\.co$", re.I)
    _WORKDAY_HOST = re.compile(r"myworkdayjobs\.com$|workday\.com$", re.I)
    _ASHBY_HOST = re.compile(r"(^|\.)jobs\.ashbyhq\.com$", re.I)
    _SR_HOST = re.compile(r"careers\.smartrecruiters\.com$|(^|\.)smartrecruiters\.com$", re.I)
    _ICIMS_HOST = re.compile(r"icims\.com$", re.I)
    _BAMBOO_HOST = re.compile(r"bamboohr\.com$", re.I)

    @classmethod
    def detect_from_url(cls, url: str) -> JobSourceType:
        try:
            host = urlparse(url).netloc.lower()
        except Exception:
            return "generic"
        host = host.split("@")[-1]
        if cls._GREENHOUSE_HOST.search(host):
            return "greenhouse"
        if cls._LEVER_HOST.search(host):
            return "lever"
        if cls._WORKDAY_HOST.search(host):
            return "workday"
        if cls._ASHBY_HOST.search(host):
            return "ashby"
        if cls._SR_HOST.search(host):
            return "smartrecruiters"
        if cls._ICIMS_HOST.search(host):
            return "icims"
        if cls._BAMBOO_HOST.search(host):
            return "bamboohr"
        return "generic"

    @classmethod
    def detect(cls, url: str, html: str | None = None) -> JobSourceType:
        base = cls.detect_from_url(url)
        if not html:
            return base
        if base != "generic":
            return base
        hl = html[:500_000].lower()
        if "boards-api.greenhouse.io" in hl:
            return "greenhouse"
        if "api.lever.co" in hl:
            return "lever"
        if "myworkdayjobs.com" in hl or ("workday" in hl and "cxs" in hl):
            return "workday"
        if "ashbyhq.com" in hl and "ashby" in hl:
            return "ashby"
        if "smartrecruiters" in hl:
            return "smartrecruiters"
        if "icims.com" in hl:
            return "icims"
        if "bamboohr.com" in hl:
            return "bamboohr"
        return "generic"
