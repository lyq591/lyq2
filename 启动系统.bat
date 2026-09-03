@echo off
chcp 65001 >nul
title FJSP智能调度系统 - 一键启动
cd /d "%~dp0"
python start.py
if errorlevel 1 (
    echo.
    echo 启动失败，请检查Python是否已安装。
    pause
)
