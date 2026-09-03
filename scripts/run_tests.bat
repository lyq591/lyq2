@echo off
chcp 65001 >nul
echo ========================================
echo   FJSP智能调度系统 - 自动化测试
echo ========================================
echo.

cd /d "%~dp0.."

python tests\run_tests.py

echo.
pause
