@echo off
chcp 65001 >nul
echo ========================================
echo   FJSP智能调度系统 - 后端服务启动
echo ========================================
echo.

cd /d "%~dp0.."
cd backend

echo 检查Python环境...
python --version
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo.
echo 检查依赖...
python -c "import fastapi; import uvicorn" 2>nul
if errorlevel 1 (
    echo 安装依赖中...
    pip install -r requirements.txt
)

echo.
echo 启动后端服务...
echo API地址: http://127.0.0.1:8000
echo API文档: http://127.0.0.1:8000/docs
echo 按 Ctrl+C 停止服务
echo.

python main.py

pause
