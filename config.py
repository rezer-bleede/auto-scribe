"""
config.py — Centralized configuration for the auto-scribe pipeline.

Loads secrets and settings from a `.env` file (via python-dotenv) and
exposes them through a frozen, validated `Config` dataclass so the rest
of the codebase never touches `os.environ` directly.

Security rule: secrets live ONLY in `.env`. Never hardcode them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Project root = directory containing this file.
BASE_DIR = Path(__file__).resolve().parent

# Load .env from the project root (no-op if the file does not exist;
# real values are still picked up from the process environment).
load_dotenv(BASE_DIR / ".env", override=False)


class ConfigError(RuntimeError):
    """Raised when a required environment variable is missing/invalid."""


@dataclass(frozen=True)
class Config:
    """Immutable, validated view of the pipeline's environment."""

    # --- OpenAI ---
    openai_api_key: str
    openai_model: str

    # --- GitHub ---
    github_token: str
    github_username: str
    github_repo: str

    # --- Derived URLs ---
    pages_base_url: str  # e.g. https://rezer-bleede.github.io/auto-scribe

    # --- Medium / Playwright ---
    medium_state_file: Path  # absolute path to medium_state.json
    medium_import_url: str = "https://medium.com/me/import"


def _require(name: str) -> str:
    """Return an env var or raise a clear, actionable ConfigError."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


def get_config() -> Config:
    """Build the Config object, validating all required secrets exist."""
    openai_api_key = _require("OPENAI_API_KEY")
    github_token = _require("GITHUB_TOKEN")
    github_username = _require("GITHUB_USERNAME")
    github_repo = _require("GITHUB_REPO")

    # Project-site GitHub Pages: content is served from the repo root,
    # so every article lands at /{slug}.html under this base URL.
    pages_base_url = f"https://{github_username}.github.io/{github_repo}"

    state_file_name = os.getenv("MEDIUM_STATE_FILE", "medium_state.json")
    medium_state_file = (BASE_DIR / state_file_name).resolve()

    return Config(
        openai_api_key=openai_api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o").strip() or "gpt-4o",
        github_token=github_token,
        github_username=github_username,
        github_repo=github_repo,
        pages_base_url=pages_base_url,
        medium_state_file=medium_state_file,
    )


if __name__ == "__main__":  # quick sanity check: `python config.py`
    try:
        cfg = get_config()
    except ConfigError as err:
        raise SystemExit(f"Configuration problem: {err}")
    # Print everything EXCEPT the secrets to verify the environment loads.
    print("Configuration OK:")
    print(f"  model:        {cfg.openai_model}")
    print(f"  repo:         {cfg.github_username}/{cfg.github_repo}")
    print(f"  pages base:   {cfg.pages_base_url}")
    print(f"  state file:   {cfg.medium_state_file}")
