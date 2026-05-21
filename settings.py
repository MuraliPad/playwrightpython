"""
Global test settings — single source of truth for all configuration.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  OVERRIDE CHAIN  (later entries win over earlier ones)

  settings.py defaults
      ↓
  .env file           (user-specific, never committed to git)
      ↓
  system env vars     (CI/Jenkins pipeline variables)
      ↓
  CLI flags           (--env, --use-remote, --remote-url)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each setting is defined ONCE here.
  - settings.py  reads  os.getenv("KEY", default)
  - .env         sets   KEY=value         (overrides default)
  - conftest.py  reads  getoption("--key") and writes back to settings
  - run_tests.bat passes --key value      (overrides .env)
  - code         reads  settings.key      (always)

Nobody else hardcodes URLs or credentials.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class Settings:

    # ── Environment ───────────────────────────────────────────────
    # Which deployment to test against.
    # Resolved to actual URLs by config/env_config.py at runtime.
    env: str = field(
        default_factory=lambda: os.getenv("ENV", "dev")
    )

    # ── Browser ───────────────────────────────────────────────────
    # Browser engine. Values: chromium | firefox | webkit
    browser: str = field(
        default_factory=lambda: os.getenv("BROWSER", "chromium")
    )
    # Channel uses your locally installed browser instead of Playwright bundled.
    # Values: chrome | msedge | "" (empty = use bundled Playwright browser)
    browser_channel: str = field(
        default_factory=lambda: os.getenv("BROWSER_CHANNEL", "")
    )

    # ── Remote execution ──────────────────────────────────────────
    # When True, connects to a remote Grid/CDP instead of local launch.
    # REMOTE_URL must be a WebSocket URL:
    #   Selenium Grid 4 : ws://<host>:4444/
    #   Direct Chrome CDP: ws://<host>:9222/
    use_remote: bool = field(
        default_factory=lambda: os.getenv("USE_REMOTE", "false").lower() == "true"
    )
    remote_url: str = field(
        default_factory=lambda: os.getenv("REMOTE_URL", "ws://localhost:4444/")
    )

    # ── SSO injection ─────────────────────────────────────────────
    # True  → inject storage.json/cookies.json tokens into browser
    #         Use for: remote Grid, Jenkins, headless, any fresh browser
    # False → skip injection, browser already has SSO session active
    #         Use for: local Chrome with BROWSER_CHANNEL=chrome
    inject_sso: bool = field(
        default_factory=lambda: os.getenv("INJECT_SSO", "true").lower() == "true"
    )

    # ── Timeouts ──────────────────────────────────────────────────
    default_timeout: int  = 15_000   # ms – Playwright element wait
    page_timeout:    int  = 30_000   # ms – Playwright navigation
    api_timeout:     int  = 30       # s  – requests HTTP timeout

    # ── Viewport ──────────────────────────────────────────────────
    viewport_width:  int  = 1920
    viewport_height: int  = 1080

    # ── API auth ──────────────────────────────────────────────────
    auth_token_path: str  = "/api/auth/token"
    api_token:       str  = ""   # set at runtime by api_session fixture

    # ── File paths ────────────────────────────────────────────────
    # All resolved relative to project root — never hardcode absolute paths.
    storage_file:      Path = PROJECT_ROOT / "config" / "testdata" / "storage.json"
    cookies_file:      Path = PROJECT_ROOT / "config" / "testdata" / "cookies.json"
    user_details_file: Path = PROJECT_ROOT / "config" / "testdata" / "user_details.json"
    screenshot_dir:    Path = PROJECT_ROOT / "results" / "screenshots"

    # ── Integrity ─────────────────────────────────────────────────
    count_tolerance: int = 0


# Singleton imported by conftest.py and all fixtures.
# conftest.py writes CLI option values back into this object
# so every fixture always reads from one place: settings.<attr>
settings = Settings()
