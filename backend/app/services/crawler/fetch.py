from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


DEFAULT_UA = "JobPulseIRBot/1.0 academic crawler"


@dataclass
class Fetcher:
    crawl_delay_s: float = 1.0
    timeout_s: float = 20.0

    def get(self, url: str) -> tuple[int | None, str | None, str | None]:
        time.sleep(self.crawl_delay_s)
        try:
            with httpx.Client(
                headers={"User-Agent": DEFAULT_UA},
                timeout=self.timeout_s,
                follow_redirects=True,
            ) as client:
                r = client.get(url)
                return r.status_code, r.text, None
        except Exception as e:
            return None, None, str(e)


def allowed_by_domain(url: str, allowed_domain: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
        allowed = allowed_domain.lower().lstrip(".")
        return host == allowed or host.endswith("." + allowed)
    except Exception:
        return False


def allowed_by_any_domain(url: str, allowed_domains_csv: str) -> bool:
    """Comma-separated hostnames (e.g. github.com,amazon.jobs,boards.greenhouse.io)."""
    for part in allowed_domains_csv.split(","):
        part = part.strip()
        if part and allowed_by_domain(url, part):
            return True
    return False

