"""
Shared component: Sidebar navigation.

Present on every page after login.
Used by any test that needs to navigate or verify the left nav.
"""

from playwright.sync_api import Page, Locator, expect


class SidebarNav:
    """Sidebar navigation component — shared across all pages."""

    NAV_ITEMS = [
        "Inventory", "Capacity", "Optimization", "Planning",
        "Migration", "Cluster", "Reports", "Management",
        "Migration Genie", "ITSO Communication",
    ]

    def __init__(self, page: Page) -> None:
        self.page = page
        # ── Locators ──────────────────────────────────────────────
        self.sidebar     = page.locator(".sidebar, .side-nav, [class*='sidebar']").first
        self.brand_title = page.locator(".sidebar :text('MiO-X'), .side-nav :text('MiO-X')").first
        self.brand_tag   = page.locator("text=The Autonomous Migration Engine")
        # Top bar
        self.tasks_btn   = page.locator("text=Tasks").first
        self.calculator  = page.locator("text=Calculator").first
        self.theme_red   = page.locator("button:has-text('Red'), [data-theme='red']").first
        self.theme_white = page.locator("button:has-text('White'), [data-theme='white']").first
        self.user_avatar = page.locator("[class*='user'], [class*='avatar'], [class*='profile']").first

    def _nav_locator(self, label: str) -> Locator:
        """Returns locator for a nav item by its visible label."""
        return self.page.locator(
            f".sidebar :text-is('{label}'), "
            f".side-nav :text-is('{label}'), "
            f"nav :text-is('{label}')"
        ).first

    # ── Verifications ─────────────────────────────────────────────

    def verify_brand(self) -> None:
        expect(self.brand_title).to_be_visible()
        expect(self.brand_title).to_contain_text("MiO-X")

    def verify_all_nav_items(self) -> None:
        for item in self.NAV_ITEMS:
            loc = self._nav_locator(item)
            expect(loc).to_be_visible(timeout=10_000), \
                f"Nav item '{item}' not visible in sidebar"

    def verify_nav_item_active(self, label: str) -> None:
        loc = self._nav_locator(label)
        classes = loc.get_attribute("class") or ""
        assert any(s in classes for s in ("active", "selected", "current", "bg-")), \
            f"Nav item '{label}' does not appear active. Classes: {classes}"

    def verify_top_bar(self) -> None:
        for el in (self.tasks_btn, self.calculator, self.theme_red,
                   self.theme_white, self.user_avatar):
            expect(el).to_be_visible()

    # ── Actions ───────────────────────────────────────────────────

    def click_nav_item(self, label: str) -> None:
        loc = self._nav_locator(label)
        loc.wait_for(state="visible", timeout=10_000)
        loc.click()
        self.page.wait_for_load_state("networkidle")

    def navigate_to_inventory(self) -> None:
        self.click_nav_item("Inventory")

    def navigate_to_capacity(self) -> None:
        self.click_nav_item("Capacity")

    def navigate_to_optimization(self) -> None:
        self.click_nav_item("Optimization")

    def navigate_to_migration(self) -> None:
        self.click_nav_item("Migration")

    def navigate_to_cluster(self) -> None:
        self.click_nav_item("Cluster")

    def navigate_to_reports(self) -> None:
        self.click_nav_item("Reports")
