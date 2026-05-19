@echo off
REM ============================================================
REM  MiO-X Playwright Python Framework – Windows run script
REM
REM  USAGE:
REM    run_tests.bat                         all tests, dev, chromium
REM    run_tests.bat --env uat               UAT environment
REM    run_tests.bat --tags smoke            smoke only
REM    run_tests.bat --tags auth             auth tests only
REM    run_tests.bat --tags integrity        integrity tests only
REM    run_tests.bat --parallel              4 workers in parallel
REM    run_tests.bat --headed                show browser window
REM    run_tests.bat --browser firefox       use Firefox
REM    run_tests.bat --remote                use remote Selenium Grid
REM    run_tests.bat --remote-url http://localhost:4444
REM ============================================================

setlocal EnableDelayedExpansion

REM ── Defaults ──────────────────────────────────────────────
set ENV=dev
set BROWSER=chromium
set HEADED=
set TAGS=
set PARALLEL=False
set WORKERS=4
set REMOTE=
set REMOTE_URL=http://localhost:4444/wd/hub
set OUTPUT=results

REM ── Argument parser ───────────────────────────────────────
:parse_args
if "%~1"=="" goto end_parse
if /I "%~1"=="--env"        ( set ENV=%~2          & shift & shift & goto parse_args )
if /I "%~1"=="--browser"    ( set BROWSER=%~2      & shift & shift & goto parse_args )
if /I "%~1"=="--headed"     ( set HEADED=--headed  & shift & goto parse_args )
if /I "%~1"=="--tags"       ( set TAGS=%~2         & shift & shift & goto parse_args )
if /I "%~1"=="--parallel"   ( set PARALLEL=True    & shift & goto parse_args )
if /I "%~1"=="--workers"    ( set WORKERS=%~2      & shift & shift & goto parse_args )
if /I "%~1"=="--remote"     ( set REMOTE=--use-remote & shift & goto parse_args )
if /I "%~1"=="--remote-url" ( set REMOTE_URL=%~2   & shift & shift & goto parse_args )
echo [ERROR] Unknown argument: %~1
exit /b 1
:end_parse

REM ── Create output dirs ─────────────────────────────────────
if not exist "!OUTPUT!\allure"       mkdir "!OUTPUT!\allure"
if not exist "!OUTPUT!\screenshots"  mkdir "!OUTPUT!\screenshots"

REM ── Print config ──────────────────────────────────────────
echo.
echo ============================================================
echo   MiO-X Playwright Tests
echo ============================================================
echo   ENV      : !ENV!
echo   Browser  : !BROWSER!
echo   Tags     : !TAGS!
echo   Parallel : !PARALLEL!
if "!PARALLEL!"=="True" echo   Workers  : !WORKERS!
echo   Remote   : !REMOTE!
echo ============================================================
echo.

REM ── Build pytest command ───────────────────────────────────
set BASE_CMD=pytest ^
    --env !ENV! ^
    --browser !BROWSER! ^
    !HEADED! ^
    !REMOTE! ^
    --remote-url !REMOTE_URL! ^
    --alluredir=!OUTPUT!llure ^
    --clean-alluredir

REM Add tags
if not "!TAGS!"=="" set BASE_CMD=!BASE_CMD! -m "!TAGS!"

REM Add parallel
if "!PARALLEL!"=="True" (
    where pytest-xdist >nul 2>&1
    if !ERRORLEVEL!==0 (
        set BASE_CMD=!BASE_CMD! -n !WORKERS!
    ) else (
        echo [WARN] pytest-xdist not found. Install: pip install pytest-xdist
        echo [FALLBACK] Running sequentially...
    )
)

echo Running: !BASE_CMD!
echo.
!BASE_CMD!
set TEST_EXIT=!ERRORLEVEL!

REM ── Allure report ──────────────────────────────────────────
echo.
where allure >nul 2>&1
if !ERRORLEVEL!==0 (
    echo Generating Allure report...
    allure generate !OUTPUT!\allure --clean -o !OUTPUT!\allure-report
    echo.
    echo  Allure report : !OUTPUT!\allure-report\index.html
    echo  Live view     : allure serve !OUTPUT!\allure
) else (
    echo [WARN] allure CLI not found.
    echo        Install: scoop install allure OR choco install allure
    echo        HTML report: !OUTPUT!\allure-report
)

echo.
if !TEST_EXIT!==0 (echo [RESULT] All tests PASSED) else (echo [RESULT] Tests FAILED - exit: !TEST_EXIT!)
endlocal
exit /b %TEST_EXIT%
