from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    jobpulse_env: str = "dev"
    database_url: str = "postgresql+psycopg://jobpulse:jobpulse@localhost:5432/jobpulse"
    cors_origins_raw: str = "http://localhost:3000"
    faiss_dir: str = "/app/data/faiss"
    embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    redis_url: str = "redis://redis:6379/0"
    # Default 24h; override with CRAWL_SCHEDULE_INTERVAL_S (seconds) for the crawl-scheduler process.
    crawl_schedule_interval_s: int = 86400

    # Scraper / polite HTTP
    scraper_user_agent: str = "JobPulseBot/1.0 (job aggregation; contact via site operator)"
    scraper_respect_robots: bool = True
    scraper_min_interval_per_host_s: float = 1.0
    scraper_http_timeout_s: float = 25.0
    scraper_http_max_retries: int = 3
    scraper_llm_enabled: bool = False
    scraper_llm_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None

    # JS career sites: headless Chromium via Playwright (see Dockerfile `playwright install`).
    scraper_render_js: bool = False
    scraper_js_nav_timeout_ms: float = 45_000.0
    scraper_js_extra_wait_ms: float = 2_000.0

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


settings = Settings()

