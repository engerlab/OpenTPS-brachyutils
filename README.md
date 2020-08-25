# Open-MCsquare Python interface

Python interface to convert Dicom data and run MCsquare simulations

## Installation:

system libraries (Ubuntu 19 or more recent):
``` 
sudo apt install libmkl-rt
``` 

system libraries (Ubuntu 18):
``` 
cd /tmp
wget https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
apt-key add GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
sudo sh -c 'echo deb https://apt.repos.intel.com/mkl all main > /etc/apt/sources.list.d/intel-mkl.list'
sudo apt-get update
sudo apt-get install intel-mkl-64bit-2020.1-102
sudo echo 'export LD_LIBRARY_PATH=/opt/intel/mkl/lib/intel64:$LD_LIBRARY_PATH' > /etc/profile.d/mkl_lib.sh

# adapted from: http://dirk.eddelbuettel.com/blog/2018/04/15/
``` 

Python modules:
``` 
pip3 install --upgrade -U pip
pip3 install -U pydicom
pip3 install -U numpy
pip3 install -U scipy
pip3 install -U matplotlib
pip3 install -U Pillow
pip3 install -U PyQt5==5.14
pip3 install -U pyqtgraph
pip3 install -U tensorflow
pip3 install -U keras
pip3 install -U sparse_dot_mkl
```

## Run:

```
python3 main.py
```


