# OpenTPS

OpenTPS is a Python application for treatment planning in proton therapy, based on the MCsquare Monte Carlo dose engine.

The OpenTPS application 1.0.0 consists of the packages opentps-core (version 1.0.7) and opentps-gui (version 1.0.5) which are also available separately.

If you are using OpenTPS as part of your research, teaching, or other activities, we would be grateful if you could star the repository and/or cite our work.

If you want to cite OpenTPS, feel free to cite our white paper accessible [here on arxiv](https://arxiv.org/abs/2303.00365) or with the following bibtex reference :

```bibtex
@misc{wuyckens2023opentps,
title={OpenTPS -- Open-source treatment planning system for research in proton therapy},
author={S. Wuyckens and D. Dasnoy and G. Janssens and V. Hamaide and M. Huet and E. Loÿen and G. Rotsart de Hertaing and B. Macq and E. Sterpin and J. A. Lee and K. Souris and S. Deffet},
year={2023},
eprint={2303.00365},
archivePrefix={arXiv},
primaryClass={physics.med-ph}
}
```

# Installing and running OpenTPS as an end user

## Without Anaconda (Linux and Windows)

1. Install Python 3.9.
2. If you don't want to install OpenTPS and its dependencies in your global Python environment: Create a virtual environment and activate it before going to step 3.
3. Install the opentps package with pip:

```
   pip install opentps
```

3. Run opentps in the command line to see the OpenTPS GUI:

```
   opentps
```

## On Windows with Anaconda

1. Install the latest version of Anaconda: https://www.anaconda.com/.
2. In a conda prompt, create a new virtual environment with python 3.9 and activate it:

```
   conda create --name OpenTPS python=3.9
   conda activate OpenTPS
```

3. Install OpenTPS:

```
   pip install opentps
```

4. Start it with:

```
   opentps
```

# Installing and running OpenTPS as a developer

## On Linux

1. Clone the OpenTPS git repository or download the source code.
2. Run the script `install_opentps_linux.sh` to create a virtual environment `OpenTPS_venv` in the _current directory_ (!). This will also install python 3.9 and add it to the path of your bash shell.
3. Run the script `start_opentps_linux.sh` in the directory where the `OpenTPS_venv` was created in step 2 to start the OpenTPS GUI.

## On Windows (without Anaconda)

1. Clone the OpenTPS git repository or download the source code.
2. Install Python 3.9 and add it to the path in your system environment.
3. Run the script `install_opentps_venv_windows.sh` to create a virtual environment `OpenTPS_venv` in the _current directory_ (!).
4. Run the script `start_opentps_venv_windows.sh` in the directory where the `OpenTPS_venv` was created in step 2 to start the OpenTPS GUI.

## On Windows (with Anaconda)

If you have Anaconda installed:

1. Open an Anaconda prompt and execute the `install_opentps_anaconda_windows.bat` script. This will create an environment named `OpenTPS_venv`.
2. To launch the OpenTPS application, run the `start_opentps_anaconda_windows.bat` script.
