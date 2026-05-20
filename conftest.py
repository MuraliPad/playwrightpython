"""
Root conftest.py — pytest fixtures shared across all test modules.

Fixture hierarchy:
    settings                 – global config singleton
    env_cfg                  – resolved UI + API URLs for current ENV
    api_session              – authenticated requests.Session (Bearer token)
    browser_type_launch_args – overrides how pytest-playwright launches browser
                               (channel, executable_path, headless handled here)
    browser_context          – Playwright BrowserContext (storage injected)
    page                     – Playwright Page (one per test)

── BROWSER CONFIGURATION ────────────────────────────────────────────
The correct place to set channel / executable_path / headless in
pytest-playwright is the `browser_type_launch_args` fixture.
pytest-playwright reads this fixture automatically when launching.

Use local installed Chrome (VDI with no internet for playwright install):
    Method A – channel (Chrome must be installed):
        pytest --env dev --browser chromium
        # set BROWSER_CHANNEL=chrome  in .env  OR
        # pytest ... (channel is read from settings.browser_channel)

    Method B – explicit exe path:
        set PLAYWRIGHT_EXECUTABLE_PATH=C:/Program Files/Google/Chrome/Application/chrome.exe
        pytest --env dev --browser chromium

    Method C – use Edge (always installed on Windows VDI):
        set PLAYWRIGHT_EXECUTABLE_PATH=C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe
        pytest --env dev --browser chromium
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Generator

# ── PROJECT ROOT ──────────────────────────────────────────────────
# Must be set BEFORE any other imports so sys.path is correct
# and dotenv can find the .env file.
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Load .env file ─────────────────────────────────────────────────
# Loads PLAYWRIGHT_EXECUTABLE_PATH, BROWSER_CHANNEL, ENV etc.
# from .env before anything else. Safe if .env does not exist.
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env", override=False)
except ImportError:
    pass  # python-dotenv not installed – use system env vars only

import pytest
import requests
from playwright.sync_api import Browser, BrowserContext, Page

from config.env_config import get_env_config, EnvConfig
from config.settings import Settings, settings as _settings


# ══════════════════════════════════════════════════════════════════
# CLI OPTIONS  (custom only – do not duplicate pytest-playwright ones)
# ══════════════════════════════════════════════════════════════════

def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Register ONLY custom CLI options.

    pytest-playwright already registers:
        --browser   chromium | firefox | webkit
        --headed    show the browser window
        --slowmo    ms delay between actions
    Adding them again causes: ArgumentError: conflicting option string
    """
    parser.addoption(
        "--env",
        default=os.getenv("ENV", "dev"),
        help="Target environment: dev | sit | uat | prod",
    )
    parser.addoption(
        "--browser-channel",
        default=os.getenv("BROWSER_CHANNEL", ""),
        help=(
            "Browser channel for using locally installed browsers. "
            "Values: chrome | msedge | chrome-beta | msedge-beta. "
            "Use when playwright install cannot run (no internet / VDI). "
            "Example: --browser-channel chrome"
        ),
    )
    parser.addoption(
        "--use-remote",
        action="store_true",
        default=False,
        help="Connect to a remote CDP / Grid endpoint",
    )
    parser.addoption(
        "--remote-url",
        default=os.getenv("REMOTE_URL", "http://localhost:4444/wd/hub"),
        help="Remote Grid URL (used with --use-remote)",
    )


# ══════════════════════════════════════════════════════════════════
# SESSION-SCOPED FIXTURES
# ══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def settings(request: pytest.FixtureRequest) -> Settings:
    """Apply CLI options onto the settings singleton."""
    s = _settings
    s.env            = request.config.getoption("--env")
    s.browser_channel = request.config.getoption("--browser-channel")
    s.use_remote     = request.config.getoption("--use-remote")
    s.remote_url     = request.config.getoption("--remote-url")
    s.screenshot_dir.mkdir(parents=True, exist_ok=True)
    return s


@pytest.fixture(scope="session")
def env_cfg(settings: Settings) -> EnvConfig:
    """Resolve BASE_URL and API_BASE_URL from ENV."""
    cfg = get_env_config(settings.env)
    print(f"\n ENV={settings.env}  UI={cfg.ui}  API={cfg.api}")
    return cfg


