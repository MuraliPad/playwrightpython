"""
Page Object: MiO-X Inventory Page.
URL: /inventory

DOM confirmed Apr 2026:
    h2.text-slate-900                          → page title
    p.text-sm.text-slate-600.mt-1              → date subtitle
    th[data-slot="table-head"]
      span.truncate.cursor-pointer             → column label
      span[role=button][aria-label="Filter column"]
      span[role=button][aria-label="Toggle sort"]
"""

import re
from playwright.sync_api import Page, Locator, expect
from resources.base.base_page import BasePage


class InventoryPage(BasePage):

    MANDATORY_VM_COLUMNS  = ["Datacenter", "Region", "ESX Host", "ESX Cluster", "vCenter"]
    MANDATORY_ESX_COLUMNS = ["ESX Host", "IP Address", "Cluster", "Datacenter",
                             "Region", "vCenter", "CPU Model", "CPU Cores"]

    DROPDOWN_OPTIONS = {
        "VM":  {"title": "VM Inventory",        "sublabel": "Compute",   "desc": "Inspect virtual machines, migration signals, and anomaly markers"},
        "ESX": {"title": "ESX Inventory",        "sublabel": "Host",      "desc": "Review host posture, cluster alignment, and infrastructure insights"},
        "OCP": {"title": "OpenShift Inventory",  "sublabel": "Platform",  "desc": "Track platform workloads and prepare for dedicated OpenShift data views"},
    }

    def __init__(self, page: Page, base_url: str) -> None:
        super().__init__(page, base_url)
        # ── Page header ───────────────────────────────────────────
        self.page_title     = page.locator("h2.text-slate-900:has-text('Inventory')")
        self.page_date      = page.locator("p.text-sm.text-slate-600.mt-1")
        # ── Dropdown ──────────────────────────────────────────────
        self.dropdown_trigger = page.locator(
            "button[aria-haspopup='menu']:has-text('Inventory'), "
            "button[aria-haspopup='listbox']:has-text('Inventory')"
        ).first
        self.dropdown_panel = page.locator(
            "[role='menu']:has-text('VM Inventory'), "
            "[role='listbox']:has-text('VM Inventory')"
        ).first
        # ── Table ─────────────────────────────────────────────────
        self.table          = page.locator("table:has(th[data-slot='table-head'])").first
        self.body_rows      = page.locator("tbody tr[data-slot='table-row']")
        # ── Toolbar ───────────────────────────────────────────────
        self.btn_export     = page.locator("button:text-is('Export')").first
        self.btn_customize  = page.locator("button:has-text('Customize')").first
        self.btn_insights   = page.locator("button:text-is('Insights')").first
        # ── Pagination ────────────────────────────────────────────
        self.pagination_info  = page.locator("*:has-text('Showing'):has-text('results')").first
        self.jump_page_input  = page.locator("input[type='number']").first
        self.jump_page_go     = page.locator("button:text-is('Go')").first

    # ── Contract ──────────────────────────────────────────────────

    def verify_page_loaded(self) -> None:
        self.page_title.wait_for(state="visible", timeout=15_000)
        expect(self.page_title).to_contain_text("Inventory")

    # ── Column locator builders ───────────────────────────────────

    def _column_label(self, name: str) -> Locator:
        """span.truncate.cursor-pointer inside th[data-slot='table-head']."""
        return self.page.locator(
            f"th[data-slot='table-head'] "
            f"span.truncate.cursor-pointer:text-is('{name}')"
        )

    def _column_filter_btn(self, name: str) -> Locator:
        """Filter icon button inside the named column header."""
        return self.page.locator(
            f"th[data-slot='table-head']:has(span:text-is('{name}')) "
            f"span[role='button'][aria-label='Filter column']"
        )

    def _column_sort_btn(self, name: str) -> Locator:
        """Sort button inside the named column header."""
        return self.page.locator(
            f"th[data-slot='table-head']:has(span:text-is('{name}')) "
            f"span[role='button'][aria-label='Toggle sort']"
        )

    # ── Section 1: Page Header ────────────────────────────────────

    def verify_page_title(self) -> None:
        expect(self.page_title).to_have_text("Inventory")

    def verify_page_date(self) -> None:
        date_text = self.page_date.inner_text().strip()
        pattern = r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+\w+\s+\d+,\s+\d{4}"
        assert re.match(pattern, date_text), \
            f"Date format unexpected: '{date_text}'"

    # ── Section 2: Inventory Type Dropdown ───────────────────────

    def open_dropdown(self) -> None:
        self.dropdown_trigger.click()
        self.dropdown_panel.wait_for(state="visible", timeout=5_000)

    def close_dropdown(self) -> None:
        self.page.keyboard.press("Escape")

    def verify_dropdown_option(self, key: str) -> None:
        """Validates title, sublabel and description for VM | ESX | OCP."""
        opt = self.DROPDOWN_OPTIONS[key]
        panel_text = self.dropdown_panel.inner_text()
        assert opt["title"]    in panel_text, f"Dropdown missing title: {opt['title']}"
        assert opt["sublabel"] in panel_text, f"Dropdown missing sublabel: {opt['sublabel']}"
        assert opt["desc"]     in panel_text, f"Dropdown missing desc: {opt['desc']}"

    def verify_all_dropdown_options(self) -> None:
        self.open_dropdown()
        for key in ("VM", "ESX", "OCP"):
            self.verify_dropdown_option(key)
        self.close_dropdown()

    def select_inventory_type(self, key: str) -> None:
        """Select VM | ESX | OCP from dropdown."""
        title = self.DROPDOWN_OPTIONS[key]["title"]
        self.open_dropdown()
        self.page.locator(
            f"[role='menuitem']:has-text('{title}'), "
            f"[role='option']:has-text('{title}')"
        ).first.click()
        self.wait_for_page_ready()

    # ── Section 3: Column Validation ─────────────────────────────

    def verify_column_label(self, name: str) -> None:
        expect(self._column_label(name)).to_be_visible(timeout=10_000)

    def verify_column_filter_button(self, name: str) -> None:
        expect(self._column_filter_btn(name)).to_be_visible()

    def verify_column_sort_button(self, name: str) -> None:
        expect(self._column_sort_btn(name)).to_be_visible()

    def verify_full_column_header(self, name: str) -> None:
        """Label + filter button + sort button."""
        self.verify_column_label(name)
        self.verify_column_filter_button(name)
        self.verify_column_sort_button(name)

    def verify_all_vm_columns(self) -> None:
        for col in self.MANDATORY_VM_COLUMNS:
            self.verify_full_column_header(col)

    def verify_all_esx_columns(self) -> None:
        for col in self.MANDATORY_ESX_COLUMNS:
            self.verify_full_column_header(col)

    def click_column_sort(self, name: str) -> None:
        self._column_sort_btn(name).click()
        self.wait_for_page_ready()

    # ── Section 4: Toolbar ────────────────────────────────────────

    def verify_toolbar(self) -> None:
        for btn in (self.btn_export, self.btn_customize, self.btn_insights):
            expect(btn).to_be_visible()

    # ── Section 5: Data rows ──────────────────────────────────────

    def verify_table_visible(self) -> None:
        expect(self.table).to_be_visible()

    def verify_has_data_rows(self) -> None:
        count = self.body_rows.count()
        assert count >= 1, f"Expected ≥1 data row, found {count}"

    def get_row_count(self) -> int:
        return self.body_rows.count()

    # ── Section 6: Pagination ─────────────────────────────────────

    def verify_pagination_info(self) -> None:
        text = self.pagination_info.inner_text().strip()
        assert re.match(r"Showing\s+\d+\s+to\s+\d+\s+of\s+\d+\s+results", text), \
            f"Unexpected pagination format: '{text}'"

    def get_pagination_total(self) -> int:
        """Extract the total count from 'Showing X to Y of Z results'."""
        text = self.pagination_info.inner_text().strip()
        match = re.search(r"of\s+(\d+)\s+results", text)
        assert match, f"Cannot parse total from: '{text}'"
        return int(match.group(1))

    def jump_to_page(self, page_num: int) -> None:
        self.jump_page_input.fill(str(page_num))
        self.jump_page_go.click()
        self.wait_for_page_ready()
