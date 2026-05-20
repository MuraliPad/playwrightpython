"""
Root conftest.py — pytest fixtures shared across all test modules.

── BROWSER CHANNEL (for VDI / no internet) ──────────────────────────
To use your locally installed Chrome or Edge instead of Playwright's
bundled browser, set BROWSER_CHANNEL in your .env file:

    BROWSER_CHANNEL=chrome       uses installed Google Chrome
    BROWSER_CHANNEL=msedge       uses installed Microsoft Edge

Do NOT pass --browser-channel on the CLI. pytest-playwright already
owns that flag and re-registering it causes:
    ArgumentError: conflicting option string: --browser-channel

── CUSTOM CLI OPTIONS (safe to add) ─────────────────────────────────
    --env           dev | sit | uat | prod
    --use-remote    connect to remote Grid
    --remote-url    Grid endpoint URL

── pytest-playwright BUILT-IN OPTIONS (do not re-register) ──────────
    --browser       chromium | firefox | webkit
    --headed        show browser window
    --slowmo        ms delay between actions
    --browser-channel  already registered by pytest-playwright
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Generator

# ── PROJECT ROOT ──────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Load .env ─────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env", override=False)
except ImportError:
    pass

import allure
import pytest
import requests
from playwright.sync_api import Browser, BrowserContext, Page

from config.env_config import get_env_config, EnvConfig
from config.settings import Settings, settings as _settings


# ══════════════════════════════════════════════════════════════════
# CUSTOM CLI OPTIONS  ← only --env, --use-remote, --remote-url
# ══════════════════════════════════════════════════════════════════

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--env",
        default=os.getenv("ENV", "dev"),
        help="Target environment: dev | sit | uat | prod",
    )
    parser.addoption(
        "--use-remote",
        action="store_true",
        default=False,
        help="Connect to a remote CDP / Selenium Grid endpoint",
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
    """Apply CLI options and env vars onto the settings singleton."""
    s = _settings
    s.env             = request.config.getoption("--env")
    s.use_remote      = request.config.getoption("--use-remote")
    s.remote_url      = request.config.getoption("--remote-url")
    # browser_channel read from .env / environment variable ONLY
    # not from CLI to avoid conflict with pytest-playwright's own flag
    s.browser_channel = os.getenv("BROWSER_CHANNEL", "")
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
    Reads user_details.json → POST /api/auth/token → Bearer token.
    """
    creds_file = settings.user_details_file
    assert creds_file.exists(), (
        f"user_details.json not found at {creds_file}. "
        "Create it at config/testdata/user_details.json"
    )
    credentials = json.loads(creds_file.read_text())
    for key in ("name", "email", "employeeID"):
        assert key in credentials and credentials[key], \
            f"user_details.json missing or empty field: '{key}'"

    token_url = f"{env_cfg.api}{settings.auth_token_path}"
    resp = requests.post(
        token_url,
        json=credentials,
        timeout=settings.api_timeout,
        verify=False,
    )
    assert resp.status_code == 200, \
        f"POST {token_url} → {resp.status_code}. Body: {resp.text[:300]}"

    data = resp.json()
    assert "access_token" in data,                    f"Missing access_token. Got: {data}"
    assert data.get("token_type","").lower()=="bearer", f"Expected bearer, got: {data.get('token_type')}"
    assert data["access_token"],                       "access_token is empty"

    settings.api_token = f"Bearer {data['access_token']}"
    session = requests.Session()
    session.headers.update({
        "Content-Type":  "application/json",
        "Accept":        "application/json",
        "Authorization": settings.api_token,
    })
    session.verify = False
    print(f"\n Bearer token: {data['access_token'][:20]}...")
    yield session
    session.close()


# ══════════════════════════════════════════════════════════════════
# BROWSER LAUNCH ARGS
#
# pytest-playwright reads `browser_type_launch_args` automatically.
# This is the correct place to inject channel= so locally installed
# Chrome or Edge is used instead of Playwright's bundled browser.
#
# Set BROWSER_CHANNEL in .env (NOT as a CLI flag):
#   BROWSER_CHANNEL=chrome    → uses installed Google Chrome
#   BROWSER_CHANNEL=msedge    → uses installed Microsoft Edge
# ══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def browser_type_launch_args(
    browser_type_launch_args: Dict[str, Any],
    settings: Settings,
) -> Dict[str, Any]:
    """
    Inject browser launch args.
    pytest-playwright passes whatever this returns to browser_type.launch().

    Headless mode:
        Default  → headless  (no flag needed)
        --headed → headed    (shows browser window)
        HEADLESS=false in .env → headed permanently

    Channel (VDI / no internet):
        BROWSER_CHANNEL=chrome  in .env → uses installed Chrome
        BROWSER_CHANNEL=msedge  in .env → uses installed Edge
    """
    launch_args = dict(browser_type_launch_args)

    # ── Headless ──────────────────────────────────────────────────
    # pytest-playwright defaults to headless=True.
    # --headed CLI flag sets headless=False automatically.
    # HEADLESS=false in .env also sets headed mode permanently.
    headless_env = os.getenv("HEADLESS", "true").lower()
    if headless_env == "false":
        launch_args["headless"] = False

    # ── Channel (locally installed Chrome / Edge) ─────────────────
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
    Fresh Playwright BrowserContext per test with SSO tokens injected.
    Uses pytest-playwright's `browser` fixture so --headed / --browser
    / --slowmo CLI flags all work correctly.
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
    """Fresh Playwright Page. SSO already active via browser_context."""
    p = browser_context.new_page()
    yield p
    p.close()


