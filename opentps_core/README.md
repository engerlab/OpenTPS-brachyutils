# opentps-core

Core library of opentps, a Python application for treatment planning in proton therapy, based on the MCsquare Monte Carlo dose engine.


## Installation (Linux):
Requirements are listed in pyproject.toml.
To install all required dependencies:
``` 
poetry install
``` 

Additional system libraries (Ubuntu 19 or more recent):
``` 
sudo apt install libmkl-rt
``` 

Additional system libraries (Ubuntu 18):
``` 
cd /tmp
wget https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
apt-key add GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
sudo sh -c 'echo deb https://apt.repos.intel.com/mkl all main > /etc/apt/sources.list.d/intel-mkl.list'
sudo apt-get update
sudo apt-get install intel-mkl-64bit-2020.1-102
echo 'export LD_LIBRARY_PATH=/opt/intel/mkl/lib/intel64:$LD_LIBRARY_PATH' | sudo tee -a /etc/profile.d/mkl_lib.sh

# adapted from: http://dirk.eddelbuettel.com/blog/2018/04/15/
```

Optional python modules:
``` 
pip3 install --user tensorflow
pip3 install --user keras
pip3 install --user cupy
```

## Installation (Windows):
Note: VTK is only compatible with Python version <= 3.9. Do not use Python 3.10

1) Install anaconda on your Windows computer

2) Open Anaconda Prompt (via the Anaconda application)

3) Create a new Anaconda environment:
``` 
conda create --name OpenTPS python=3.8
``` 

4) Activate the new environment:
``` 
conda activate OpenTPS
``` 

5) Install the following python modules:
Python modules:
``` 
pip3 install --upgrade --user pip
pip3 install --user pydicom
pip3 install --user numpy
pip3 install --user scipy
pip3 install --user matplotlib
pip3 install --user Pillow
pip3 install --user sparse_dot_mkl
pip3 install --user SimpleITK
pip3 install --user pandas
pip3
```

Optional python modules:
``` 
pip3 install --user tensorflow
pip3 install --user keras
pip3 install --user cupy
```
