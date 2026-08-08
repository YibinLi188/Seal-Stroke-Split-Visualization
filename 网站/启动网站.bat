@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动拆笔画可视化网站...
start "" /B python server.py --host 127.0.0.1 --port 8766
timeout /t 1 /nobreak >nul
start "" http://127.0.0.1:8766
echo.
echo 网站已打开。关闭此窗口不会停止后台服务；如需停止，请关闭对应的 Python 进程。
pause
