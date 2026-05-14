from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    u = url.strip()
    parsed = urlparse(u)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    # Drop fragments; keep query since sometimes job IDs are there, but trim tracking params later if needed.
    normalized = urlunparse((scheme, netloc, path, "", parsed.query, ""))
    return normalized

