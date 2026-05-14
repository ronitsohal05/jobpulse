from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.jobs import JobIn

from .types import JobSourceType


class BaseJobAdapter(ABC):
    """Abstract adapter: discover listing URLs, extract a single job, batch extract."""

    source: JobSourceType

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def discover_job_urls(self, url: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def extract_job(self, url: str) -> JobIn:
        raise NotImplementedError

    def extract_jobs(self, url: str) -> list[JobIn]:
        jobs: list[JobIn] = []
        for u in self.discover_job_urls(url):
            try:
                jobs.append(self.extract_job(u))
            except Exception:
                continue
        return jobs
