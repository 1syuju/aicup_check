# 報到系統使用
1. ivanti 連接 vpn
2. 用ssh 進入 aicup_check@140.115.51.156


```
aicup_check@lupin:~$ python3 -m http.server 8080
```
在app.py的資料夾底下輸入
```
scp -r templates static aicup_check@140.115.51.156:~/
```
這邊不確定要不要
```
aicup_check@lupin:~$ python3 -m venv venv
aicup_check@lupin:~$ source venv/bin/activate
aicup_check@lupin:~$ pip install flask flask_sqlalchemy flask_cors pandas openpyxl
aicup_check@lupin:~$ pip install flask flask_sqlalchemy flask_cors
aicup_check@lupin:~$ python3 app.py
```
啟動
```
aicup_check@lupin:~$ source ~/venv/bin/activate
aicup_check@lupin:~$ export PORT=8080
aicup_check@lupin:~$ python3 ~/app.py
```
