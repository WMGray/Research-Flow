@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%"
set "FRONTEND_DIR=%ROOT%frontend"
set "FRONTEND_URL=http://127.0.0.1:5173"
set "BACKEND_URL=http://127.0.0.1:8000/health"
set "MODE=electron"

if /i "%~1"=="--help" goto :usage
if /i "%~1"=="-h" goto :usage
if /i "%~1"=="/?" goto :usage
if /i "%~1"=="--browser" set "MODE=browser"
if /i "%~1"=="browser" set "MODE=browser"

if not exist "%FRONTEND_DIR%" (
  echo [ERROR] Frontend directory not found: "%FRONTEND_DIR%"
  exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found in PATH.
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm was not found in PATH.
  exit /b 1
)

if "%MODE%"=="electron" (
  if not exist "%FRONTEND_DIR%\node_modules\electron" (
    echo [ERROR] Electron dependency not found.
    echo Run: cd frontend ^&^& cmd /c npm install
    exit /b 1
  )
)

call :url_ready "%BACKEND_URL%"
if errorlevel 1 (
  echo Starting backend on http://127.0.0.1:8000 ...
  start "Research-Flow Backend" cmd /k "cd /d "%BACKEND_DIR%" && python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"
) else (
  echo [OK] backend is already running.
)

call :url_ready "%FRONTEND_URL%"
if errorlevel 1 (
  echo Starting frontend on %FRONTEND_URL% ...
  start "Research-Flow Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev -- --host 127.0.0.1 --port 5173"
) else (
  echo [OK] frontend is already running.
)

echo Waiting for services to warm up...
call :wait_for_url "%BACKEND_URL%" 30 "backend"
call :wait_for_url "%FRONTEND_URL%" 45 "frontend"

if "%MODE%"=="browser" (
  echo Opening browser: %FRONTEND_URL%
  start "" "%FRONTEND_URL%"
) else (
  echo Starting Electron desktop shell...
  start "Research-Flow Desktop" cmd /k "cd /d "%FRONTEND_DIR%" && npm run electron:dev"
)

endlocal
exit /b 0

:url_ready
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 '%~1'; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } } catch { exit 1 }"
exit /b %errorlevel%

:wait_for_url
set "URL=%~1"
set "RETRIES=%~2"
set "LABEL=%~3"

for /L %%I in (1,1,%RETRIES%) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 '%URL%'; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } } catch { exit 1 }"
  if not errorlevel 1 (
    echo [OK] %LABEL% is ready.
    exit /b 0
  )
  timeout /t 1 /nobreak >nul
)

echo [WARN] %LABEL% did not respond before timeout: %URL%
exit /b 0

:usage
echo Research-Flow one-click launcher
echo.
echo Usage:
echo   start-dev.bat              Start backend, Vite, and Electron desktop shell.
echo   start-dev.bat --browser    Start backend, Vite, and open the browser UI.
echo   start-dev.bat --help       Show this help.
echo.
echo Notes:
echo   - Existing backend/frontend services on 127.0.0.1:8000 and 127.0.0.1:5173 are reused.
echo   - Electron mode requires frontend dependencies to be installed.
exit /b 0
