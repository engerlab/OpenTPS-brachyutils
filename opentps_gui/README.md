# opentps-gui

GUI of opentps, a Python application for treatment planning in proton therapy, based on the MCsquare Monte Carlo dose engine.

## Installation (Linux):

Requirements are listed in pyproject.toml.
To install all required dependencies:

```
poetry install
```

## Installation (Windows):


1. Install anaconda on your Windows computer

2. Open Anaconda Prompt (via the Anaconda application)

3. Create a new Anaconda environment:

```
conda create --name OpenTPS python=3.11
```

4. Activate the new environment:

```
conda activate OpenTPS
```

5. Install the following python modules:
   Python modules:

```
pip3 install --upgrade pip
pip3 install pydicom
pip3 install numpy>=1.24.0
pip3 install scipy
pip3 install matplotlib
pip3 install Pillow
pip3 install PyQt5==5.15.7
pip3 install pyqtgraph
pip3 install sparse_dot_mkl
pip3 install vtk==9.2.6
pip3 install SimpleITK
pip3 install pandas
pip3 install scikit-image
pip3 install pymedphys==0.40.0
pip3
```

Optional python modules:

```
pip3 install tensorflow
pip3 install keras
pip3 install cupy
```

## Run:

```
python3 main.py
```

or from a python script:

```python
import opentps.gui as opentps_gui
opentps_gui.run()
```
