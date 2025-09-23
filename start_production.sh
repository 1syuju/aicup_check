#!/bin/bash

# AI CUP 2025 報到系統 - 生產環境啟動腳本
# 使用 Gunicorn 提供更好的效能和穩定性

echo "🚀 啟動 AI CUP 2025 報到系統（生產模式）..."

# 檢查 Gunicorn 是否安裝
if ! command -v gunicorn &> /dev/null; then
    echo "❌ Gunicorn 未安裝，正在安裝..."
    pip3 install gunicorn
fi

# 建立日誌目錄
mkdir -p logs

# 設定環境變數
export FLASK_APP=app.py
export FLASK_ENV=production

# 啟動 Gunicorn
echo "🌐 啟動 Gunicorn 伺服器..."
gunicorn -c gunicorn.conf.py app:app

echo "✅ 應用程式已啟動"
echo "🌐 訪問網址: http://your-server-ip:5000"
