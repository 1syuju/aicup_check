# Gunicorn 配置檔案
# 適用於生產環境部署

import os

# 綁定地址和端口
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"

# 工作進程數量
workers = 2

# 工作進程類型
worker_class = "sync"

# 每個工作進程的線程數
threads = 2

# 最大請求數（防止記憶體洩漏）
max_requests = 1000
max_requests_jitter = 50

# 超時設定
timeout = 30
keepalive = 2

# 日誌設定
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"

# 進程名稱
proc_name = "aicup-checkin"

# 預載入應用程式
preload_app = True

# 用戶和群組（在 Linux 上使用）
# user = "www-data"
# group = "www-data"

# 安全設定
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
