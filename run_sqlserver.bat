@echo off
echo AI CUP 2025 報到系統 - SQL Server 版本
echo ========================================
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
echo 檢查 ODBC Driver...
echo 請確保已安裝 Microsoft ODBC Driver 17 for SQL Server
echo 下載網址: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

echo.
echo 檢查環境設定...
if not exist .env (
    echo 警告: 找不到 .env 檔案
    echo 請複製 config.env 為 .env 並設定資料庫連線
    echo.
    copy config.env .env
    echo 已複製 config.env 為 .env，請編輯 .env 檔案設定資料庫連線
    echo.
    pause
)

echo.
echo 啟動 Flask 應用程式...
echo 請確保 SQL Server 服務正在運行
echo 請確保已執行 sql_server_setup.sql 建立資料庫
echo.
python app.py

pause
