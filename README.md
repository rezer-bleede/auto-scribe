# auto-scribe

An automated knowledge base exploring AI, coding agents, and the future of
automated content creation and deployment.

`auto-scribe` is a three-stage publishing pipeline:

```
 OpenAI generates ──▶ GitHub Pages hosts ──▶ Medium imports as a draft
    (generator.py)       (publisher.py)          (importer.py)
```

Articles are served from the GitHub Pages **project site**, so each one is
live at `https://rezer-bleede.github.io/auto-scribe/{slug}.html`.

## Requirements

- Python 3.10+
- An OpenAI API key
- A GitHub token with write access to `rezer-bleede/auto-scribe`
- A Medium account (one-time manual login, see below)

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install the Chromium browser used by Playwright
playwright install chromium

# 3. Configure secrets (never commit the resulting .env)
cp .env.example .env
#    then edit .env: OPENAI_API_KEY, GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_REPO

# 4. Verify configuration (prints non-secret values only)
python config.py
```

## One-time Medium login

Headless imports reuse a persisted browser session to skip logins/CAPTCHAs.
Create it once with the interactive helper:

```bash
python setup_login.py
```

A visible Chromium window opens at `medium.com/me/import`. Log in manually
(including 2FA/CAPTCHA if prompted), wait for the import page to load, then
press **Enter** in the terminal. Your session is saved to `medium_state.json`
(git-ignored — it contains auth cookies).

Re-run this whenever the session expires (the pipeline will tell you if it did).

## Running the pipeline

```bash
# Explicit topic + slug
python main.py --topic "RAG pipelines explained" --slug rag-pipelines-explained

# Or use the built-in defaults (DEFAULT_TOPIC / DEFAULT_SLUG in main.py)
python main.py

# Generate + publish only (skip Medium)
python main.py --skip-import
```

Exit codes: `0` success · `1` generation · `2` publish · `3` Medium import ·
`10` missing configuration.

## File map

| File | Purpose |
|------|---------|
| `config.py` | Loads/validates `.env` into a frozen `Config` object |
| `generator.py` | Strict HTML5 article generation via OpenAI (canonical URL, no divs/inline CSS, absolute image URLs) |
| `publisher.py` | GitHub Contents API commit (`PUT`, with `sha` fetch for updates) + 15s Pages build wait |
| `importer.py` | Playwright headless import into `medium.com/me/import` |
| `setup_login.py` | One-time interactive login → `medium_state.json` |
| `main.py` | Orchestrator + CLI |

## Troubleshooting

- **`401/403` from GitHub** — token lacks `repo`/Contents write scope, or the
  repo name in `.env` is wrong.
- **Redirected to a login wall during import** — Medium session expired;
  re-run `python setup_login.py`.
- **"Could not find the URL input field"** — Medium changed its import UI;
  update `URL_INPUT_SELECTORS` in `importer.py`.
- **Imported draft is empty** — GitHub Pages hadn't built yet; the publisher
  already waits 15s, re-run `python importer.py <url>` if Pages was slow.
