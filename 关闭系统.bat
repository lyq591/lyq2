@echo off
title FJSP Scheduler - Stop
cd /d "%~dp0"

echo ========================================
echo   FJSP Scheduler - Stop All Services
echo ========================================
echo.

set STOPPED=0

REM --- Method 1: Stop by PID file ---
if exist ".running_pids" (
    echo [Method 1] Stopping processes by PID file...
    for /f "tokens=1,2 delims==" %%a in (.running_pids) do (
        if "%%a"=="backend" (
            echo   Killing backend PID %%b...
            taskkill /F /T /PID %%b >nul 2>&1 && echo   OK: backend stopped
        )
        if "%%a"=="frontend" (
            echo   Killing frontend PID %%b...
            taskkill /F /T /PID %%b >nul 2>&1 && echo   OK: frontend stopped
        )
    )
    del /q ".running_pids" >nul 2>&1
    set STOPPED=1
)

REM --- Method 2: Stop by command line match ---
echo.
echo [Method 2] Scanning for FJSP-related python processes...

REM Kill backend (python main.py in backend dir)
for /f "tokens=2 delims=," %%p in ('wmic process where "commandline like '%%main.py%%' and commandline like '%%backend%%'" get processid /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    echo   Killing backend process PID %%p...
    taskkill /F /T /PID %%p >nul 2>&1
    set STOPPED=1
)

REM Kill frontend (python -m http.server in frontend dir)
for /f "tokens=2 delims=," %%p in ('wmic process where "commandline like '%%http.server%%' and commandline like '%%frontend%%'" get processid /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    echo   Killing frontend process PID %%p...
    taskkill /F /T /PID %%p >nul 2>&1
    set STOPPED=1
)

REM Kill start.py launcher itself
for /f "tokens=2 delims=," %%p in ('wmic process where "commandline like '%%start.py%%'" get processid /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    echo   Killing launcher process PID %%p...
    taskkill /F /T /PID %%p >nul 2>&1
    set STOPPED=1
)

REM --- Method 3: Kill by port (fallback) ---
echo.
echo [Method 3] Checking ports...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo   Port 8000 occupied by PID %%p, killing...
    taskkill /F /T /PID %%p >nul 2>&1
    set STOPPED=1
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5500" ^| findstr "LISTENING"') do (
    echo   Port 5500 occupied by PID %%p, killing...
    taskkill /F /T /PID %%p >nul 2>&1
    set STOPPED=1
)

REM --- Verify ---
echo.
echo ========================================
echo   Verification
echo ========================================
timeout /t 2 /nobreak >nul

set PORT8000=free
set PORT5500=free
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul && set PORT8000=occupied
netstat -ano | findstr ":5500" | findstr "LISTENING" >nul && set PORT5500=occupied

echo   Backend  port 8000: %PORT8000%
echo   Frontend port 5500: %PORT5500%

REM Clean up PID file if still exists
if exist ".running_pids" del /q ".running_pids" >nul 2>&1

echo.
if "%PORT8000%"=="free" if "%PORT5500%"=="free" (
    echo   [OK] All services stopped successfully.
) else (
    echo   [WARNING] Some ports may still be occupied.
    echo   You can run this script again, or restart your computer.
)
echo ========================================
echo.
pause
