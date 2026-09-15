@echo off
setlocal
title Safe ADB Bridge
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-SafeAdbBridge.ps1" -AdbPath "%~dp0adb.exe" -LinuxHost "user@<server-ip>" -RemotePort 15038
if errorlevel 1 (
  echo.
  echo Bridge failed. Review the error above.
  pause
)
