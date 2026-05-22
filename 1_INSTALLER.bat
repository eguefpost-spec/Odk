@echo off
cd /d "%~dp0"
echo Installation en cours...
py -m pip install -r requirements.txt
py -m playwright install chromium
echo.
echo Installation terminee !
pause
