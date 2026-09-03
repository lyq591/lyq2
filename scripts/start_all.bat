@echo off
chcp 65001 >nul
echo ========================================
echo   FJSP智能调度系统 - 一键启动
echo ========================================
echo.

cd /d "%~dp0.."

echo [1/3] 启动后端服务...
start "FJSP后端服务" cmd /k "cd /d %~dp0..\backend && python main.py"

timeout /t 3 /nobreak >nul

echo [2/3] 启动前端服务...
start "FJSP前端服务" cmd /k "cd /d %~dp0..\frontend && python -m http.server 5500"

timeout /t 2 /nobreak >nul

echo [3/3] 打开浏览器...
start http://127.0.0.1:5500

echo.
echo ========================================
echo   系统启动完成!
echo   前端: http://127.0.0.1:5500
echo   后端API: http://127.0.0.1:8000
echo   API文档: http://127.0.0.1:8000/docs
echo ========================================
echo.
pause
