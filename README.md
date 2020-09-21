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
pip3 install --upgrade --user pip
pip3 install --user pydicom
pip3 install --user numpy
pip3 install --user scipy
pip3 install --user matplotlib
pip3 install --user Pillow
pip3 install --user PyQt5==5.14
pip3 install --user pyqtgraph
pip3 install --user tensorflow
pip3 install --user keras
pip3 install --user sparse_dot_mkl
pip3 install --user shutil
pip3 install --user paramiko
```

## Run:

```
python3 main.py
```


