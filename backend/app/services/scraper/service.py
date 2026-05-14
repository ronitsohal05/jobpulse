from __future__ import annotations

from app.schemas.jobs import JobIn

from .adapters.ashby import AshbyAdapter
from .adapters.generic import BambooHrAdapter, GenericJobPageAdapter, IcimsAdapter
from .adapters.greenhouse import GreenhouseAdapter
from .adapters.lever import LeverAdapter
from .adapters.smartrecruiters import SmartRecruitersAdapter
from .adapters.workday import WorkdayAdapter
from .base import BaseJobAdapter
from .detector import JobSourceDetector
from .http import PoliteHttpClient, client_from_settings
from .normalizer import normalize_job_in, normalize_source_url
from .types import JobSourceType


class JobScraperService:
    """
    Orchestrates detection, discovery, extraction, validation, deduplication.
    """

    def __init__(self, http: PoliteHttpClient | None = None) -> None:
        self.http = http or client_from_settings()

    def _adapters(
        self,
        *,
        job_link_pattern: str | None,
        allowed_domains_csv: str | None,
        max_discovered_links: int,
        max_listing_pages: int = 25,
    ) -> list[BaseJobAdapter]:
        return [
            GreenhouseAdapter(self.http),
            LeverAdapter(self.http),
            WorkdayAdapter(self.http),
            AshbyAdapter(self.http),
            SmartRecruitersAdapter(self.http),
            IcimsAdapter(
                self.http,
                job_link_pattern=job_link_pattern,
                allowed_domains_csv=allowed_domains_csv,
                max_discovered_links=max_discovered_links,
                max_listing_pages=max_listing_pages,
            ),
            BambooHrAdapter(
                self.http,
                job_link_pattern=job_link_pattern,
                allowed_domains_csv=allowed_domains_csv,
                max_discovered_links=max_discovered_links,
                max_listing_pages=max_listing_pages,
            ),
            GenericJobPageAdapter(
                self.http,
                job_link_pattern=job_link_pattern,
                allowed_domains_csv=allowed_domains_csv,
                max_discovered_links=max_discovered_links,
                max_listing_pages=max_listing_pages,
            ),
        ]

    def _pick_adapter(self, url: str, adapters: list[BaseJobAdapter]) -> BaseJobAdapter:
        for a in adapters:
            if a.can_handle(url):
                return a
        return adapters[-1]

    def _filter_discovered(self, urls: list[str], allowed_domains_csv: str | None) -> list[str]:
        if not allowed_domains_csv:
            return urls
        from app.services.crawler.fetch import allowed_by_any_domain

        return [u for u in urls if allowed_by_any_domain(u, allowed_domains_csv)]

    def scrape_seed_urls(
        self,
        seeds: list[str],
        *,
        job_link_pattern: str | None = None,
        allowed_domains_csv: str | None = None,
        max_pages: int = 100,
        max_discovered_links: int = 500,
        max_listing_pages: int = 25,
    ) -> list[JobIn]:
        adapters = self._adapters(
            job_link_pattern=job_link_pattern,
            allowed_domains_csv=allowed_domains_csv,
            max_discovered_links=max_discovered_links,
            max_listing_pages=max_listing_pages,
        )
        collected: dict[str, JobIn] = {}

        for seed in seeds:
            if not seed.strip():
                continue
            seed_adapter = self._pick_adapter(seed, adapters)
            discovered = seed_adapter.discover_job_urls(seed)
            discovered = self._filter_discovered(discovered, allowed_domains_csv)
            if not discovered:
                discovered = [seed]
            discovered = discovered[:max_pages]

            seen_norm: set[str] = set()
            for u in discovered:
                if not u.strip():
                    continue
                norm = normalize_source_url(u)
                if norm in seen_norm:
                    continue
                seen_norm.add(norm)
                try:
                    job_adapter = self._pick_adapter(u, adapters)
                    job = job_adapter.extract_job(u)
                    job = normalize_job_in(job)
                    key = normalize_source_url(job.source_url)
                    collected[key] = job
                except Exception:
                    continue

        return list(collected.values())

    def detect_only(self, url: str) -> JobSourceType:
        st, html, err = self.http.get(url)
        return JobSourceDetector.detect(url, html if not err else None)
