"""
Navigation / Sidebar Tests.

Validates the left-hand navigation after SSO login.
Storage injection in browser_context fixture means the app shell
loads directly without any SSO prompt.
"""

import allure
import pytest
from playwright.sync_api import Page, expect

from resources.components.sidebar_nav import SidebarNav


@allure.feature("Navigation")
@allure.story("Sidebar")
class TestNavigation:

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, env_cfg) -> None:
        self.nav = SidebarNav(page)
        page.goto(env_cfg.ui)
        # Wait for sidebar to confirm app shell is loaded
        self.nav.sidebar.wait_for(state="visible", timeout=30_000)

    @allure.title("App shell renders after SSO login")
    @pytest.mark.smoke
    def test_app_shell_renders(self) -> None:
        expect(self.nav.sidebar).to_be_visible()

    @allure.title("Sidebar shows MiO-X brand title")
    @pytest.mark.smoke
    def test_brand_title(self) -> None:
        self.nav.verify_brand()

    @allure.title("All 10 navigation items are present")
    @pytest.mark.smoke
    def test_all_nav_items_present(self) -> None:
        self.nav.verify_all_nav_items()

    @allure.title("Inventory nav item is present")
    @pytest.mark.smoke
    @pytest.mark.parametrize("item", ["Inventory", "Capacity", "Optimization",
                                       "Planning", "Migration", "Cluster",
                                       "Reports", "Management",
                                       "Migration Genie", "ITSO Communication"])
    def test_nav_item_visible(self, item: str) -> None:
        expect(self.nav._nav_locator(item)).to_be_visible()

    @allure.title("All top-bar controls are visible")
    @pytest.mark.smoke
    def test_top_bar_controls(self) -> None:
        self.nav.verify_top_bar()

    @allure.title("Clicking Capacity changes the URL")
    @pytest.mark.regression
    def test_navigate_to_capacity(self, page: Page) -> None:
        original = page.url
        self.nav.navigate_to_capacity()
        assert page.url != original