@pytest.fixture(scope="session")
def api_session(
    settings: Settings,
    env_cfg: EnvConfig,
) -> Generator[requests.Session, None, None]:
    """
    Authenticated requests.Session with Bearer token.

    Flow:
        user_details.json → POST /api/auth/token
        → parse access_token → Authorization: Bearer <token>
        → inject into requests.Session headers
    """
    creds_file = settings.user_details_file
    assert creds_file.exists(), (
        f"user_details.json not found at {creds_file}. "
        "Create it at config/testdata/user_details.json"
    )
    credentials = json.loads(creds_file.read_text())
    assert all(k in credentials for k in ("name", "email", "employeeID")), (
        "user_details.json must contain: name, email, employeeID"
    )

    token_url = f"{env_cfg.api}{settings.auth_token_path}"
    resp = requests.post(
        token_url,
        json=credentials,
        timeout=settings.api_timeout,
        verify=False,
    )
    assert resp.status_code == 200, (
        f"POST {token_url} → {resp.status_code}. Body: {resp.text[:300]}"
    )
    data = resp.json()
    assert "access_token" in data, f"Missing access_token. Got: {data}"
    assert data.get("token_type", "").lower() == "bearer"

    token = data["access_token"]
    assert token, "access_token is empty"
    settings.api_token = f"Bearer {token}"

    session = requests.Session()
    session.headers.update({
        "Content-Type":  "application/json",
        "Accept":        "application/json",
        "Authorization": settings.api_token,
    })
    session.verify = False
    print(f"\n Bearer token: {token[:20]}...")
    yield session
    session.close()


# ══════════════════════════════════════════════════════════════════
# BROWSER LAUNCH ARGS  ← THE CORRECT PLACE FOR channel / exe PATH
#
# pytest-playwright reads this fixture automatically before launching
# any browser. Return a dict of kwargs passed to browser_type.launch().
#
# channel values for locally installed browsers (no playwright install needed):
#   "chrome"        → uses installed Google Chrome
#   "msedge"        → uses installed Microsoft Edge
#   "chrome-beta"   → uses Chrome Beta channel
#   "msedge-beta"   → uses Edge Beta channel
#
# executable_path overrides the channel and points directly at an exe:
#   PLAYWRIGHT_EXECUTABLE_PATH env var is read automatically by
#   Playwright itself – no need to pass it here manually.
# ══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def browser_type_launch_args(
    browser_type_launch_args: Dict[str, Any],
    settings: Settings,
) -> Dict[str, Any]:
    """
    Override browser launch arguments.

    This is the correct pytest-playwright hook to pass:
        channel         – use locally installed Chrome / Edge
        executable_path – use a specific browser executable
        headless        – already handled by --headed CLI flag

    Priority:
        1. PLAYWRIGHT_EXECUTABLE_PATH env var (set in .env or system)
           → Playwright reads this automatically, nothing needed here
        2. --browser-channel CLI flag or BROWSER_CHANNEL env var
           → passed as channel= to browser_type.launch()
        3. Neither set → Playwright uses its bundled browser

    Run commands:
        # Use installed Chrome:
        pytest --env dev --browser-channel chrome -v

        # Use installed Edge:
        pytest --env dev --browser-channel msedge -v

        # Use exe path (via .env):
        # PLAYWRIGHT_EXECUTABLE_PATH=C:/Program Files/Google/Chrome/Application/chrome.exe
        pytest --env dev -v
    """
    launch_args = dict(browser_type_launch_args)  # copy existing args

    # Inject channel if set (use installed Chrome/Edge instead of bundled)
    if settings.browser_channel:
        launch_args["channel"] = settings.browser_channel
        print(f"\n Browser channel: {settings.browser_channel}")

    return launch_args


