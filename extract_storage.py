"""
Extract localStorage / sessionStorage tokens after SSO login.

This is a standalone Python script — run with `python`, NOT `pytest`.

Usage:
    python scripts/extract_storage.py
    python scripts/extract_storage.py --env uat
    python scripts/extract_storage.py --env dev --channel chrome

What it does:
    1. Opens a headed browser (must be visible for SSO)
    2. Navigates to the app URL
    3. Clicks Sign In using SSO
    4. Waits for you to complete corporate login
    5. Extracts all localStorage + sessionStorage tokens
    6. Saves to config/testdata/storage.json

Re-run when tokens expire (typically 8-24 hours).

Browser used:
    Reads BROWSER_CHANNEL from .env automatically.
    Pass --channel chrome or --channel msedge to override.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ── Project root on sys.path ──────────────────────────────────────
# Must be first so config/ imports work when running as a script.
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Load .env ─────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    print("✔ .env loaded")
except ImportError:
    print("⚠ python-dotenv not installed. Install: pip install python-dotenv")

from playwright.sync_api import sync_playwright
from config.env_config import get_env_config

STORAGE_FILE = PROJECT_ROOT / "config" / "testdata" / "storage.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract SSO localStorage/sessionStorage tokens",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/extract_storage.py
  python scripts/extract_storage.py --env uat
  python scripts/extract_storage.py --channel chrome
  python scripts/extract_storage.py --env dev --channel msedge
        """
    )
    parser.add_argument(
        "--env",
        default=os.getenv("ENV", "dev"),
        help="Environment: dev | sit | uat | prod  (default: dev)",
    )
    parser.add_argument(
        "--channel",
        default=os.getenv("BROWSER_CHANNEL", ""),
        help=(
            "Browser channel: chrome | msedge. "
            "Leave empty to use Playwright bundled browser. "
            "Reads BROWSER_CHANNEL from .env if not passed."
        ),
    )
    args = parser.parse_args()

    # ── Resolve URL ───────────────────────────────────────────────
    env_cfg  = get_env_config(args.env)
    base_url = env_cfg.ui
    print(f"\n ENV     : {args.env}")
    print(f" URL     : {base_url}")
    print(f" Channel : {args.channel or 'playwright bundled'}")
    print(f" Output  : {STORAGE_FILE}\n")

    # ── Launch browser ────────────────────────────────────────────
    with sync_playwright() as pw:

        # Always headed – SSO requires a visible browser
        launch_args = {"headless": False}
        if args.channel:
            launch_args["channel"] = args.channel

        print(f" Launching browser (channel={args.channel or 'bundled'}, headless=False)...")
        browser = pw.chromium.launch(**launch_args)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )
        page = context.new_page()

        # ── Navigate and click SSO ────────────────────────────────
        print(f" Navigating to {base_url} ...")
        page.goto(base_url, timeout=30_000)

        sso_locator = page.locator(
            "button:has-text('Sign In using SSO'), "
            "a:has-text('Sign In using SSO')"
        ).first

        print(" Waiting for SSO button...")
        sso_locator.wait_for(state="visible", timeout=20_000)
        sso_locator.click()
        print(" SSO button clicked. Complete your corporate login in the browser window...")
        print(" (waiting up to 120 seconds for you to finish logging in)")

        # ── Wait for app to fully load after SSO ─────────────────
        # Wait for the sidebar which confirms the app shell is rendered
        page.wait_for_selector(
            ".sidebar, .side-nav, [class*='sidebar'], [class*='side-nav']",
            state="visible",
            timeout=120_000,
        )
        print(" ✔ SSO login complete. App shell visible.\n")

        # ── Show available keys ───────────────────────────────────
        ls_keys = page.evaluate("Object.keys(localStorage)")
        ss_keys = page.evaluate("Object.keys(sessionStorage)")
        print(f" localStorage keys   ({len(ls_keys)}): {ls_keys}")
        print(f" sessionStorage keys ({len(ss_keys)}): {ss_keys}\n")

        if not ls_keys and not ss_keys:
            print(" ⚠ WARNING: Both localStorage and sessionStorage are empty.")
            print("   The app may store auth in cookies instead.")
            print("   Check Application tab in DevTools to confirm.")
            browser.close()
            return

        # ── Extract all values ────────────────────────────────────
        ls_data: dict = {}
        for key in ls_keys:
            val = page.evaluate(f"localStorage.getItem({json.dumps(key)})")
            ls_data[key] = val or ""

        ss_data: dict = {}
        for key in ss_keys:
            val = page.evaluate(f"sessionStorage.getItem({json.dumps(key)})")
            ss_data[key] = val or ""

        # ── Write storage.json ────────────────────────────────────
        STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STORAGE_FILE.write_text(
            json.dumps(
                {"localStorage": ls_data, "sessionStorage": ss_data},
                indent=2,
            ),
            encoding="utf-8",
        )

        print(f" ✔ Saved {len(ls_data)} localStorage "
              f"+ {len(ss_data)} sessionStorage entries")
        print(f" ✔ File : {STORAGE_FILE}")
        print("\n Next steps:")
        print("   1. Set INJECT_SSO=true  in .env  (for remote/headless runs)")
        print("   2. Set INJECT_SSO=false in .env  (for local Chrome runs)")
        print("   3. Re-run this script when SSO session expires (8-24 hours)")

        browser.close()


if __name__ == "__main__":
    main()
