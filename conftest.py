"""
Root conftest.py — pytest fixtures shared across all test modules.

Fixture hierarchy:
    settings        – global config singleton
    env_config      – resolved UI + API URLs for current ENV
    api_session     – authenticated requests.Session (Bearer token)
    browser_context – Playwright BrowserContext (storage injected)
    page            – Playwright Page (one per test)
"""

import json
import os
from pathlib import Path
from typing import Generator

import pytest
import requests
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

from config.env_config import get_env_config, EnvConfig
from config.settings import Settings, settings as _settings


# ══════════════════════════════════════════════════════════════════
# CLI OPTIONS
# ══════════════════════════════════════════════════════════════════

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--env",       default="dev",       help="Environment: dev|sit|uat|prod")
    parser.addoption("--browser-type", default="chromium", help="Browser: chromium|firefox|webkit")
    parser.addoption("--headed",    action="store_true", default=False, help="Run headed (visible browser)")
    parser.addoption("--slow-mo",   type=int, default=0, help="Slow motion ms between actions")
    parser.addoption("--use-remote",action="store_true", default=False, help="Use remote Selenium/CDP")
    parser.addoption("--remote-url",default="http://localhost:4444/wd/hub", help="Remote Grid URL")


# ══════════════════════════════════════════════════════════════════
# SESSION-SCOPED FIXTURES  (created once per test session)
# ══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def settings(request: pytest.FixtureRequest) -> Settings:
    """Apply CLI options onto the settings singleton."""
    s = _settings
    s.env        = request.config.getoption("--env")
    s.browser    = request.config.getoption("--browser-type")
    s.headless   = not request.config.getoption("--headed")
    s.slow_mo    = request.config.getoption("--slow-mo")
    s.use_remote = request.config.getoption("--use-remote")
    s.remote_url = request.config.getoption("--remote-url")
    s.screenshot_dir.mkdir(parents=True, exist_ok=True)
    return s


@pytest.fixture(scope="session")
def env_cfg(settings: Settings) -> EnvConfig:
    """Resolve BASE_URL and API_BASE_URL from ENV."""
    cfg = get_env_config(settings.env)
    print(f"\n ENV={settings.env}  UI={cfg.ui}  API={cfg.api}")
    return cfg


@pytest.fixture(scope="session")
def api_session(settings: Settings, env_cfg: EnvConfig) -> Generator[requests.Session, None, None]:
    """
    Authenticated requests.Session.

    Reads user_details.json → POST /api/auth/token → Bearer token
    → injects Authorization header into session for all API calls.
    """
    # Load credentials from JSON file
    creds_file = settings.user_details_file
    assert creds_file.exists(), (
        f"user_details.json not found at {creds_file}. "
        "Create it at config/testdata/user_details.json"
    )
    credentials = json.loads(creds_file.read_text())
    assert all(k in credentials for k in ("name", "email", "employeeID")), (
        "user_details.json must contain: name, email, employeeID"
    )

    # Fetch Bearer token
    token_url = f"{env_cfg.api}{settings.auth_token_path}"
    resp = requests.post(
        token_url,
        json=credentials,
        timeout=settings.api_timeout,
        verify=False,
    )
    assert resp.status_code == 200, (
        f"POST {token_url} returned {resp.status_code}. Body: {resp.text[:300]}"
    )
    token_data = resp.json()
    assert "access_token" in token_data, (
        f"Auth response missing 'access_token'. Got: {token_data}"
    )
    assert token_data.get("token_type", "").lower() == "bearer", (
        f"Expected token_type 'bearer', got '{token_data.get('token_type')}'"
    )

    access_token = token_data["access_token"]
    assert access_token, "access_token is empty in auth response"

    # Store on settings so other fixtures can read it
    settings.api_token = f"Bearer {access_token}"

    # Build session
    session = requests.Session()
    session.headers.update({
        "Content-Type":  "application/json",
        "Accept":        "application/json",
        "Authorization": settings.api_token,
    })
    session.verify = False

    print(f"\n Bearer token obtained: {access_token[:20]}...")
    yield session
    session.close()


