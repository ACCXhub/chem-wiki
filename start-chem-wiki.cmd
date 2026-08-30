@echo off
chcp 65001 >nul
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev\chem-wiki.ps1" -Action Start
if errorlevel 1 (
  echo.
  echo Chem Wiki 启动失败。请根据上方错误处理后重试。
  pause
  exit /b 1
)
