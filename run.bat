@echo off
echo AI CUP 2025 報到系統 - SQLite 版本
echo ====================================
echo.

echo 檢查 Python 環境...
python --version
if %errorlevel% neq 0 (
    echo 錯誤: 找不到 Python，請先安裝 Python 3.8+
    pause
    exit /b 1
)

echo.
echo 安裝/更新 Python 依賴套件...
pip install -r requirements.txt

echo.
echo 啟動 Flask 應用程式...
echo 系統將在以下地址運行：
echo - 本機: http://127.0.0.1:5000
echo - 區域網路: http://[您的IP地址]:5000
echo.
echo 請確保手機和電腦在同一個 WiFi 網路中
echo.
python app.py

pause 