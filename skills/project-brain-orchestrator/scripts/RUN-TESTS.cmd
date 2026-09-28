@echo off
setlocal EnableExtensions
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m unittest -v test_artifact_publisher.py
  exit /b %errorlevel%
)
python -m unittest -v test_artifact_publisher.py
exit /b %errorlevel%
