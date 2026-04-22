@echo off
setlocal

cd /d "%~dp0"

set "NGROK_EXE=%NGROK_PATH%"

if not defined NGROK_EXE if exist "%~dp0ngrok.exe" set "NGROK_EXE=%~dp0ngrok.exe"
if not defined NGROK_EXE if exist "C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe" set "NGROK_EXE=C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe"
if not defined NGROK_EXE if exist "C:\ngrok\ngrok.exe" set "NGROK_EXE=C:\ngrok\ngrok.exe"

if not defined NGROK_EXE (
    echo ngrok.exe was not found.
    echo.
    echo Set NGROK_PATH or place ngrok.exe in one of these locations:
    echo   %~dp0ngrok.exe
    echo   C:\Users\Admin\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe
    echo   C:\ngrok\ngrok.exe
    pause
    exit /b 1
)

echo Starting ngrok for BUFIA on http://127.0.0.1:8000
echo Using: %NGROK_EXE%
echo If you have not added your ngrok authtoken yet, run:
echo "%NGROK_EXE%" config add-authtoken YOUR_TOKEN
"%NGROK_EXE%" http 8000
