@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%"
set "FRONTEND_DIR=%ROOT%frontend"
set "FRONTEND_URL=http://127.0.0.1:5173"

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

echo Starting backend on http://127.0.0.1:8000 ...
start "Research-Flow Backend" cmd /k "cd /d "%BACKEND_DIR%" && python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

echo Starting frontend on %FRONTEND_URL% ...
start "Research-Flow Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev -- --host 127.0.0.1 --port 5173"

echo Waiting for frontend to warm up...
timeout /t 4 /nobreak >nul

echo Opening browser: %FRONTEND_URL%
start "" "%FRONTEND_URL%"

endlocal
