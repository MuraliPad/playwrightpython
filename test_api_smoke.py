"""
API Smoke Tests — Auth Validation + Endpoint Health Checks.

Auth tests run first validating the full token flow.
Endpoint tests use the live Bearer token from api_session fixture.
No browser involved — fast CI gate.
"""

import json
import allure
import pytest
import requests

from config.settings import settings
from resources.api.inventory_api import InventoryApi


@pytest.fixture(scope="module")
def inv_api(api_session: requests.Session, env_cfg) -> InventoryApi:
    return InventoryApi(api_session, env_cfg.api)


# ══════════════════════════════════════════════════════════════════
# AUTH VALIDATION
# ══════════════════════════════════════════════════════════════════

@allure.feature("API Auth")
@allure.story("Token Flow")
class TestApiAuth:

    @allure.title("user_details.json exists and is readable")
    @pytest.mark.smoke
    @pytest.mark.auth
    def test_user_details_file_exists(self) -> None:
        f = settings.user_details_file
        assert f.exists(), f"user_details.json not found at {f}"
        assert f.stat().st_size > 0, "user_details.json is empty"

    @allure.title("user_details.json contains all required fields")
    @pytest.mark.smoke
    @pytest.mark.auth
    def test_user_details_fields(self) -> None:
        data = json.loads(settings.user_details_file.read_text())
        for field in ("name", "email", "employeeID"):
            assert field in data, f"user_details.json missing field: '{field}'"
            assert data[field], f"user_details.json field '{field}' is empty"

    @allure.title("API_TOKEN is set and formatted as Bearer token")
    @pytest.mark.smoke
    @pytest.mark.auth
    def test_api_token_is_set(self, api_session: requests.Session) -> None:
        token = settings.api_token
        assert token, "API_TOKEN is empty – was api_session fixture called?"
        assert token.startswith("Bearer "), \
            f"API_TOKEN does not start with 'Bearer '. Got: {token[:30]}"

    @allure.title("Bearer token is accepted by a protected endpoint")
    @pytest.mark.smoke
    @pytest.mark.auth
    def test_token_accepted_by_protected_endpoint(self, inv_api: InventoryApi) -> None:
        resp = inv_api.get_all_vms()
        assert resp.status_code == 200, \
            f"Expected 200 (not 401). Token may be invalid. Got: {resp.status_code}"


# ══════════════════════════════════════════════════════════════════
# INVENTORY ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@allure.feature("API")
@allure.story("Inventory")
class TestInventoryEndpoints:

    @allure.title("GET /api/inventory/vms returns 200")
    @pytest.mark.smoke
    @pytest.mark.health
    def test_get_vms(self, inv_api: InventoryApi) -> None:
        resp = inv_api.get_all_vms()
        assert resp.status_code == 200
        assert resp.text

    @allure.title("GET /api/inventory/vms response time < 3s")
    @pytest.mark.smoke
    @pytest.mark.performance
    def test_get_vms_response_time(self, inv_api: InventoryApi) -> None:
        resp = inv_api.get_all_vms()
        inv_api.assert_response_time(resp, max_ms=3000)

    @allure.title("GET /api/inventory/vms/filters returns 200")
    @pytest.mark.smoke
    @pytest.mark.health
    def test_get_vm_filters(self, inv_api: InventoryApi) -> None:
        resp = inv_api.get_vm_filters()
        assert resp.status_code == 200

    @allure.title("GET /api/inventory/migration-categories returns 200")
    @pytest.mark.smoke
    @pytest.mark.health
    def test_get_migration_categories(self, inv_api: InventoryApi) -> None:
        resp = inv_api.get_migration_categories()
        assert resp.status_code == 200

    @allure.title("GET /api/inventory/country-vm-summary returns 200")
    @pytest.mark.smoke
    @pytest.mark.health
    def test_get_country_vm_summary(self, inv_api: InventoryApi) -> None:
        resp = inv_api.get_country_vm_summary()
        assert resp.status_code == 200

    @allure.title("GET /api/inventory/esx returns 200")
    @pytest.mark.smoke
    @pytest.mark.health
    def test_get_esx(self, inv_api: InventoryApi) -> None:
        resp = inv_api.get_esx_inventory()
        assert resp.status_code == 200
