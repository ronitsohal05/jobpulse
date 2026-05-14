"""
Headless Chromium fetch for JS-rendered pages (optional).

Enabled via settings `scraper_render_js`. Requires `playwright` and
`playwright install --with-deps chromium` in the image (see Dockerfile).
"""
from __future__ import annotations

import atexit
import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_pw: Any = None
_browser: Any = None


def _close_singleton() -> None:
    global _pw, _browser
    with _lock:
        b, p = _browser, _pw
        _browser, _pw = None, None
    if b is not None:
        try:
            b.close()
        except Exception as exc:  # noqa: BLE001
            logger.debug("playwright_browser_close err=%s", exc)
    if p is not None:
        try:
            p.stop()
        except Exception as exc:  # noqa: BLE001
            logger.debug("playwright_stop err=%s", exc)


atexit.register(_close_singleton)


def fetch_rendered_html(
    url: str,
    *,
    user_agent: str,
    nav_timeout_ms: float,
    extra_wait_ms: float,
) -> tuple[int | None, str | None, str | None]:
    """
    Load `url` in headless Chromium and return (http_status, html, error).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, None, "playwright_not_installed"

    global _pw, _browser
    try:
        with _lock:
            if _browser is None:
                inst = sync_playwright().start()
                _pw = inst
                _browser = inst.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-software-rasterizer",
                    ],
                )
                logger.info("playwright_chromium_started")
            browser = _browser
    except Exception as e:
        logger.exception("playwright_launch_failed")
        return None, None, f"playwright_launch_failed:{e}"

    context = browser.new_context(user_agent=user_agent or "JobPulseBot/1.0")
    page = context.new_page()
    status: int | None = None
    body: str | None = None
    err: str | None = None
    try:
        nav_to = max(1000, int(nav_timeout_ms))
        resp = page.goto(url, wait_until="domcontentloaded", timeout=nav_to)
        status = resp.status if resp else None
        if extra_wait_ms > 0:
            time.sleep(min(extra_wait_ms / 1000.0, 30.0))
        body = page.content()
    except Exception as e:  # noqa: BLE001
        err = str(e)
        logger.info("playwright_goto_failed url=%s err=%s", url, err)
    finally:
        try:
            context.close()
        except Exception:
            pass
    logger.debug("playwright_fetch url=%s status=%s err=%s", url, status, err)
    if err:
        return status, body, err
    if status is not None and status >= 400:
        return status, body, f"http_{status}"
    return status, body, None
