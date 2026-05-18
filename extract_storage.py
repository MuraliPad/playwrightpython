"""
Extract localStorage / sessionStorage after SSO login.

Run ONCE on your VDI after manually logging in via SSO.
Saves all tokens to config/testdata/storage.json.
Re-run when tokens expire (typically 8-24 hours).

Usage:
    python scripts/extract_storage.py
    python scripts/extract_storage.py --env uat --headed
"""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).parent.parent
STORAGE_FILE = PROJECT_ROOT / "config" / "testdata" / "storage.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract SSO storage tokens")
    parser.add_argument("--env",     default="dev", help="Environment: dev|sit|uat|prod")
    parser.add_argument("--headed",  action="store_true", default=True,
                        help="Show browser (default: True – needed for SSO)")
    args = parser.parse_args()

    # Load env URL
    from config.env_config import get_env_config
    env_cfg = get_env_config(args.env)
    base_url = env_cfg.ui
    print(f"\n Opening {base_url} ...")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)  # must be headed for SSO
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.goto(base_url)

        # Wait for SSO button and click it
        sso = page.locator(
            "button:has-text('Sign In using SSO'), "
            "a:has-text('Sign In using SSO')"
        ).first
        sso.wait_for(state="visible", timeout=15_000)
        sso.click()

        # Wait for full SSO login – sidebar confirms app loaded
        print(" Waiting for SSO login... (complete corporate login in the browser)")
        page.locator(
            ".sidebar, .side-nav, [class*='sidebar']"
        ).first.wait_for(state="visible", timeout=120_000)
        print(" ✔ SSO login complete. Extracting storage...")

        # Show available keys
        ls_keys = page.evaluate("Object.keys(localStorage)")
        ss_keys = page.evaluate("Object.keys(sessionStorage)")
        print(f" localStorage keys:   {ls_keys}")
        print(f" sessionStorage keys: {ss_keys}")

        # Collect all entries
        ls_data: dict = {}
        for key in ls_keys:
            safe_key = json.dumps(key)
            val = page.evaluate(f"localStorage.getItem({safe_key})")
            ls_data[key] = val or ""

        ss_data: dict = {}
        for key in ss_keys:
            safe_key = json.dumps(key)
            val = page.evaluate(f"sessionStorage.getItem({safe_key})")
            ss_data[key] = val or ""

        # Write to file
        STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STORAGE_FILE.write_text(
            json.dumps({"localStorage": ls_data, "sessionStorage": ss_data}, indent=2)
        )

        ls_count = len(ls_data)
        ss_count = len(ss_data)
        print(f"\n ✔ Saved {ls_count} localStorage + {ss_count} sessionStorage entries")
        print(f"   File: {STORAGE_FILE}")
        print("   Re-run when SSO session expires (typically 8-24 hours)")

        browser.close()


if __name__ == "__main__":
    main()
