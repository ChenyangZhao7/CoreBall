@echo off
set "B=C:\Users\21165\Apps\blender-4.5.16\blender-4.5.16-windows-x64\blender.exe"
start "" "%B%" "%~dp0out\cmd\coreball_command.blend" --python "%~dp0cmd_runtime.py"
