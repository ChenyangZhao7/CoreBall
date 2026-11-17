@echo off
chcp 65001 >nul
set "BLENDER=C:\Users\21165\Apps\blender-4.5.16\blender-4.5.16-windows-x64\blender.exe"
set "HERE=%~dp0"

if not exist "%BLENDER%" (
  echo Blender not found: %BLENDER%
  pause
  exit /b 1
)

echo.
echo   1  核心球
echo   2  工位 + 五线
echo   3  吊点总成
echo   4  绞盘总成
echo.
set /p PICK=选一个 (1-4):

if "%PICK%"=="1" set "SCRIPT=build_ball.py" & set "OUT=out\ball"
if "%PICK%"=="2" set "SCRIPT=build_desk_rig.py" & set "OUT=out\rig"
if "%PICK%"=="3" set "SCRIPT=build_hub.py" & set "OUT=out\hub"
if "%PICK%"=="4" set "SCRIPT=build_winch.py" & set "OUT=out\winch"

if not defined SCRIPT exit /b 1

echo Rebuilding %SCRIPT% ...
"%BLENDER%" --background --python "%HERE%%SCRIPT%" -- --out "%HERE%%OUT%" --render

echo.
echo Done. Output in %HERE%%OUT%
pause
