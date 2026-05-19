"""
Page Object: MiO-X Login / SSO Landing Page.

DOM confirmed Apr 2026:
    <h2 class="...">MiO-X</h2>
    <p>The Autonomous Migration Engine</p>
    <button>Sign In using SSO</button>
"""

from playwright.sync_api import Page, expect
from resources.base.base_page import BasePage


class LoginPage(BasePage):

    def __init__(self, page: Page, base_url: str) -> None:
        super().__init__(page, base_url)
        # ── Locators ──────────────────────────────────────────────
        self.app_title   = page.locator("text=MiO-X").first
        self.app_tagline = page.locator("text=The Autonomous Migration Engine")
        self.sso_button  = page.locator(
            "button:has-text('Sign In using SSO'), "
            "a:has-text('Sign In using SSO')"
        )

    # ── Contract ──────────────────────────────────────────────────

    def verify_page_loaded(self) -> None:
        """Confirm the SSO login page is rendered."""
        self.app_title.wait_for(state="visible", timeout=15_000)
        self.sso_button.wait_for(state="visible", timeout=15_000)

    # ── Verifications ─────────────────────────────────────────────

    def verify_app_title(self) -> None:
        self.assert_contains_text(self.app_title, "MiO-X")

    def verify_tagline(self) -> None:
        self.assert_contains_text(self.app_tagline, "The Autonomous Migration Engine")

    def verify_sso_button_enabled(self) -> None:
        expect(self.sso_button).to_be_enabled()

    def verify_sso_button_label(self) -> None:
        expect(self.sso_button).to_contain_text("Sign In using SSO")

    # ── Actions ───────────────────────────────────────────────────

    def click_sso_button(self) -> None:
        """Click SSO button and wait for navigation to complete."""
        self.sso_button.click()
        self.wait_for_page_ready()
