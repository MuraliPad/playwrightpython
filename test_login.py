"""
Login Page Tests.

Validates the SSO landing screen before authentication.
Each test gets a fresh browser context with storage tokens injected.
"""

import allure
import pytest
from playwright.sync_api import Page, expect

from resources.pages.login_page import LoginPage


@allure.feature("Login")
@allure.story("SSO Landing Page")
class TestLogin:

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, env_cfg) -> None:
        self.login = LoginPage(page, env_cfg.ui)
        page.goto(env_cfg.ui)

    @allure.title("Login page loads without errors")
    @pytest.mark.smoke
    def test_page_loads(self) -> None:
        self.login.verify_page_loaded()

    @allure.title("App title 'MiO-X' is displayed")
    @pytest.mark.smoke
    def test_app_title(self) -> None:
        self.login.verify_app_title()

    @allure.title("App tagline is displayed")
    @pytest.mark.smoke
    def test_app_tagline(self) -> None:
        self.login.verify_tagline()

    @allure.title("SSO button is visible and enabled")
    @pytest.mark.smoke
    def test_sso_button_visible_and_enabled(self) -> None:
        self.login.verify_sso_button_enabled()

    @allure.title("SSO button has correct label")
    @pytest.mark.regression
    def test_sso_button_label(self) -> None:
        self.login.verify_sso_button_label()

    @allure.title("Browser page title contains MiO-X")
    @pytest.mark.smoke
    def test_browser_title(self, page: Page) -> None:
        expect(page).to_have_title(lambda t: "MiO-X" in t)
