@echo off
chcp 65001 >nul
title PMFY 全局翻译 (控制台日志调试模式)

:: 切换到当前脚本所在目录
cd /d "%~dp0"

:: 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未检测到 Python 虚拟环境 .venv！
    pause
    exit /b 1
)

echo ============================================================
echo   PMFY 全局翻译 - 调试控制台模式
echo   按 Ctrl+C 可在此控制台窗口退出程序
echo ============================================================
echo.

:: 使用 python.exe 启动并保持控制台前台运行
".venv\Scripts\python.exe" "run.py"

pause