# ══════════════════════════════════════════════════════════════════
# FUNCTION-SCOPED FIXTURES  (fresh per test)
# ══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="function")
def browser_context(
    browser: Browser,
    settings: Settings,
    env_cfg: EnvConfig,
) -> Generator[BrowserContext, None, None]:
    """
    Fresh Playwright BrowserContext per test.
    Storage tokens are injected via add_init_script so SSO
    is active before the first page.goto() call.
    """
    context = browser.new_context(
        viewport={
            "width":  settings.viewport_width,
            "height": settings.viewport_height,
        },
        base_url=env_cfg.ui,
        ignore_https_errors=True,
    )
    context.set_default_timeout(settings.default_timeout)
    context.set_default_navigation_timeout(settings.page_timeout)

    _inject_sso(context, settings, env_cfg)

    yield context
    context.close()


@pytest.fixture(scope="function")
def page(browser_context: BrowserContext) -> Generator[Page, None, None]:
    """Fresh Playwright Page per test. SSO already active via context."""
    p = browser_context.new_page()
    yield p
    p.close()


# ══════════════════════════════════════════════════════════════════
# SSO INJECTION HELPERS
# ══════════════════════════════════════════════════════════════════

def _inject_sso(
    context: BrowserContext,
    settings: Settings,
    env_cfg: EnvConfig,
) -> None:
    """
    Inject SSO auth into the BrowserContext before any test navigates.

    Detection order:
        1. storage.json → inject localStorage + sessionStorage
        2. cookies.json → inject session cookies
        3. neither      → no injection (SSO button click required)
    """
    if settings.storage_file.exists():
        _inject_storage(context, settings.storage_file)
    elif settings.cookies_file.exists():
        _inject_cookies(context, settings.cookies_file, env_cfg.ui)
    else:
        print("\n No storage.json or cookies.json – SSO button click needed")


def _inject_storage(context: BrowserContext, storage_file: Path) -> None:
    """
    Inject localStorage/sessionStorage via add_init_script.
    Runs before every page load so tokens are available immediately.
    json.dumps each value so JWT tokens with dots/quotes are safe.
    """
    data    = json.loads(storage_file.read_text())
    ls_data = data.get("localStorage",   {})
    ss_data = data.get("sessionStorage", {})

    ls_lines = "\n".join(
        f"  localStorage.setItem({json.dumps(k)}, {json.dumps(v)});"
        for k, v in ls_data.items()
    )
    ss_lines = "\n".join(
        f"  sessionStorage.setItem({json.dumps(k)}, {json.dumps(v)});"
        for k, v in ss_data.items()
    )
    script = f"""
(function() {{
  try {{
{ls_lines}
{ss_lines}
  }} catch(e) {{ console.warn('SSO storage injection failed:', e); }}
}})();
"""
    context.add_init_script(script)
    print(
        f"\n Storage injection: {len(ls_data)} localStorage "
        f"+ {len(ss_data)} sessionStorage entries"
    )


def _inject_cookies(
    context: BrowserContext,
    cookies_file: Path,
    base_url: str,
) -> None:
    """Inject saved session cookies into the BrowserContext."""
    from urllib.parse import urlparse
    hostname = urlparse(base_url).hostname
    raw      = json.loads(cookies_file.read_text())
    cookies  = [c for c in raw if not c.get("name", "").startswith("_")]

    playwright_cookies = [
        {
            "name":     c["name"],
            "value":    c["value"],
            "domain":   c.get("domain", "").lstrip(".") or hostname,
            "path":     c.get("path", "/"),
            "secure":   c.get("secure",   False),
            "httpOnly": c.get("httpOnly", False),
            "url":      base_url,
        }
        for c in cookies
    ]
    if playwright_cookies:
        context.add_cookies(playwright_cookies)
        print(f"\n Cookie injection: {len(playwright_cookies)} cookies")


# ══════════════════════════════════════════════════════════════════
# ALLURE ENVIRONMENT INFO
# ══════════════════════════════════════════════════════════════════

def pytest_configure(config: pytest.Config) -> None:
    results_dir = Path("results/allure")
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "environment.properties").write_text(
        f"ENV={os.getenv('ENV', 'dev')}\n"
        f"BROWSER={os.getenv('BROWSER', 'chromium')}\n"
        f"CHANNEL={os.getenv('BROWSER_CHANNEL', '')}\n"
        f"REMOTE={os.getenv('USE_REMOTE', 'false')}\n"
    )
