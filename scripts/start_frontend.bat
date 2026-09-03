@echo off
chcp 65001 >nul
echo ========================================
echo   FJSP智能调度系统 - 前端启动
echo ========================================
echo.

cd /d "%~dp0.."
cd frontend

echo 前端地址: http://127.0.0.1:5500
echo.
echo 正在启动本地HTTP服务器...
echo 按 Ctrl+C 停止服务
echo.

python -m http.server 5500

pause
