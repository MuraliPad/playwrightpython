"""
ESX Inventory Table Tests.

Validates page header, dropdown, columns (label + filter + sort),
toolbar, pagination, and data rows.
"""

import allure
import pytest
from playwright.sync_api import Page

from resources.pages.inventory_page import InventoryPage
from resources.components.sidebar_nav import SidebarNav


@pytest.fixture()
def inventory(page: Page, env_cfg) -> InventoryPage:
    """Navigate to Inventory page and return the page object."""
    nav = SidebarNav(page)
    page.goto(env_cfg.ui)
    nav.sidebar.wait_for(state="visible", timeout=30_000)
    nav.navigate_to_inventory()
    inv = InventoryPage(page, env_cfg.ui)
    inv.verify_page_loaded()
    return inv


@allure.feature("Inventory")
@allure.story("Page Header")
class TestInventoryHeader:

    @allure.title("Page title is 'Inventory'")
    @pytest.mark.smoke
    def test_page_title(self, inventory: InventoryPage) -> None:
        inventory.verify_page_title()

    @allure.title("Page date subtitle is displayed")
    @pytest.mark.smoke
    def test_page_date(self, inventory: InventoryPage) -> None:
        inventory.verify_page_date()


@allure.feature("Inventory")
@allure.story("Inventory Type Dropdown")
class TestInventoryDropdown:

    @allure.title("Dropdown trigger is visible")
    @pytest.mark.smoke
    def test_dropdown_trigger_visible(self, inventory: InventoryPage) -> None:
        from playwright.sync_api import expect
        expect(inventory.dropdown_trigger).to_be_visible()

    @allure.title("Dropdown opens on click")
    @pytest.mark.smoke
    def test_dropdown_opens(self, inventory: InventoryPage) -> None:
        inventory.open_dropdown()
        from playwright.sync_api import expect
        expect(inventory.dropdown_panel).to_be_visible()
        inventory.close_dropdown()

    @allure.title("All three dropdown options are valid")
    @pytest.mark.smoke
    def test_all_dropdown_options(self, inventory: InventoryPage) -> None:
        inventory.verify_all_dropdown_options()

    @allure.title("Dropdown option: {key}")
    @pytest.mark.regression
    @pytest.mark.parametrize("key", ["VM", "ESX", "OCP"])
    def test_dropdown_option(self, inventory: InventoryPage, key: str) -> None:
        inventory.open_dropdown()
        inventory.verify_dropdown_option(key)
        inventory.close_dropdown()


@allure.feature("Inventory")
@allure.story("ESX Table Columns")
class TestInventoryColumns:

    @allure.title("Table is visible")
    @pytest.mark.smoke
    def test_table_visible(self, inventory: InventoryPage) -> None:
        inventory.verify_table_visible()

    @allure.title("Table has at least one data row")
    @pytest.mark.smoke
    def test_has_data_rows(self, inventory: InventoryPage) -> None:
        inventory.verify_has_data_rows()

    @allure.title("Column label: {col}")
    @pytest.mark.smoke
    @pytest.mark.parametrize("col", InventoryPage.MANDATORY_VM_COLUMNS)
    def test_column_label(self, inventory: InventoryPage, col: str) -> None:
        inventory.verify_column_label(col)

    @allure.title("Column filter button: {col}")
    @pytest.mark.smoke
    @pytest.mark.parametrize("col", InventoryPage.MANDATORY_VM_COLUMNS)
    def test_column_filter_button(self, inventory: InventoryPage, col: str) -> None:
        inventory.verify_column_filter_button(col)

    @allure.title("Column sort button: {col}")
    @pytest.mark.smoke
    @pytest.mark.parametrize("col", InventoryPage.MANDATORY_VM_COLUMNS)
    def test_column_sort_button(self, inventory: InventoryPage, col: str) -> None:
        inventory.verify_column_sort_button(col)

    @allure.title("Full column header validated: {col}")
    @pytest.mark.regression
    @pytest.mark.parametrize("col", InventoryPage.MANDATORY_VM_COLUMNS)
    def test_full_column_header(self, inventory: InventoryPage, col: str) -> None:
        inventory.verify_full_column_header(col)

    @allure.title("All VM columns validated in one pass")
    @pytest.mark.smoke
    def test_all_vm_columns(self, inventory: InventoryPage) -> None:
        inventory.verify_all_vm_columns()

    @allure.title("All ESX columns validated in one pass")
    @pytest.mark.regression
    def test_all_esx_columns(self, inventory: InventoryPage) -> None:
        inventory.select_inventory_type("ESX")
        inventory.verify_all_esx_columns()


@allure.feature("Inventory")
@allure.story("Table Toolbar & Pagination")
class TestInventoryToolbar:

    @allure.title("All toolbar buttons are visible")
    @pytest.mark.smoke
    def test_toolbar(self, inventory: InventoryPage) -> None:
        inventory.verify_toolbar()

    @allure.title("Pagination info is displayed")
    @pytest.mark.smoke
    def test_pagination_info(self, inventory: InventoryPage) -> None:
        inventory.verify_pagination_info()

    @allure.title("Jump to page 1 works")
    @pytest.mark.regression
    def test_jump_to_page(self, inventory: InventoryPage) -> None:
        inventory.jump_to_page(1)