# ══════════════════════════════════════════════════════════════════
# SSO INJECTION
# ══════════════════════════════════════════════════════════════════

def _inject_sso(
    context: BrowserContext,
    settings: Settings,
    env_cfg: EnvConfig,
) -> None:
    """
    Inject SSO tokens into the browser context.

    Controlled by INJECT_SSO in .env or environment variable:
        INJECT_SSO=true  → inject localStorage/cookies (remote browser, Jenkins)
        INJECT_SSO=false → skip injection (local Chrome with existing session)

    Local run with BROWSER_CHANNEL=chrome:
        Your Chrome already has the SSO session active – no injection needed.
        Set INJECT_SSO=false in .env.

    Remote / Jenkins run:
        Browser is fresh with no session – injection required.
        Set INJECT_SSO=true in .env.
    """
    if not settings.inject_sso:
        print("\n SSO injection skipped (INJECT_SSO=false) – using existing browser session")
        return

    if settings.storage_file.exists():
        _inject_storage(context, settings.storage_file)
    elif settings.cookies_file.exists():
        _inject_cookies(context, settings.cookies_file, env_cfg.ui)
    else:
        print("\n No storage.json or cookies.json found – SSO button click needed")


def _inject_storage(context: BrowserContext, storage_file: Path) -> None:
    """Inject localStorage/sessionStorage via add_init_script (runs before every page load)."""
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
    context.add_init_script(f"""
(function() {{
  try {{
{ls_lines}
{ss_lines}
  }} catch(e) {{ console.warn('SSO injection failed:', e); }}
}})();
""")
    print(f"\n Storage injection: {len(ls_data)} localStorage + {len(ss_data)} sessionStorage")


def _inject_cookies(
    context: BrowserContext,
    cookies_file: Path,
    base_url: str,
) -> None:
    """Inject saved session cookies into the BrowserContext."""
    from urllib.parse import urlparse
    hostname = urlparse(base_url).hostname
    raw      = json.loads(cookies_file.read_text())
    cookies  = [
        {
            "name":     c["name"],
            "value":    c["value"],
            "domain":   c.get("domain", "").lstrip(".") or hostname,
            "path":     c.get("path", "/"),
            "secure":   c.get("secure",   False),
            "httpOnly": c.get("httpOnly", False),
            "url":      base_url,
        }
        for c in raw
        if not c.get("name", "").startswith("_")
    ]
    if cookies:
        context.add_cookies(cookies)
        print(f"\n Cookie injection: {len(cookies)} cookies")


# ══════════════════════════════════════════════════════════════════
# ALLURE ENVIRONMENT
# ══════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════
# REPORTING HOOKS
# ══════════════════════════════════════════════════════════════════

def pytest_configure(config: pytest.Config) -> None:
    """
    Called once at startup.
    Creates results directories and writes Allure environment info.
    """
    # Create all report directories up front
    for d in ("results/allure", "results/screenshots", "results/allure-report"):
        Path(d).mkdir(parents=True, exist_ok=True)

    # Allure environment.properties – shown on the Allure Overview page
    allure_dir = Path("results/allure")
    allure_dir.mkdir(parents=True, exist_ok=True)
    (allure_dir / "environment.properties").write_text(
        f"ENV={os.getenv('ENV', 'dev')}\n"
        f"URL={os.getenv('BASE_URL', '')}\n"
        f"BROWSER={os.getenv('BROWSER', 'chromium')}\n"
        f"CHANNEL={os.getenv('BROWSER_CHANNEL', '')}\n"
        f"HEADLESS={os.getenv('HEADLESS', 'true')}\n"
        f"INJECT_SSO={os.getenv('INJECT_SSO', 'true')}\n",
        encoding="utf-8",
    )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    """
    Called after each test phase (setup / call / teardown).

    On FAILURE:
        - captures a screenshot from the Playwright page fixture
        - attaches it to the Allure report
        - attaches it to the pytest-html report
        - saves it to results/screenshots/

    Works automatically for any test that uses the `page` fixture.
    """
    outcome = yield
    report  = outcome.get_result()

    # Only act on the actual test call phase, not setup/teardown
    if report.when != "call":
        return

    # Try to get the Playwright page from the test's fixtures
    page = item.funcargs.get("page")
    if page is None:
        return  # API-only test, no browser

    if report.failed:
        # ── Build a safe filename from the test name ──────────────
        safe_name = re.sub(r"[^\w\-]", "_", item.nodeid.replace("/", "_").replace("\\", "_"))
        screenshot_path = Path("results/screenshots") / f"FAILED_{safe_name}.png"

        try:
            # Take screenshot
            page.screenshot(path=str(screenshot_path), full_page=True)

            # ── Attach to Allure ──────────────────────────────────
            allure.attach(
                screenshot_path.read_bytes(),
                name=f"FAILED – {item.name}",
                attachment_type=allure.attachment_type.PNG,
            )

            # ── Attach to pytest-html ─────────────────────────────
            # pytest-html reads extras from report.extras
            try:
                from pytest_html import extras as html_extras
                if not hasattr(report, "extras"):
                    report.extras = []
                report.extras.append(
                    html_extras.image(str(screenshot_path))
                )
            except ImportError:
                pass  # pytest-html not installed

            print(f"\n Screenshot saved: {screenshot_path}")

        except Exception as e:
            print(f"\n Could not capture screenshot: {e}")

    elif report.passed:
        # Optionally attach screenshot on pass too (comment out if not needed)
        pass
