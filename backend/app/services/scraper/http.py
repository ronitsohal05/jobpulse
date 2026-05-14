from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.settings import settings

from . import js_render
from .logging_types import ScraperRequestLog

logger = logging.getLogger(__name__)


@dataclass
class PoliteHttpClient:
    """
    Polite HTTP client: optional robots.txt, per-host spacing, retries with backoff, request logs.
    Does not bypass auth, CAPTCHAs, or anti-bot systems.
    """

    user_agent: str = ""
    timeout_s: float = 25.0
    min_interval_per_host_s: float = 1.0
    max_retries: int = 3
    respect_robots: bool = True
    render_js: bool = False
    js_nav_timeout_ms: float = 45_000.0
    js_extra_wait_ms: float = 2_000.0
    request_logs: list[ScraperRequestLog] = field(default_factory=list)

    _last_request_mono: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    _robots: dict[str, RobotFileParser | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.user_agent:
            self.user_agent = getattr(settings, "scraper_user_agent", "JobPulseBot/1.0")

    def _host(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower().split("@")[-1]
        except Exception:
            return ""

    def _sleep_for_politeness(self, url: str) -> None:
        host = self._host(url)
        if not host:
            return
        now = time.monotonic()
        last = self._last_request_mono[host]
        wait = self.min_interval_per_host_s - (now - last)
        if wait > 0:
            time.sleep(wait)

    def _robots_parser(self, url: str) -> RobotFileParser | None:
        if not self.respect_robots:
            return None
        host = self._host(url)
        if not host:
            return None
        if host in self._robots:
            return self._robots[host]
        rp = RobotFileParser()
        robots_url = f"{urlparse(url).scheme or 'https'}://{host}/robots.txt"
        try:
            with httpx.Client(headers={"User-Agent": self.user_agent}, timeout=self.timeout_s) as c:
                r = c.get(robots_url)
                if r.status_code == 200 and r.text:
                    rp.parse(r.text.splitlines())
                else:
                    rp.parse(["User-agent: *", "Allow: /"])
        except Exception as e:
            logger.debug("robots_fetch_failed host=%s err=%s", host, e)
            rp.parse(["User-agent: *", "Allow: /"])
        self._robots[host] = rp
        return rp

    def can_fetch(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        rp = self._robots_parser(url)
        if rp is None:
            return True
        try:
            return rp.can_fetch(self.user_agent, url)
        except Exception:
            return True

    def get(self, url: str) -> tuple[int | None, str | None, str | None]:
        if not self.can_fetch(url):
            self.request_logs.append(
                ScraperRequestLog(
                    url=url,
                    status_code=None,
                    error="disallowed_by_robots.txt",
                    robots_allowed=False,
                )
            )
            return None, None, "disallowed_by_robots.txt"

        self._sleep_for_politeness(url)
        t0 = time.perf_counter()
        status: int | None = None
        body: str | None = None
        err: str | None = None
        host = self._host(url)

        if self.render_js:
            status, body, err = js_render.fetch_rendered_html(
                url,
                user_agent=self.user_agent,
                nav_timeout_ms=self.js_nav_timeout_ms,
                extra_wait_ms=self.js_extra_wait_ms,
            )
            self._last_request_mono[host] = time.monotonic()
            dur_ms = (time.perf_counter() - t0) * 1000
            self.request_logs.append(
                ScraperRequestLog(
                    url=url,
                    status_code=status,
                    error=err,
                    duration_ms=dur_ms,
                    robots_allowed=True,
                )
            )
            if err:
                return status, body, err
            if status is not None and status >= 400:
                return status, body, f"http_{status}"
            return status, body, None

        try:
            with httpx.Client(
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout_s,
                follow_redirects=True,
            ) as client:
                for attempt in range(self.max_retries):
                    try:
                        r = client.get(url, follow_redirects=True)
                        status = r.status_code
                        body = r.text
                        if status in (429, 500, 502, 503, 504) and attempt < self.max_retries - 1:
                            time.sleep(min(2**attempt, 16))
                            continue
                        break
                    except (httpx.TimeoutException, httpx.TransportError) as e:
                        err = str(e)
                        if attempt >= self.max_retries - 1:
                            raise
                        time.sleep(min(2**attempt, 8))
        except Exception as e:
            err = str(e)
            logger.info("http_get_failed url=%s err=%s", url, err)

        self._last_request_mono[host] = time.monotonic()
        dur_ms = (time.perf_counter() - t0) * 1000
        self.request_logs.append(
            ScraperRequestLog(
                url=url,
                status_code=status,
                error=err,
                duration_ms=dur_ms,
                robots_allowed=True,
            )
        )
        if err:
            return status, body, err
        if status is not None and status >= 400:
            return status, body, f"http_{status}"
        return status, body, None


def client_from_settings() -> PoliteHttpClient:
    return PoliteHttpClient(
        user_agent=getattr(settings, "scraper_user_agent", "JobPulseBot/1.0"),
        respect_robots=getattr(settings, "scraper_respect_robots", True),
        min_interval_per_host_s=getattr(settings, "scraper_min_interval_per_host_s", 1.0),
        timeout_s=getattr(settings, "scraper_http_timeout_s", 25.0),
        max_retries=getattr(settings, "scraper_http_max_retries", 3),
        render_js=getattr(settings, "scraper_render_js", False),
        js_nav_timeout_ms=getattr(settings, "scraper_js_nav_timeout_ms", 45_000.0),
        js_extra_wait_ms=getattr(settings, "scraper_js_extra_wait_ms", 2_000.0),
    )
