# AI CUP 2025 報到系統

## 系統概述

這是一個基於 Flask 和 SQLite 的活動報到系統，支援：
- 參加者自助報到（只需輸入姓名）
- 管理員後台管理
- Excel 資料匯入/匯出

## 系統需求

- Python 3.8+
- 現代瀏覽器（支援 JavaScript）

## 快速開始

### 1. 安裝依賴
```bash
pip install -r requirements.txt
```

### 2. 啟動系統
```bash
# Windows
run.bat

# 或直接執行
python app.py
```

### 3. 存取系統
- **首頁**: http://localhost:5000/
- **報到介面**: http://localhost:5000/checkin
- **管理後台**: http://localhost:5000/admin



## 功能特色

### 1. 自動資料匯入
- 系統啟動時自動從 Excel 檔案匯入參加者名單
- 支援手動重新載入固定名單

### 2. 多種報到方式
- **手動報到**: 管理員在後台手動標記
- **自助報到**: 參加者輸入姓名報到

### 3. 資料匯出
- 支援 Excel 格式匯出
- 包含完整的報到狀態和時間資訊

## 資料庫結構

### 主要表格

#### participants（參加者）
- `id`: 主鍵
- `name`: 姓名
- `email`: 電子郵件
- `phone`: 電話
- `organization`: 組織/學校
- `created_at`: 建立時間

#### checkin_logs（報到記錄）
- `id`: 主鍵
- `participant_id`: 參加者 ID（外鍵）
- `checkin_time`: 報到時間
- `checkin_method`: 報到方式（manual, qr, mobile）

## 故障排除

### 手機無法連接到電腦

1. **檢查防火牆設定**
   - Windows Defender → 防火牆與網路保護
   - 允許 Python 通過防火牆

2. **確認網路設定**
   - 手機和電腦必須在同一個 WiFi 網路
   - 檢查路由器設定

3. **檢查應用程式狀態**
   - 確認 Flask 正在運行
   - 查看控制台是否有錯誤訊息

### 掃描 QR Code 後無法開啟

1. **檢查 QR Code 內容**
   - 確認 URL 是否包含正確的 IP 地址

2. **手動測試 URL**
   - 在手機瀏覽器中手動輸入 QR Code 的 URL

## 完整指南

詳細的手機掃描簽到指南請參考：`手機掃描簽到完整指南.md`

## 版本資訊

- **版本**: 1.0.0
- **Python**: 3.8+
- **Flask**: 3.0.0
- **資料庫**: SQLite
- **最後更新**: 2025年1月 