@echo off
chcp 65001 >nul
set "BLENDER=C:\Users\21165\Apps\blender-4.5.16\blender-4.5.16-windows-x64\blender.exe"
set "HERE=%~dp0"

echo.
echo   1  核心球
echo   2  工位 + 五线
echo   3  吊点总成
echo   4  绞盘总成
echo.
set /p PICK=打开哪个 .blend (1-4):

if "%PICK%"=="1" set "BLEND=%HERE%out\ball\coreball_ball.blend"
if "%PICK%"=="2" set "BLEND=%HERE%out\rig\coreball_rig.blend"
if "%PICK%"=="3" set "BLEND=%HERE%out\hub\coreball_hub.blend"
if "%PICK%"=="4" set "BLEND=%HERE%out\winch\coreball_winch.blend"

if not defined BLEND exit /b 1
if not exist "%BLEND%" (
  echo 还没生成，先跑一遍 重建.bat
  pause
  exit /b 1
)

start "" "%BLENDER%" "%BLEND%"
