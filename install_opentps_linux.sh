#!/bin/bash

ENV_PATH="$PWD/OpenTPS_venv"

# Directory that contains this script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Check if the destination folder already exists
if [ -d "$ENV_PATH" ]; then
    echo "The directory $ENV_PATH already exists. If you want rerun this script, first remove this directory."
    exit 1;
fi

echo "This script will install system libraries and tools that you will need to work with OpenTPS. At several points in the installation process apt will ask you to confirm the installation and updates of packages. The script will also create a virtual python environment in the CURRENT directory named $ENV_PATH that will be used to install the python dependencies of OpenTPS."

read -p "Do you want to proceed? (y/n) " CONT
if [ "$CONT" = "y" ]; then
  echo "Installation continues";
else
  echo "Installation canceled"
  exit;
fi

# Install Python 3.9
sudo apt update && sudo apt upgrade
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.9

# Add Python path to system environment
echo 'export PATH="/usr/bin/python3.9:$PATH"' >> ~/.bashrc
source ~/.bashrc
echo "Python 3.9 installed and path added to system environment."

# Check if Python 3.9 is installed 
if ! command -v python3.9 &>/dev/null; then
    echo "Python 3.9 is not installed. Please install it and try again."
    exit 1
fi

# Some tools we need later
sudo apt-get install curl wget

# Additional system libraries (Ubuntu 19 or more recent)
sudo apt install libmkl-rt libxcb-xinerama0

cd /tmp
wget https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
apt-key add GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
sudo sh -c 'echo deb https://apt.repos.intel.com/mkl all main > /etc/apt/sources.list.d/intel-mkl.list'
sudo apt-get install intel-mkl-64bit-2020.1-102
echo 'export LD_LIBRARY_PATH=/opt/intel/mkl/lib/intel64:$LD_LIBRARY_PATH' | sudo tee -a /etc/profile.d/mkl_lib.sh

# install poetry
# curl -sSL https://install.python-poetry.org | python3 -

# Create a virtual environment
sudo apt-get install python3.9-venv
python3.9 -m venv $ENV_PATH

# Activate the virtual environment
source $ENV_PATH/bin/activate
echo "Virtual environment 'OpenTPS/venv' created"

# Upgrade pip
pip3 install --upgrade pip

# Install required Python packages
pip3 install pydicom numpy scipy matplotlib Pillow PyQt5==5.15.7 pyqtgraph sparse_dot_mkl vtk SimpleITK pandas scikit-image tensorflow keras
# pip3 install cupy

echo
echo "Installation complete. You can start opentps with"
echo "   bash $SCRIPT_DIR/start_opentps_linux.sh"
echo "You have to be in the directory where you ran the install script."