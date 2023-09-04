@echo off

set ENV_PATH=%cd%\OpenTPS_venv

:: Get the directory that contains this script
for %%I in ("%~dp0.") do set "SCRIPT_DIR=%%~fI"

:: Check if the destination folder already exists
if exist "ENV_PATH" (
    echo The directory %ENV_PATH% already exists. If you want to rerun this script, first remove this directory.
    exit /b 1
)

echo This script will install system libraries and tools that you will need to work with OpenTPS. At several points in the installation process, the script will also create a virtual python environment in the CURRENT directory named %ENV_PATH% that will be used to install the python dependencies of OpenTPS.

echo Create the Python virtual environment. You need to install python version 3.9.13 on your PC and set the python path in the system environment.

REM Check if Python 3.9 is installed
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "python_version=%%i"
echo Installed Python Version: %python_version%

:: Create a virtual environment using 'venv'
if not exist "%ENV_PATH%" (
    echo Creating virtual environment at %ENV_PATH%
    :: Make sure to adjust the Python executable path if needed
    call python -m venv %ENV_PATH%
)

REM Activate the virtual environment
call %ENV_PATH%\Scripts\activate
echo Virtual environment 'OpenTPS_venv' created

REM Checke the virtual environment is activated
if defined ENV_PATH (
    echo Virtual environment is activated.
    echo Virtual environment path: %VIRTUAL_ENV%
) else (
    echo No virtual environment is activated.
)

REM Upgrade pip
python -m pip install --upgrade pip

:: Install required Python packages
pip install pydicom
pip install numpy
pip install scipy
pip install matplotlib
pip install Pillow
pip install PyQt5==5.15.7
pip install pyqtgraph
pip install sparse_dot_mkl
pip install vtk
pip install SimpleITK
pip install pandas
pip install scikit-image
pip install tensorflow
pip install keras
REM pip3 install cupy

echo All packages installed successfully.

echo Installation complete. You can start opentps with
echo    start_opentps_venv_windows.bat
echo You have to be in the directory where you ran the install script.
