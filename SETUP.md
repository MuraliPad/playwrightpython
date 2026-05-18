# MiO-X Playwright Python Framework — Setup Guide

## Install

```bat
pip install -r requirements.txt
playwright install chromium
```

## Extract SSO tokens (once per session)

```bat
python scripts/extract_storage.py --env dev
```

## Run tests

```bat
:: All tests
run_tests.bat

:: Smoke only
run_tests.bat --tags smoke

:: Auth tests only
run_tests.bat --tags auth

:: Integrity tests
run_tests.bat --tags integrity

:: UAT environment
run_tests.bat --env uat

:: Headed (visible browser)
run_tests.bat --headed

:: Parallel - 4 workers
run_tests.bat --parallel

:: Remote Grid
run_tests.bat --remote --remote-url http://localhost:4444/wd/hub

:: Firefox
run_tests.bat --browser firefox
```

## Direct pytest commands

```bat
pytest --env dev -m smoke -v
pytest --env uat -m "smoke and not performance" -v
pytest --env dev -m auth -v
pytest --env dev -n 4 -v                         # parallel
pytest --env dev --headed -v                     # headed
pytest tests/api/test_api_smoke.py -v
pytest tests/integrity/ -v
```

## Allure report

```bat
allure serve results/allure
```

## Project structure

```
miox_playwright/
├── config/
│   ├── env_config.py          ← URL map: dev/sit/uat/prod
│   ├── settings.py            ← all settings as dataclass
│   └── testdata/
│       ├── user_details.json  ← API auth credentials
│       └── storage.json       ← SSO localStorage tokens (extracted)
├── resources/
│   ├── base/
│   │   └── base_page.py       ← abstract base all pages inherit
│   ├── components/
│   │   └── sidebar_nav.py     ← shared nav component
│   ├── pages/
│   │   ├── login_page.py
│   │   └── inventory_page.py
│   └── api/
│       ├── api_client.py      ← base HTTP client
│       └── inventory_api.py   ← inventory endpoints
├── tests/
│   ├── login/test_login.py
│   ├── inventory/
│   │   ├── test_navigation.py
│   │   └── test_esx_table.py
│   ├── api/test_api_smoke.py
│   └── integrity/test_integrity.py
├── scripts/
│   └── extract_storage.py     ← extract SSO tokens from browser
├── conftest.py                ← fixtures: page, api_session, env_cfg
├── pytest.ini
├── requirements.txt
└── run_tests.bat
```
