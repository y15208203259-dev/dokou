@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist "data" (
  echo 还没有 data 目录，先运行一次 渡口.exe 再备份。
  pause
  exit /b
)
set stamp=%date:~0,4%%date:~5,2%%date:~8,2%-%time:~0,2%%time:~3,2%
set stamp=%stamp: =0%
if not exist "backups" md "backups"
robocopy "data" "backups\data-%stamp%" /E /NFL /NDL /NJH /NJS /XD "data\window-profile" >nul
if errorlevel 8 (
  echo 备份失败：可能有文件被占用，先关闭渡口再试。
) else (
  echo 已备份到 backups\data-%stamp%
)
pause
