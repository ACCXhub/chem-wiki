@echo off
chcp 65001 >nul
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev\chem-wiki.ps1" -Action Stop
if errorlevel 1 (
  echo.
  echo Chem Wiki 停止失败。请根据上方错误处理后重试。
  pause
  exit /b 1
)
