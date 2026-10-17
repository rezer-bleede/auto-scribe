# AGENTS.md — auto-scribe operating manual

Instructions for AI coding agents (and humans) working in this repository.
Read this before changing code or publishing articles.

## What this repo is

**auto-scribe** is an automated publishing pipeline for a Medium knowledge
base about AI, coding agents, and automated content creation:

```
OpenAI generates → GitHub Pages hosts → Medium imports as a draft
   generator.py        publisher.py              importer.py
```

The repo doubles as the GitHub Pages **project site**: every article is a
single `{slug}.html` file committed to the repo root and served at
`https://rezer-bleede.github.io/auto-scribe/{slug}.html`.

## File map

| File | Role |
|------|------|
| `config.py` | Loads `.env` into a frozen, validated `Config`; secrets never live in code |
| `generator.py` | OpenAI article generation + strict HTML validation (`SYSTEM_PROMPT_TEMPLATE` at generator.py:25, `_validate_html` at generator.py:73) |
| `publisher.py` | GitHub Contents API commit (`push_to_github` at publisher.py:64), base64 + sha-fetch for updates, 15s Pages build wait |
| `importer.py` | Playwright headless Medium import via persisted `medium_state.json` |
| `setup_login.py` | One-time interactive Medium login that creates `medium_state.json` |
| `main.py` | CLI orchestrator: generate → publish → import |
| `docs/WRITING_GUIDE.md` | Editorial style + HTML format spec for articles |

## Setup & run commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env        # fill in OPENAI_API_KEY + GITHUB_TOKEN
python config.py            # validates env, prints non-secret values only
python setup_login.py       # one-time, visible-browser Medium login
python main.py --topic "..." --slug my-slug [--skip-import]
```

Exit codes from `main.py`: `0` success · `1` generation · `2` publish ·
`3` Medium import · `10` missing/invalid configuration.

## Hard rules — do not break these

### Secrets & state
1. Secrets come from `.env` only (python-dotenv). **Never** hardcode API
   keys or tokens in code, comments, docs, or commit messages.
2. `medium_state.json` contains live auth cookies. It is git-ignored —
   never stage, print, or upload it.
3. When shell-authenticating against GitHub for a one-off command, pull
   the token from `.env` via substitution (`$(grep '^GITHUB_TOKEN=' .env |
   cut -d= -f2-)`), so raw token values never appear in commands or logs.

### Content & publishing
4. Articles are committed **through `publisher.py`** (Contents API), never
   by hand-editing tracked `*.html` files. Root `*.html` is git-ignored
   locally for this reason; tracked copies arrive via `git pull` after a
   publish commits to the remote.
5. Every article must satisfy `docs/WRITING_GUIDE.md`. The machine-checkable
   subset is enforced by `_validate_html` (generator.py:73) — slug format by
   `generate_html_article` (generator.py:105), kebab-case, ≤ 60 chars.
6. The canonical URL is **required** and must match
   `https://rezer-bleede.github.io/auto-scribe/{slug}.html` exactly, or the
   Medium import credits the wrong source.
7. Keep `SYSTEM_PROMPT_TEMPLATE` (generator.py:25) and
   `docs/WRITING_GUIDE.md` in sync: if you change an allowed/forbidden tag
   list, a length rule, or the image policy, change **both** and the
   validator in the same commit.

### Pipeline mechanics
8. `publisher.py` waits `PAGES_BUILD_WAIT_SECONDS` (publisher.py:25) before
   returning. After any publish, still poll the live URL for HTTP 200 —
   first-ever builds (or enabling Pages) can take minutes.
9. Playwright must run headless in the pipeline and load/save
   `medium_state.json`; only `setup_login.py` may open a visible browser.
10. If Medium's import UI changes, update the selector tuples in
    `importer.py` (`URL_INPUT_SELECTORS` at importer.py:25 and
    `IMPORT_BUTTON_SELECTORS`). Do not add per-run credentials or CAPTCHA
    workarounds — re-authenticate with `setup_login.py`.
11. GitHub Pages must be enabled (Settings → Pages → Deploy from a branch,
    `main` / root). A fine-grained PAT needs **Contents: Read and write**
    (publishing) and **Pages: Read and write** (enabling/building) — a
    403 from `POST /repos/{owner}/{repo}/pages` means the latter is missing.

## Article workflow checklist

1. Pick `topic` + kebab-case `slug` (no collisions — re-publishing the same
   slug **updates** the live article, it is idempotent).
2. Generate: LLM via `generate_html_article`, or author it inline following
   `docs/WRITING_GUIDE.md`.
3. Validate with `_validate_html` before pushing — cheap failure beats a
   bad commit.
4. Publish with `push_to_github` → returns the live URL.
5. Poll the URL until 200, then import (`importer.py` or `main.py`).
6. `git pull` so the local clone matches the remote after each publish.

## Commit conventions

- Article commits (created by the API): `auto-scribe: publish {slug}.html`
- Code commits: imperative subject ≤ 72 chars, body wraps at ~76; explain
  the *why*, not the *what*. Never `git commit -A` blindly — stage intended
  files and confirm `.env`/`medium_state.json` are absent from the diff.

## Documentation pointers

- Writing style & HTML constraints: **`docs/WRITING_GUIDE.md`**
- User-facing setup/troubleshooting: **`README.md`**
- Reference article (the style exemplar): `ai-coding-agents-explained.html`
  on Pages
