"""
Base page object.

Every page class inherits from BasePage.
Provides shared navigation, waiting, screenshot, and assertion helpers.
Page-specific locators and keywords live in the subclass.
"""

from pathlib import Path
from playwright.sync_api import Page, Locator, expect
import allure
import time


class BasePage:
    """Abstract base – override `verify_page_loaded` in every subclass."""

    def __init__(self, page: Page, base_url: str) -> None:
        self.page     = page
        self.base_url = base_url

    # ── Contract ──────────────────────────────────────────────────

    def verify_page_loaded(self) -> None:
        """
        MUST be overridden by every subclass.
        Should assert the page-specific heading/title is visible.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement verify_page_loaded()"
        )

    # ── Navigation ────────────────────────────────────────────────

    def navigate(self, path: str = "") -> None:
        """Navigate to base_url + path and wait for load."""
        self.page.goto(f"{self.base_url}{path}")
        self.wait_for_page_ready()

    def wait_for_page_ready(self) -> None:
        """Wait until document.readyState == 'complete'."""
        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_load_state("networkidle")

    # ── Element helpers ───────────────────────────────────────────

    def wait_and_click(self, locator: Locator) -> None:
        locator.wait_for(state="visible")
        locator.click()

    def wait_and_fill(self, locator: Locator, text: str) -> None:
        locator.wait_for(state="visible")
        locator.fill(text)

    def get_text(self, locator: Locator) -> str:
        locator.wait_for(state="visible")
        return locator.inner_text().strip()

    # ── Assertions ────────────────────────────────────────────────

    def assert_visible(self, locator: Locator, message: str = "") -> None:
        expect(locator).to_be_visible(timeout=15_000)

    def assert_text(self, locator: Locator, expected: str) -> None:
        expect(locator).to_have_text(expected, timeout=15_000)

    def assert_contains_text(self, locator: Locator, text: str) -> None:
        expect(locator).to_contain_text(text, timeout=15_000)

    def assert_url_contains(self, fragment: str) -> None:
        expect(self.page).to_have_url(f".*{fragment}.*", timeout=15_000)

    # ── Screenshot ────────────────────────────────────────────────

    def take_screenshot(self, name: str) -> None:
        """Take a screenshot and attach it to the Allure report."""
        ts = int(time.time())
        path = Path("results/screenshots") / f"{name}_{ts}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(path))
        allure.attach(
            path.read_bytes(),
            name=name,
            attachment_type=allure.attachment_type.PNG,
        )
