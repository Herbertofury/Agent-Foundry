@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap.ps1" %*
set "DEVKIT_EXIT=%errorlevel%"
if "%~1"=="" pause
exit /b %DEVKIT_EXIT%
