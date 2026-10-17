"""
main.py — auto-scribe pipeline orchestrator.

Runs the full flow sequentially:

    1. generator.generate_html_article(topic, slug)  → HTML string
    2. publisher.push_to_github(html, slug)          → live Pages URL
    3. importer.import_to_medium(url)                → Medium draft

Usage:
    python main.py --topic "Your article topic" --slug my-article-slug
    python main.py            # falls back to the DEFAULT_* values below
"""

from __future__ import annotations

import argparse
import logging
import re
import sys

from config import ConfigError, get_config
from generator import generate_html_article
from importer import MediumImportError, import_to_medium
from publisher import GitHubPublishError, push_to_github

logger = logging.getLogger("auto-scribe")

# ---------------------------------------------------------------------
# Hardcoded fallbacks used when CLI flags are omitted. Edit freely, or
# prefer the CLI for anything beyond a quick test run.
# ---------------------------------------------------------------------
DEFAULT_TOPIC = "How AI coding agents plan, use tools, and ship software"
DEFAULT_SLUG = "ai-coding-agents-explained"


def _slugify(topic: str) -> str:
    """Derive a URL-safe kebab-case slug from a topic string."""
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return slug[:60].rstrip("-") or "untitled-article"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auto-scribe",
        description="Generate an HTML article, publish it to GitHub Pages, "
                    "and import it into Medium as a draft.",
    )
    parser.add_argument(
        "--topic",
        default=None,
        help=f"Article topic (default: {DEFAULT_TOPIC!r})",
    )
    parser.add_argument(
        "--slug",
        default=None,
        help="URL slug; defaults to a slugified topic, e.g. 'ai-coding-agents'",
    )
    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Generate + publish only (useful while debugging Medium)",
    )
    return parser


def run_pipeline(topic: str, slug: str, skip_import: bool = False) -> int:
    """Execute generate → publish → import. Returns a process exit code."""
    step, total = 0, 2 if skip_import else 3

    # --- Step 1: generate -------------------------------------------------
    step += 1
    logger.info("[%d/%d] Generating article: %r (slug: %s)", step, total, topic, slug)
    try:
        html = generate_html_article(topic=topic, slug=slug)
        logger.info("[%d/%d] Generation complete (%d chars)", step, total, len(html))
    except Exception:
        logger.exception("[%d/%d] Article generation failed", step, total)
        return 1

    # --- Step 2: publish to GitHub Pages -----------------------------------
    step += 1
    logger.info("[%d/%d] Publishing %s.html to GitHub Pages", step, total, slug)
    try:
        live_url = push_to_github(html_content=html, slug=slug)
        logger.info("[%d/%d] Live at: %s", step, total, live_url)
    except (GitHubPublishError, ConfigError) as exc:
        logger.error("[%d/%d] Publishing failed: %s", step, total, exc)
        return 2
    except Exception:
        logger.exception("[%d/%d] Unexpected publishing error", step, total)
        return 2

    if skip_import:
        logger.info("--skip-import set; pipeline stopped after publishing.")
        return 0

    # --- Step 3: import into Medium ----------------------------------------
    step += 1
    logger.info("[%d/%d] Importing into Medium as a draft", step, total)
    try:
        import_to_medium(article_url=live_url)
        logger.info("[%d/%d] Import complete — check medium.com/me/stories/drafts",
                    step, total)
    except MediumImportError as exc:
        logger.error("[%d/%d] Medium import failed: %s", step, total, exc)
        logger.error("Hint: the article IS live on GitHub Pages. After fixing "
                     "your session, re-run just the import step:")
        logger.error("    python importer.py %s", live_url)
        return 3
    except Exception:
        logger.exception("[%d/%d] Unexpected Medium import error", step, total)
        return 3

    logger.info("Pipeline finished successfully.")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    args = _build_arg_parser().parse_args(argv)
    topic = args.topic or DEFAULT_TOPIC
    slug = args.slug or _slugify(topic)

    # Fail fast on missing secrets before touching any external service.
    try:
        get_config()
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        return 10

    return run_pipeline(topic=topic, slug=slug, skip_import=args.skip_import)


if __name__ == "__main__":
    sys.exit(main())
