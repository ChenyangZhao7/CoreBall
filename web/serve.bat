@echo off
chcp 65001 >nul
cd /d "%~dp0.."
start "" /min cmd /c "python -m http.server 8000"
timeout /t 1 >nul
start "" "http://localhost:8000/web/viewer.html"
echo CoreBall viewer: http://localhost:8000/web/viewer.html
echo 关闭本窗口不会停掉服务；要停服务请关掉最小化的 python 窗口。
pause
