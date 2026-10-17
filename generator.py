"""
generator.py — LLM-powered HTML article generation.

Produces a clean, strictly-formatted HTML5 document for a given topic
using the OpenAI Chat Completions API. The output is designed to be
Medium-import friendly (semantic tags only, no divs/CSS).
"""

from __future__ import annotations

import logging
import re

from openai import OpenAI

from config import get_config

logger = logging.getLogger("auto-scribe.generator")

# Number of attempts to obtain a schema-valid document before giving up.
MAX_GENERATION_ATTEMPTS = 3

# The system prompt is intentionally strict: Medium's importer handles
# simple semantic HTML best, so we forbid layout markup entirely.
SYSTEM_PROMPT_TEMPLATE = """\
You are an expert technical writer producing a single, complete HTML5
article for publication on Medium via GitHub Pages.

Canonical URL of this article (REQUIRED, exact value):
{canonical_url}

STRICT OUTPUT RULES — you MUST follow every rule:
1. Output ONLY a valid HTML5 document. Begin with <!DOCTYPE html> and end
   with </html>. Output NOTHING else — no explanations, no preamble.
2. The <head> MUST contain:
     - <meta charset="utf-8">
     - <title>...</title> (an engaging title for the topic)
     - <link rel="canonical" href="{canonical_url}">
3. Inside <body>, use ONLY these tags:
   <h1>, <h2>, <p>, <ul>, <li>, <strong>, <pre>, <code>, <em>, <blockquote>,
   <figure>, <img>, <figcaption>, <main>, <article>, <header>.
   NEVER use <div> or <span>. NEVER use inline CSS, style attributes,
   <style> blocks, classes, ids, JavaScript, or iframes.
4. Every <img> src MUST be an absolute https:// URL to a real, stable image
   (e.g. https://images.unsplash.com/... with sizing query params). Always
   include a descriptive alt attribute. Images are optional; include at
   most 2.
5. Structure: one <h1> title, an intro paragraph, 3–6 <h2> sections, at
   least one <ul> list, optional <pre><code> snippets, and a closing
   paragraph. Aim for 600–900 words of genuinely useful, accurate prose.
6. Write in English, in a clear expert voice. No marketing fluff.
"""


def _strip_markdown_fences(text: str) -> str:
    """Remove ```html ... ``` (or ``` ... ```) wrappers an LLM may add."""
    cleaned = text.strip()

    # Full fenced block: ```html\n<...>\n```
    match = re.match(
        r"^```(?:html|xml)?\s*\n(?P<body>.*?)\n?```$", cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group("body").strip()

    # Defensive: dangling fences at either end.
    cleaned = re.sub(r"^```(?:html|xml)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _validate_html(html: str, canonical_url: str) -> None:
    """Enforce the hard formatting rules; raise ValueError if violated."""
    lowered = html.lower()

    checks = (
        ("<!doctype html" in lowered, "missing <!DOCTYPE html declaration"),
        ("<title>" in lowered and "</title>" in lowered, "missing <title>"),
        (
            'rel="canonical"' in lowered and canonical_url.lower() in lowered,
            f"missing canonical link to {canonical_url}",
        ),
        ("<h1>" in lowered, "missing <h1> heading"),
        ("<p>" in lowered, "missing <p> paragraphs"),
    )
    for ok, reason in checks:
        if not ok:
            raise ValueError(f"Generated HTML invalid: {reason}")

    # Forbidden constructs (checked on tag boundaries to avoid false
    # positives inside text content).
    forbidden = re.findall(r"<\s*(div|span|style|script|iframe|link\s[^>]*stylesheet)\b", lowered)
    if forbidden:
        raise ValueError(f"Generated HTML uses forbidden tags: {sorted(set(forbidden))}")
    if re.search(r"<[^>]+\bstyle\s*=", lowered):
        raise ValueError("Generated HTML uses inline CSS (style attributes)")

    # Every <img> must use an absolute https URL.
    for src in re.findall(r"<img[^>]*\bsrc\s*=\s*[\"']([^\"']+)", lowered):
        if not src.startswith("https://"):
            raise ValueError(f"Image src is not an absolute https URL: {src}")


def generate_html_article(topic: str, slug: str) -> str:
    """
    Generate a strictly-formatted HTML5 article about `topic`.

    Args:
        topic: Human-readable article subject, e.g. "RAG pipelines".
        slug:  URL slug (kebab-case) that will become /{slug}.html on
               GitHub Pages, e.g. "rag-pipelines-explained".

    Returns:
        The validated HTML document as a string.

    Raises:
        ValueError: if the topic/slug are unusable.
        RuntimeError: if the LLM cannot produce valid HTML after retries.
    """
    if not topic or not topic.strip():
        raise ValueError("topic must be a non-empty string")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug or ""):
        raise ValueError(
            f"slug must be lowercase kebab-case (letters, digits, hyphens): {slug!r}"
        )

    cfg = get_config()
    canonical_url = f"{cfg.pages_base_url}/{slug}.html"
    client = OpenAI(api_key=cfg.openai_api_key)

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(canonical_url=canonical_url)
    user_prompt = (
        f"Write the article now.\n"
        f"Topic: {topic.strip()}\n"
        f"Target file name: {slug}.html\n"
        f"Remember: output ONLY the raw HTML document."
    )

    last_error: Exception | None = None
    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        logger.info("Generating article (attempt %d/%d) with model %s",
                    attempt, MAX_GENERATION_ATTEMPTS, cfg.openai_model)
        try:
            response = client.chat.completions.create(
                model=cfg.openai_model,
                temperature=0.7,
                max_tokens=3000,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = (response.choices[0].message.content or "").strip()
            if not raw:
                raise ValueError("LLM returned an empty response")

            html = _strip_markdown_fences(raw)
            _validate_html(html, canonical_url)

            logger.info("Article generated and validated (%d chars)", len(html))
            return html

        except ValueError as exc:
            # Format violation — retry with feedback so the model can fix it.
            last_error = exc
            logger.warning("Attempt %d produced invalid HTML: %s", attempt, exc)
            user_prompt += f"\n\nFix this problem: {exc}. Re-output the full HTML."

    raise RuntimeError(
        f"Failed to generate valid HTML after {MAX_GENERATION_ATTEMPTS} attempts"
    ) from last_error


if __name__ == "__main__":  # manual smoke test
    logging.basicConfig(level=logging.INFO)
    demo_html = generate_html_article(
        topic="What are AI coding agents and how do they work?",
        slug="ai-coding-agents",
    )
    print(demo_html[:1000], "...")