# ══════════════════════════════════════════════════════════════════
# FUNCTION-SCOPED FIXTURES  (created fresh per test)
# ══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="function")
def browser_context(
    settings: Settings,
    env_cfg: EnvConfig,
) -> Generator[BrowserContext, None, None]:
    """
    Fresh Playwright BrowserContext per test.
    Injects localStorage/sessionStorage tokens from storage.json
    so SSO is active when the page first loads.
    """
    with sync_playwright() as pw:
        browser = _launch_browser(pw, settings)
        context = browser.new_context(
            viewport={"width": settings.viewport_width, "height": settings.viewport_height},
            base_url=env_cfg.ui,
            ignore_https_errors=True,
        )
        context.set_default_timeout(settings.default_timeout)
        context.set_default_navigation_timeout(settings.page_timeout)

        # Inject SSO tokens before any page opens
        _inject_sso(context, settings, env_cfg)

        yield context

        context.close()
        browser.close()


@pytest.fixture(scope="function")
def page(browser_context: BrowserContext) -> Generator[Page, None, None]:
    """
    Fresh Playwright Page per test.
    The browser context already has SSO tokens injected.
    """
    p = browser_context.new_page()
    yield p
    p.close()


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def _launch_browser(pw: Playwright, settings: Settings) -> Browser:
    """Launch local or remote browser based on settings."""
    browser_type = getattr(pw, settings.browser)   # pw.chromium / pw.firefox / pw.webkit

    launch_args = dict(
        headless = settings.headless,
        slow_mo  = settings.slow_mo,
    )

    if settings.use_remote:
        # Connect to a remote Selenium Grid or CDP endpoint
        # For Playwright remote use CDP URL: ws://<host>:4444/...
        return browser_type.connect_over_cdp(settings.remote_url)

    return browser_type.launch(**launch_args)


def _inject_sso(
    context: BrowserContext,
    settings: Settings,
    env_cfg: EnvConfig,
) -> None:
    """
    Inject SSO auth into the browser context before any test navigates.

    Detection order:
        1. storage.json → inject localStorage + sessionStorage
        2. cookies.json → inject session cookies
        3. neither      → no injection (SSO button click needed)

    Both strategies work for local and remote browsers because
    Playwright's add_cookies() and add_init_script() communicate
    via the CDP protocol to wherever the browser actually runs.
    """
    if settings.storage_file.exists():
        _inject_storage(context, settings.storage_file, env_cfg.ui)
    elif settings.cookies_file.exists():
        _inject_cookies(context, settings.cookies_file, env_cfg.ui)
    else:
        print("\n No storage.json or cookies.json found – SSO button click required.")


def _inject_storage(
    context: BrowserContext,
    storage_file: Path,
    base_url: str,
) -> None:
    """
    Inject localStorage and sessionStorage via an init script.

    add_init_script runs before every page load so tokens are
    available the moment the app's JavaScript executes.
    JSON dumps each value so JWT tokens with dots/quotes are safe.
    """
    data = json.loads(storage_file.read_text())
    ls_data = data.get("localStorage", {})
    ss_data = data.get("sessionStorage", {})

    # Build a JS snippet that sets each key safely
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
        f"\n Storage injection: {len(ls_data)} localStorage + "
        f"{len(ss_data)} sessionStorage entries"
    )


def _inject_cookies(
    context: BrowserContext,
    cookies_file: Path,
    base_url: str,
) -> None:
    """Inject saved session cookies into the browser context."""
    from urllib.parse import urlparse
    hostname = urlparse(base_url).hostname

    raw = json.loads(cookies_file.read_text())
    cookies = [c for c in raw if not c.get("name", "").startswith("_")]

    playwright_cookies = []
    for c in cookies:
        domain = c.get("domain", "").lstrip(".") or hostname
        playwright_cookies.append({
            "name":     c["name"],
            "value":    c["value"],
            "domain":   domain,
            "path":     c.get("path", "/"),
            "secure":   c.get("secure", False),
            "httpOnly": c.get("httpOnly", False),
            "url":      base_url,
        })

    if playwright_cookies:
        context.add_cookies(playwright_cookies)
        print(f"\n Cookie injection: {len(playwright_cookies)} cookies")


# ══════════════════════════════════════════════════════════════════
# ALLURE ENVIRONMENT INFO
# ══════════════════════════════════════════════════════════════════

def pytest_configure(config: pytest.Config) -> None:
    """Write environment info to Allure results folder."""
    results_dir = Path("results/allure")
    results_dir.mkdir(parents=True, exist_ok=True)
    env_props = results_dir / "environment.properties"
    env_props.write_text(
        f"ENV={os.getenv('ENV', 'dev')}\n"
        f"BROWSER={os.getenv('BROWSER', 'chromium')}\n"
        f"REMOTE={os.getenv('USE_REMOTE', 'false')}\n"
    )
