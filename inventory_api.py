"""
API Resource: Inventory Endpoints.

Endpoints (from Swagger):
    GET  /api/inventory/vms
    GET  /api/inventory/vms/filters
    GET  /api/inventory/migration-categories
    GET  /api/inventory/country-vm-summary
    GET  /api/inventory/esx
"""

from typing import Optional, Dict
import requests
from resources.api.api_client import ApiClient


class InventoryApi(ApiClient):

    def get_all_vms(self, params: Optional[Dict] = None) -> requests.Response:
        return self.get("/api/inventory/vms", params=params)

    def get_vm_count(self) -> int:
        resp = self.get_all_vms()
        return self.get_total_count(resp)

    def get_vms_filtered(
        self,
        datacenter: Optional[str] = None,
        region: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> requests.Response:
        params: Dict = {"page": page, "page_size": page_size}
        if datacenter:
            params["datacenter"] = datacenter
        if region:
            params["region"] = region
        return self.get("/api/inventory/vms", params=params)

    def get_vm_filters(self, columns: Optional[str] = None) -> requests.Response:
        """
        GET /api/inventory/vms/filters
        The endpoint requires a `columns` query param on some versions.
        Pass columns as a comma-separated string e.g. "datacenter,region"
        or leave None to try without (will return 422 if required by server).
        """
        params = {}
        if columns:
            params["columns"] = columns
        return self.get("/api/inventory/vms/filters", params=params or None)

    def get_migration_categories(self) -> requests.Response:
        return self.get("/api/inventory/migration-categories")

    def get_country_vm_summary(self) -> requests.Response:
        return self.get("/api/inventory/country-vm-summary")

    def get_esx_inventory(self, params: Optional[Dict] = None) -> requests.Response:
        return self.get("/api/inventory/esx", params=params)

    def get_esx_count(self) -> int:
        resp = self.get_esx_inventory()
        return self.get_total_count(resp)
