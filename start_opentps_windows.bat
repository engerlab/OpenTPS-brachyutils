@echo off

if not defined CONDA_PREFIX (
    echo No anaconda prompt detected.
    echo Run this script in an anaconda prompt.
    exit /b
)

call conda activate OpenTPS

set PYTHONPATH=%~dp0opentps_core;%~dp0opentps_gui

python %~dp0opentps_gui\opentps\gui\main.py