@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: Form Fill Demo — Command-line trigger for n8n Fill Form v0.1
:: ============================================================
::
:: Usage:
::   form-fill-demo.bat [form_type] [options]
::
:: Form types:
::   Environmental  (ENV-001)
::   Water          (WCN-001)
::   Planning       (APP-001)
::   Electricity    (NEC-001)
::   Effluent       (TEF-001)
::   Test           (TST-001)
::
:: Options:
::   --test         Use n8n test webhook URL (for debugging in n8n UI)
::   --user UUID    Override the default user_id
::   --project NAME Override the project_name in additional_data
::
:: Examples:
::   form-fill-demo.bat Water
::   form-fill-demo.bat Electricity --test
::   form-fill-demo.bat Environmental --user a1b2c3d4-e5f6-7890-abcd-ef1234567890
::   form-fill-demo.bat Planning --project "Cambridge Data Centre" --test
::

:: --- Configuration ---
set "N8N_BASE=http://localhost:5678"
set "WEBHOOK_PATH=webhook/fill-form"
set "TEST_PATH=webhook-test/fill-form"
set "DEFAULT_USER_ID=f24ee278-fb1e-42dc-8777-ac9af1954d25"

:: --- Defaults ---
set "USE_TEST="
set "USER_ID=%DEFAULT_USER_ID%"
set "PROJECT_NAME=Demo Project"
set "FORM_TYPE="

:: --- Parse arguments ---
:parse_args
if "%~1"=="" goto :check_form_type

:: Check for options first
if /i "%~1"=="--test" (
    set "USE_TEST=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--user" (
    set "USER_ID=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--project" (
    set "PROJECT_NAME=%~2"
    shift
    shift
    goto :parse_args
)

:: Must be the form type
if not defined FORM_TYPE (
    set "FORM_TYPE=%~1"
    shift
    goto :parse_args
)

:: Unknown argument
echo ERROR: Unknown argument: %~1
goto :show_menu

:check_form_type
if defined FORM_TYPE goto :resolve_ref

:: --- Interactive menu ---
:show_menu
echo.
echo  =============================================
echo   Form Fill Demo — n8n Webhook Trigger
echo  =============================================
echo.
echo   Select a form type to fill:
echo.
echo     1. Environmental   (ENV-001)
echo     2. Water           (WCN-001)
echo     3. Planning        (APP-001)
echo     4. Electricity     (NEC-001)
echo     5. Effluent        (TEF-001)
echo     6. Test            (TST-001)
echo.
echo     0. Exit
echo.
set /p "CHOICE=  Enter choice (1-6): "

if "%CHOICE%"=="0" goto :eof
if "%CHOICE%"=="1" set "FORM_TYPE=Environmental"
if "%CHOICE%"=="2" set "FORM_TYPE=Water"
if "%CHOICE%"=="3" set "FORM_TYPE=Planning"
if "%CHOICE%"=="4" set "FORM_TYPE=Electricity"
if "%CHOICE%"=="5" set "FORM_TYPE=Effluent"
if "%CHOICE%"=="6" set "FORM_TYPE=Test"

if not defined FORM_TYPE (
    echo  Invalid choice. Please try again.
    goto :show_menu
)

:: --- Resolve form_type to template_ref ---
:resolve_ref
set "TEMPLATE_REF="

if /i "%FORM_TYPE%"=="Environmental" set "TEMPLATE_REF=ENV-001"
if /i "%FORM_TYPE%"=="Water"         set "TEMPLATE_REF=WCN-001"
if /i "%FORM_TYPE%"=="Planning"      set "TEMPLATE_REF=APP-001"
if /i "%FORM_TYPE%"=="Electricity"   set "TEMPLATE_REF=NEC-001"
if /i "%FORM_TYPE%"=="Effluent"      set "TEMPLATE_REF=TEF-001"
if /i "%FORM_TYPE%"=="Test"          set "TEMPLATE_REF=TST-001"

if not defined TEMPLATE_REF (
    echo.
    echo  ERROR: Unknown form type: "%FORM_TYPE%"
    echo  Valid types: Environmental, Water, Planning, Electricity, Effluent, Test
    echo.
    exit /b 1
)

:: --- Build run_id with timestamp ---
for /f "tokens=1-5 delims=/:. " %%a in ("%date% %time%") do (
    set "TIMESTAMP=%%c-%%a-%%b_%%d-%%e"
)
set "RUN_ID=Demo-%TEMPLATE_REF%-%TIMESTAMP%"

:: --- Select webhook URL ---
if defined USE_TEST (
    set "WEBHOOK_URL=%N8N_BASE%/%TEST_PATH%"
    set "MODE_LABEL=TEST"
) else (
    set "WEBHOOK_URL=%N8N_BASE%/%WEBHOOK_PATH%"
    set "MODE_LABEL=PRODUCTION"
)

:: --- Display summary ---
echo.
echo  -----------------------------------------
echo   Form Fill Demo
echo  -----------------------------------------
echo   Form Type    : %FORM_TYPE%
echo   Template Ref : %TEMPLATE_REF%
echo   Run ID       : %RUN_ID%
echo   User ID      : %USER_ID%
echo   Project      : %PROJECT_NAME%
echo   Webhook      : %WEBHOOK_URL%
echo   Mode         : %MODE_LABEL%
echo  -----------------------------------------
echo.

:: --- Build JSON payload ---
set "JSON_BODY={\"run_id\":\"%RUN_ID%\",\"template_ref\":\"%TEMPLATE_REF%\",\"user_id\":\"%USER_ID%\",\"additional_data\":{\"project_name\":\"%PROJECT_NAME%\",\"simulation_date\":\"%date%\"}}"

:: --- Send request ---
echo  Sending request...
echo.

curl -s -X POST "%WEBHOOK_URL%" ^
  -H "Content-Type: application/json" ^
  -d "%JSON_BODY%" ^
  -w "\n\n  HTTP Status: %%{http_code}\n" ^
  --max-time 120

echo.
echo  -----------------------------------------
echo   Done.
echo  -----------------------------------------

endlocal
