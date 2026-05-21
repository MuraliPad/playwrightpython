"""
Global test settings.

All configuration in one place. Override via pytest CLI options
defined in conftest.py or via environment variables.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

# Project root = parent of this file's directory
PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class Settings:
    # ── Environment ───────────────────────────────────────────────
    env:              str  = field(default_factory=lambda: os.getenv("ENV", "dev"))

    # ── Browser ───────────────────────────────────────────────────
    browser:          str  = field(default_factory=lambda: os.getenv("BROWSER", "chromium"))
    headless:         bool = field(default_factory=lambda: os.getenv("HEADLESS", "false").lower() == "true")
    slow_mo:          int  = 0       # ms between actions, useful for debugging

    # ── SSO injection ─────────────────────────────────────────────────────────────
    # Controls whether localStorage/cookie tokens are injected into the browser.
    #   True  → inject (remote browser, Jenkins, fresh session)
    #   False → skip   (local Chrome/Edge with existing SSO session)
    # Set via INJECT_SSO in .env or environment variable.
    inject_sso:       bool = field(default_factory=lambda: os.getenv("INJECT_SSO", "true").lower() == "true")

    # Channel for using locally installed browser (VDI / no internet).
    # Values: chrome | msedge | chrome-beta | msedge-beta | "" (empty = bundled)
    # Set via --browser-channel CLI flag or BROWSER_CHANNEL in .env
    browser_channel:  str  = field(default_factory=lambda: os.getenv("BROWSER_CHANNEL", ""))

    # ── Remote (Playwright CDP / Selenium Grid) ──────────────────────────────────
    # use_remote=True → connect_over_cdp(remote_url) instead of local launch
    # Set USE_REMOTE=true in .env or pass --use-remote on CLI
    use_remote:       bool = field(default_factory=lambda: os.getenv("USE_REMOTE", "false").lower() == "true")
    # remote_url must be a WebSocket URL for Playwright CDP:
    #   Selenium Grid 4:  ws://<host>:4444/
    #   Direct CDP:       ws://<host>:9222/
    # Note: http:// URLs are NOT supported by connect_over_cdp()
    remote_url:       str  = field(default_factory=lambda: os.getenv("REMOTE_URL", "ws://localhost:4444/"))

    # ── Timeouts (milliseconds for Playwright) ────────────────────
    default_timeout:  int  = 15_000   # 15s  – element wait timeout
    page_timeout:     int  = 30_000   # 30s  – navigation timeout
    api_timeout:      int  = 30       # 30s  – requests library (seconds)

    # ── Viewport ──────────────────────────────────────────────────
    viewport_width:   int  = 1920
    viewport_height:  int  = 1080

    # ── Auth ──────────────────────────────────────────────────────
    auth_token_path:  str  = "/api/auth/token"
    api_token:        str  = ""   # populated at runtime by auth flow

    # ── Storage injection files ───────────────────────────────────
    storage_file:     Path = PROJECT_ROOT / "config" / "testdata" / "storage.json"
    cookies_file:     Path = PROJECT_ROOT / "config" / "testdata" / "cookies.json"
    user_details_file:Path = PROJECT_ROOT / "config" / "testdata" / "user_details.json"

    # ── Screenshots ───────────────────────────────────────────────
    screenshot_dir:   Path = PROJECT_ROOT / "results" / "screenshots"

    # ── Integrity ─────────────────────────────────────────────────
    count_tolerance:  int  = 0


# Singleton – imported by conftest and all fixtures
settings = Settings()
