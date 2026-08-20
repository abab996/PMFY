@echo off
chcp 65001 >nul
title PMFY 全局翻译启动程序

:: 切换到当前脚本所在目录
cd /d "%~dp0"

:: 检查虚拟环境是否存在
if not exist ".venv\Scripts\pythonw.exe" (
    echo [错误] 未检测到 Python 虚拟环境 .venv！
    echo 请确认是否已在项目根目录下完成环境安装。
    pause
    exit /b 1
)

:: 使用 pythonw 静默启动（无黑框后台运行，托盘常驻）
echo 正在启动 PMFY 全局翻译软件...
start "" ".venv\Scripts\pythonw.exe" "run.py"

exit
