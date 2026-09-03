@echo off
chcp 65001 >nul 2>nul
title FJSP Scheduler - Launcher
cd /d "%~dp0"

echo ========================================
echo   FJSP Intelligent Scheduling System
echo ========================================
echo.

REM ===== 1. Detect Python =====
set PYTHON_CMD=
where python >nul 2>nul
if %errorlevel%==0 set PYTHON_CMD=python
if "%PYTHON_CMD%"=="" (
    where py >nul 2>nul
    if %errorlevel%==0 set PYTHON_CMD=py
)
if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ and add it to PATH.
    pause
    exit /b 1
)
echo [1/5] Python found: %PYTHON_CMD%
%PYTHON_CMD% --version

REM ===== 2. Check dependencies =====
echo.
echo [2/5] Checking dependencies...
%PYTHON_CMD% -c "import flask, flask_cors" 2>nul
if errorlevel 1 (
    echo       Installing flask flask-cors...
    %PYTHON_CMD% -m pip install flask flask-cors
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)
echo       Dependencies OK.

REM ===== 3. Check files =====
if not exist "backend\main.py" (
    echo [ERROR] backend\main.py not found!
    pause
    exit /b 1
)
if not exist "frontend\index.html" (
    echo [ERROR] frontend\index.html not found!
    pause
    exit /b 1
)

REM ===== 4. Check ports =====
echo [3/5] Checking ports...
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo [ERROR] Port 8000 is already in use!
    echo Please run close-system script first.
    pause
    exit /b 1
)
netstat -ano | findstr ":5500" | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo [ERROR] Port 5500 is already in use!
    echo Please run close-system script first.
    pause
    exit /b 1
)
echo       Ports 8000 and 5500 are free.

REM ===== 5. Start backend in new window =====
echo [4/5] Starting services...
start "FJSP-Backend" /D "%~dp0backend" cmd /k "%PYTHON_CMD% main.py"

REM Wait for backend port to be listening
echo       Waiting for backend...
set /a WAIT_COUNT=0
:WAIT_BACKEND
ping -n 2 127.0.0.1 >nul
set /a WAIT_COUNT+=1
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul
if not errorlevel 1 goto BACKEND_OK
if %WAIT_COUNT% GEQ 20 (
    echo [WARNING] Backend start timeout. Check FJSP-Backend window.
    goto START_FRONTEND
)
goto WAIT_BACKEND
:BACKEND_OK
echo       Backend OK on port 8000.

REM ===== 6. Start frontend in new window =====
:START_FRONTEND
start "FJSP-Frontend" /D "%~dp0frontend" cmd /k "%PYTHON_CMD% -m http.server 5500 --bind 127.0.0.1"

set /a WAIT_COUNT=0
:WAIT_FRONTEND
ping -n 2 127.0.0.1 >nul
set /a WAIT_COUNT+=1
netstat -ano | findstr ":5500" | findstr "LISTENING" >nul
if not errorlevel 1 goto FRONTEND_OK
if %WAIT_COUNT% GEQ 10 (
    echo [WARNING] Frontend start timeout.
    goto OPEN_BROWSER
)
goto WAIT_FRONTEND
:FRONTEND_OK
echo       Frontend OK on port 5500.

REM ===== 7. Open browser =====
:OPEN_BROWSER
echo [5/5] Opening browser...
ping -n 2 127.0.0.1 >nul
start "" "http://127.0.0.1:5500"

echo.
echo ========================================
echo   System is RUNNING
echo ========================================
echo.
echo   Frontend : http://127.0.0.1:5500
echo   Backend  : http://127.0.0.1:8000
echo   API Check: http://127.0.0.1:8000/api/health
echo.
echo   Two extra windows opened:
echo     FJSP-Backend  - Flask logs
echo     FJSP-Frontend - HTTP logs
echo.
echo   Press ANY KEY to stop ALL services.
echo ========================================
echo.

pause >nul

echo.
echo Stopping all services...

REM Kill by port
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /T /PID %%p >nul 2>nul
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5500" ^| findstr "LISTENING"') do (
    taskkill /F /T /PID %%p >nul 2>nul
)

REM Kill by window title
taskkill /F /FI "WINDOWTITLE eq FJSP-Backend*" >nul 2>nul
taskkill /F /FI "WINDOWTITLE eq FJSP-Frontend*" >nul 2>nul

ping -n 3 127.0.0.1 >nul
echo.
echo ========================================
echo   All services stopped.
echo ========================================
echo.
pause
