@echo off
REM ============================================================
REM  MiO-X Playwright – Windows run script
REM
REM  USAGE:
REM    run_tests.bat                         all tests, dev
REM    run_tests.bat --env uat               UAT environment
REM    run_tests.bat --tags smoke            smoke only
REM    run_tests.bat --tags auth             auth tests only
REM    run_tests.bat --tags "smoke or auth"  multiple tags
REM    run_tests.bat --parallel              4 parallel workers
REM    run_tests.bat --headed                show browser window
REM    run_tests.bat --remote                use remote Selenium Grid
REM
REM  REPORTS generated in results\:
REM    results\allure\          raw Allure JSON (used by allure generate)
REM    results\allure-report\   HTML Allure report (open index.html)
REM    results\report.html      pytest-html report (no extra tool needed)
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
REM REMOTE_URL default comes from .env (REMOTE_URL=ws://...).
REM Override here only when passing --remote-url on the CLI.
set REMOTE_URL=
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

REM ── Build output paths as separate variables ───────────────
REM !! IMPORTANT: never use \a \b \n etc inside a set value !!
REM !! BAT treats backslash-letter as escape in some contexts !!
REM !! Use separate variables for each path segment instead.  !!
set ALLURE_RAW=%OUTPUT%\allure
set ALLURE_HTML=%OUTPUT%\allure-report
set HTML_REPORT=%OUTPUT%\report.html
set SCREENSHOTS=%OUTPUT%\screenshots

REM ── Create output directories ──────────────────────────────
if not exist "!ALLURE_RAW!"   mkdir "!ALLURE_RAW!"
if not exist "!ALLURE_HTML!"  mkdir "!ALLURE_HTML!"
if not exist "!SCREENSHOTS!"  mkdir "!SCREENSHOTS!"

REM ── Print config ──────────────────────────────────────────
echo.
echo ============================================================
echo   MiO-X Playwright Tests
echo ============================================================
echo   ENV      : !ENV!
echo   Browser  : !BROWSER!
echo   Tags     : !TAGS!
echo   Parallel : !PARALLEL!
echo   Remote   : !REMOTE!
echo   Reports  : !ALLURE_HTML!\index.html
echo              !HTML_REPORT!
echo ============================================================
echo.

REM ── Build pytest command ───────────────────────────────────
REM Allure dir uses the variable NOT a backslash-a path literal
set BASE_CMD=pytest ^
    --env !ENV! ^
    --browser !BROWSER! ^
    !HEADED! ^
    !REMOTE! ^
    --alluredir=!ALLURE_RAW! ^
    --clean-alluredir

REM Only pass --remote-url if explicitly set on CLI (otherwise .env value is used)
if not "!REMOTE_URL!"=="" set BASE_CMD=!BASE_CMD! --remote-url !REMOTE_URL!

REM Add tag filter
if not "!TAGS!"=="" set BASE_CMD=!BASE_CMD! -m "!TAGS!"

REM Add parallel workers
if "!PARALLEL!"=="True" (
    where pytest-xdist >nul 2>&1
    if !ERRORLEVEL!==0 (
        set BASE_CMD=!BASE_CMD! -n !WORKERS!
    ) else (
        echo [WARN] pytest-xdist not installed. Run: pip install pytest-xdist
        echo [FALLBACK] Running sequentially...
    )
)

echo Running: !BASE_CMD!
echo.
!BASE_CMD!
set TEST_EXIT=!ERRORLEVEL!

REM ── Generate Allure HTML report ────────────────────────────
echo.
echo Generating Allure report...
where allure >nul 2>&1
if !ERRORLEVEL!==0 (
    allure generate "!ALLURE_RAW!" --clean -o "!ALLURE_HTML!"
    if !ERRORLEVEL!==0 (
        echo.
        echo ============================================================
        echo   REPORTS
        echo ============================================================
        echo   Allure HTML  : !ALLURE_HTML!\index.html
        echo   Allure live  : allure serve !ALLURE_RAW!
        echo   pytest-html  : !HTML_REPORT!
        echo   Screenshots  : !SCREENSHOTS!\
        echo ============================================================
    ) else (
        echo [WARN] Allure generation failed.
    )
) else (
    echo [WARN] allure CLI not found on PATH.
    echo        Install with one of:
    echo          scoop install allure
    echo          choco install allure
    echo        After install, re-run: allure generate !ALLURE_RAW! -o !ALLURE_HTML!
    echo.
    echo   pytest-html report is still available (no extra tool needed):
    echo   !HTML_REPORT!
)

REM ── Result ────────────────────────────────────────────────
echo.
if !TEST_EXIT!==0 (
    echo [RESULT] All tests PASSED
) else (
    echo [RESULT] Tests FAILED  (exit code: !TEST_EXIT!)
)

endlocal
exit /b %TEST_EXIT%
