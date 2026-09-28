@echo off
setlocal EnableExtensions
set "SCRIPT=%~dp0artifact_publisher.py"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 "%SCRIPT%" %*
  exit /b %errorlevel%
)
where python >nul 2>&1
if %errorlevel%==0 (
  python "%SCRIPT%" %*
  exit /b %errorlevel%
)
echo ERROR: Python 3 was not found. Install Python 3 and try again. 1>&2
exit /b 9009
