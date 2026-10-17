"""
publisher.py — Push generated HTML to the GitHub Pages repo.

Uses the GitHub REST Contents API (PUT /repos/{owner}/{repo}/contents/{path})
to commit `{slug}.html` to the repo root. Handles the create-vs-update
distinction by fetching the file's blob SHA first (required for updates).
"""

from __future__ import annotations

import base64
import logging
import time

import requests

from config import get_config

logger = logging.getLogger("auto-scribe.publisher")

GITHUB_API_ROOT = "https://api.github.com"

# GitHub Pages rebuilds are not instantaneous; give the build a head start
# before Medium tries to scrape the URL.
PAGES_BUILD_WAIT_SECONDS = 15


class GitHubPublishError(RuntimeError):
    """Raised when the Contents API rejects the commit."""


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_existing_sha(session: requests.Session, contents_url: str) -> str | None:
    """
    Return the current blob SHA of the file, or None if it doesn't exist yet.

    PUT-ing an existing path without its SHA returns 409, so this lookup
    makes the publisher idempotent (re-publishing the same slug updates it).
    """
    response = session.get(contents_url, timeout=30)

    if response.status_code == 200:
        sha = response.json().get("sha")
        logger.info("File exists — updating (sha=%s)", sha)
        return sha
    if response.status_code == 404:
        logger.info("File does not exist yet — creating a new commit")
        return None

    # Any other status (401/403/5xx) is a real problem; surface it.
    raise GitHubPublishError(
        f"Unexpected status {response.status_code} checking file existence: "
        f"{response.text[:300]}"
    )


def push_to_github(html_content: str, slug: str) -> str:
    """
    Commit `html_content` to the Pages repo as `{slug}.html` (repo root).

    Args:
        html_content: The complete HTML document string.
        slug:         URL-safe file stem, e.g. "rag-pipelines".

    Returns:
        The final public GitHub Pages URL for the article.

    Raises:
        GitHubPublishError: on auth failure, API rejection, or bad input.
    """
    cfg = get_config()
    if not html_content.strip():
        raise ValueError("html_content is empty")
    if not slug or not slug.replace("-", "").isalnum():
        raise ValueError(f"Invalid slug: {slug!r}")

    path = f"{slug}.html"
    contents_url = (
        f"{GITHUB_API_ROOT}/repos/{cfg.github_username}/{cfg.github_repo}/contents/{path}"
    )
    live_url = f"{cfg.pages_base_url}/{path}"

    with requests.Session() as session:
        session.headers.update(_headers(cfg.github_token))

        existing_sha = _get_existing_sha(session, contents_url)

        payload = {
            "message": f"auto-scribe: publish {path}",
            # GitHub requires the content to be base64-encoded.
            "content": base64.b64encode(html_content.encode("utf-8")).decode("ascii"),
            "branch": "main",
        }
        if existing_sha:
            payload["sha"] = existing_sha

        logger.info("PUT %s", contents_url)
        response = session.put(contents_url, json=payload, timeout=60)

    if response.status_code not in (200, 201):
        raise GitHubPublishError(
            f"GitHub Contents API failed ({response.status_code}): "
            f"{response.text[:500]}"
        )

    commit_sha = response.json().get("commit", {}).get("sha", "?")
    logger.info("Committed %s (commit %s)", path, str(commit_sha)[:7])

    # Give GitHub Pages time to build before the importer scrapes the URL.
    logger.info("Waiting %ds for GitHub Pages to build...", PAGES_BUILD_WAIT_SECONDS)
    time.sleep(PAGES_BUILD_WAIT_SECONDS)

    return live_url


if __name__ == "__main__":  # manual smoke test with a trivial page
    logging.basicConfig(level=logging.INFO)
    demo = (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8"><title>Smoke test</title>'
        "</head><body><h1>Smoke test</h1><p>hello</p></body></html>"
    )
    print(push_to_github(demo, "smoke-test"))
