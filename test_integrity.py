"""
UI ↔ API Integrity Tests.

Cross-validates that the UI and API return consistent data.
Each test opens a real browser AND calls the API, then compares results.
"""

import allure
import pytest
import requests
from playwright.sync_api import Page

from config.settings import settings
from resources.api.inventory_api import InventoryApi
from resources.pages.inventory_page import InventoryPage
from resources.components.sidebar_nav import SidebarNav


@pytest.fixture()
def inv_api(api_session: requests.Session, env_cfg) -> InventoryApi:
    return InventoryApi(api_session, env_cfg.api)


@pytest.fixture()
def inventory_ui(page: Page, env_cfg) -> InventoryPage:
    nav = SidebarNav(page)
    page.goto(env_cfg.ui)
    nav.sidebar.wait_for(state="visible", timeout=30_000)
    nav.navigate_to_inventory()
    inv = InventoryPage(page, env_cfg.ui)
    inv.verify_page_loaded()
    return inv


@allure.feature("Integrity")
@allure.story("Count Match")
class TestCountMatch:

    @allure.title("VM count: API total matches UI pagination total")
    @pytest.mark.smoke
    @pytest.mark.integrity
    def test_vm_count_matches(
        self,
        inv_api: InventoryApi,
        inventory_ui: InventoryPage,
    ) -> None:
        # API count
        api_count = inv_api.get_vm_count()

        # UI count
        inventory_ui.select_inventory_type("VM")
        ui_count = inventory_ui.get_pagination_total()

        diff = abs(api_count - ui_count)
        assert diff <= settings.count_tolerance, (
            f"VM count mismatch: API={api_count}, UI={ui_count}, "
            f"diff={diff}, tolerance={settings.count_tolerance}"
        )

    @allure.title("ESX host count: API total matches UI pagination total")
    @pytest.mark.smoke
    @pytest.mark.integrity
    def test_esx_count_matches(
        self,
        inv_api: InventoryApi,
        inventory_ui: InventoryPage,
    ) -> None:
        api_count = inv_api.get_esx_count()
        inventory_ui.select_inventory_type("ESX")
        ui_count = inventory_ui.get_pagination_total()

        diff = abs(api_count - ui_count)
        assert diff <= settings.count_tolerance, (
            f"ESX count mismatch: API={api_count}, UI={ui_count}, diff={diff}"
        )


@allure.feature("Integrity")
@allure.story("API Data in UI")
class TestApiDataInUI:

    @allure.title("First ESX host from API is visible in UI table")
    @pytest.mark.regression
    @pytest.mark.integrity
    def test_first_esx_host_in_ui(
        self,
        inv_api: InventoryApi,
        inventory_ui: InventoryPage,
    ) -> None:
        # Get first hostname from API
        resp  = inv_api.get_esx_inventory()
        data  = inv_api.parse_json(resp)
        items = data.get("items", data) if isinstance(data, dict) else data
        assert items, "API returned no ESX items"
        first = items[0]
        hostname = first.get("name") or first.get("hostname") or first.get("esx_name")
        assert hostname, f"Cannot find hostname key in first ESX item: {first}"

        # Verify in UI table
        inventory_ui.select_inventory_type("ESX")
        row = inventory_ui.page.locator(
            f"tbody tr[data-slot='table-row'] :text('{hostname}')"
        ).first
        row.wait_for(state="visible", timeout=15_000)


@allure.feature("Integrity")
@allure.story("Filter Match")
class TestFilterMatch:

    @allure.title("Filter Datacenter=GB-WGDC: UI count matches API filtered count")
    @pytest.mark.regression
    @pytest.mark.integrity
    def test_datacenter_filter_matches(
        self,
        inv_api: InventoryApi,
        inventory_ui: InventoryPage,
    ) -> None:
        datacenter = "GB-WGDC"

        # UI: apply filter
        inventory_ui.select_inventory_type("VM")
        inventory_ui.page.locator(
            f"th[data-slot='table-head']:has(span:text-is('Datacenter')) "
            f"span[role='button'][aria-label='Filter column']"
        ).click()
        filter_input = inventory_ui.page.locator(
            "[role='dialog'] input, [role='menu'] input"
        ).first
        filter_input.wait_for(state="visible", timeout=5_000)
        filter_input.fill(datacenter)
        inventory_ui.page.keyboard.press("Enter")
        inventory_ui.wait_for_page_ready()
        ui_count = inventory_ui.get_pagination_total()

        # API: same filter
        resp = inv_api.get_vms_filtered(datacenter=datacenter)
        api_count = inv_api.get_total_count(resp)

        diff = abs(api_count - ui_count)
        assert diff <= settings.count_tolerance, (
            f"Filter mismatch (datacenter={datacenter}): "
            f"API={api_count}, UI={ui_count}, diff={diff}"
        )


@allure.feature("Integrity")
@allure.story("Performance")
class TestPerformance:

    @allure.title("API responds within 3s while browser is active")
    @pytest.mark.regression
    @pytest.mark.integrity
    def test_api_response_time_during_ui_session(
        self,
        inv_api: InventoryApi,
        inventory_ui: InventoryPage,
    ) -> None:
        inventory_ui.select_inventory_type("VM")
        resp = inv_api.get_all_vms()
        inv_api.assert_response_time(resp, max_ms=3000)
