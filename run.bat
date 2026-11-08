@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo 未检测到 Python。两种解决办法：
    echo   1. 到 Releases 页面下载免安装版：双击即用
    echo   2. 安装 Python 并勾选 "Add Python to PATH"：https://www.python.org/downloads/
    pause
    exit /b 1
)
echo DS-160 隐私脱敏工具（完全本地运行，无需联网）
echo 把要脱敏的 PDF/截图放到本文件夹，按任意键开始...
pause >nul
python -u ds160_redact.py
pause
