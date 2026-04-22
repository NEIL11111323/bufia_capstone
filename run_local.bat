@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Virtual environment Python was not found at:
    echo %PYTHON_EXE%
    pause
    exit /b 1
)

echo Starting BUFIA locally on http://0.0.0.0:8000
echo Use your PC's Wi-Fi IP on another device, for example: http://192.168.1.8:8000
echo Using stable no-reload mode for local debugging.
"%PYTHON_EXE%" -u manage.py runserver 0.0.0.0:8000 --noreload
