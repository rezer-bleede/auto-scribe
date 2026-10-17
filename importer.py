"""
importer.py — Drive Medium's "Import from link" UI with Playwright.

Relies on a persisted storage state (`medium_state.json`, created by
setup_login.py) so the browser starts already authenticated, avoiding
logins and CAPTCHAs on every run.
"""

from __future__ import annotations

import logging
import sys

from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from config import get_config

logger = logging.getLogger("auto-scribe.importer")

# Medium's import form changes occasionally; try selectors in order of
# specificity so a small UI tweak doesn't break the whole pipeline.
URL_INPUT_SELECTORS = (
    'input[placeholder*="link" i]',
    'input[placeholder*="url" i]',
    'input[placeholder*="paste" i]',
    'input[aria-label*="link" i]',
    'input[aria-label*="url" i]',
    'input[type="url"]',
    'input[type="text"]',
)

IMPORT_BUTTON_SELECTORS = (
    'button:has-text("Import")',
    'div[role="button"]:has-text("Import")',
    'input[type="submit"]',
)

# Medium's scraper fetches + converts the article server-side; it surfaces
# as a new draft rather than a redirect, so we wait this out.
SCRAPE_WAIT_MS = 10_000


class MediumImportError(RuntimeError):
    """Raised when the import flow cannot complete."""


def _find_first(page, selectors: tuple[str, ...], what: str, timeout_ms: int = 10_000):
    """Return the first visible element matching any selector in order."""
    deadline_budget = max(timeout_ms // len(selectors), 2500)
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=deadline_budget)
            logger.debug("Matched %s with selector %r", what, selector)
            return locator
        except PlaywrightTimeoutError:
            continue
    raise MediumImportError(
        f"Could not find the {what} on Medium's import page. "
        "The UI may have changed — update the selector list in importer.py."
    )


def import_to_medium(article_url: str) -> None:
    """
    Submit `article_url` to https://medium.com/me/import as a logged-in user.

    Loads cookies from medium_state.json, performs the import, then writes
    the (possibly refreshed) storage state back so future runs stay warm.

    Raises:
        MediumImportError: if login state is missing, the page redirects to
                           a login wall, or the form can't be completed.
    """
    cfg = get_config()

    if not article_url.startswith(("http://", "https://")):
        raise ValueError(f"article_url must be a full URL: {article_url!r}")

    if not cfg.medium_state_file.exists():
        raise MediumImportError(
            f"No saved Medium session found at {cfg.medium_state_file}. "
            "Run `python setup_login.py` once to authenticate before "
            "running the pipeline."
        )

    logger.info("Importing %s into Medium", article_url)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                storage_state=str(cfg.medium_state_file),
                # A realistic UA reduces the odds of bot heuristics firing.
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
            )
            page = context.new_page()

            try:
                page.goto(cfg.medium_import_url, wait_until="domcontentloaded", timeout=60_000)
                page.wait_for_load_state("networkidle", timeout=30_000)
            except PlaywrightTimeoutError as exc:
                raise MediumImportError(f"Failed to load Medium import page: {exc}") from exc

            # Session expired → Medium bounces us to a login/signup wall.
            if "/me/import" not in page.url:
                raise MediumImportError(
                    f"Redirected to {page.url!r} — the saved Medium session "
                    "has expired. Re-run `python setup_login.py`."
                )

            url_input = _find_first(page, URL_INPUT_SELECTORS, "URL input field")
            url_input.click()
            url_input.fill(article_url)

            import_button = _find_first(page, IMPORT_BUTTON_SELECTORS, "Import button")
            import_button.click()
            logger.info("Clicked Import; waiting %dms for Medium's scraper", SCRAPE_WAIT_MS)

            # Medium converts the URL to a draft asynchronously. Give the
            # scraper time to fetch GitHub Pages and create the draft, then
            # let any queued network requests settle.
            page.wait_for_timeout(SCRAPE_WAIT_MS)
            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except PlaywrightTimeoutError:
                pass  # idle is best-effort; the draft is already created.

            # Persist refreshed cookies (Medium rotates session tokens).
            context.storage_state(path=str(cfg.medium_state_file))
            logger.info("Import flow completed; storage state saved to %s",
                        cfg.medium_state_file.name)

        finally:
            browser.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if not target:
        sys.exit("usage: python importer.py <article-url>")
    import_to_medium(target)
