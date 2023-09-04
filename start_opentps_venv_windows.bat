@echo off

set ENV_PATH=%cd%\OpenTPS_venv

REM Get the directory containing this script
for %%i in ("%~dp0.") do set "SCRIPT_DIR=%%~fi"

REM Check if the virtual environment exists
if exist "%ENV_PATH%\Scripts\activate.bat" (
    echo %ENV_PATH% virtual environment found.
) else (
    echo We couldn't find the activation command for the virtual environment %ENV_PATH%. Did you run the install script and are you in the directory where the virtual environment directory %ENV_NAME% was created?
    exit
)

REM Activate the virtual environment
call %ENV_PATH%\Scripts\activate
echo Virtual environment 'OpenTPS_venv' activated


REM Run main.py
set "PYTHONPATH=%~dp0opentps_core;%~dp0opentps_gui"

python "%~dp0opentps_gui\opentps\gui\main.py"
