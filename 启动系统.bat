@echo off
title FJSP Scheduler - Launcher

echo ========================================
echo   FJSP Intelligent Scheduling System
echo ========================================
echo.

REM Switch to script directory
cd /d "%~dp0"

REM Detect Python
set PYTHON_CMD=
where python >nul 2>nul
if %errorlevel%==0 (
    set PYTHON_CMD=python
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set PYTHON_CMD=py
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [OK] Python found: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

REM Check if start.py exists
if not exist "start.py" (
    echo [ERROR] start.py not found in %cd%
    echo.
    pause
    exit /b 1
)

echo [INFO] Starting system...
echo   Backend:  http://127.0.0.1:8000
echo   Frontend: http://127.0.0.1:5500
echo.
echo   Press Ctrl+C to stop all services
echo ========================================
echo.

%PYTHON_CMD% start.py

echo.
echo ========================================
echo   System stopped.
echo ========================================
echo.
pause
