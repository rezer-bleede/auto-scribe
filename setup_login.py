"""
setup_login.py — One-time, interactive Medium authentication.

Opens a VISIBLE Chromium window, navigates to Medium's import page, and
lets you log in by hand (including any 2FA / CAPTCHA). Once you close the
tab or press Enter here, the browser's cookies + localStorage are saved
to `medium_state.json` for headless reuse by importer.py.

Run once: `python setup_login.py`
"""

from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

from config import get_config


def main() -> int:
    cfg = get_config()
    state_path = cfg.medium_state_file

    print("=" * 64)
    print(" auto-scribe — Medium login helper")
    print("=" * 64)
    if state_path.exists():
        print(f"NOTE: an existing session at {state_path.name} will be")
        print("      overwritten when you press Enter below.")
    print()
    print("A browser window will now open at medium.com/me/import.")
    print("  1. Log into Medium manually (email/password or SSO/2FA).")
    print("  2. Wait until the Import page finishes loading — you should")
    print("     see the 'Import from link or document' form.")
    print("  3. Come back to this terminal and press ENTER.")
    print()

    with sync_playwright() as playwright:
        # headless=False is the point of this script: humans need a window.
        browser = playwright.chromium.launch(headless=False)
        try:
            # Reuse any previous state so a refresh login keeps settings.
            context = (
                browser.new_context(storage_state=str(state_path))
                if state_path.exists()
                else browser.new_context()
            )
            page = context.new_page()
            page.goto(cfg.medium_import_url, wait_until="domcontentloaded", timeout=60_000)

            try:
                input(">>> Press ENTER here once you are logged in... ")
            except EOFError:
                print("No interactive terminal detected; waiting 120s instead.")
                page.wait_for_timeout(120_000)

            # Persist the authenticated session for importer.py.
            context.storage_state(path=str(state_path))
            print(f"\nSaved session to {state_path}")
            print("You can now run `python main.py` headlessly.")
        finally:
            browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
