# OpenTPS

Python application for treatment planning in proton therapy, based on the MCsquare Monte Carlo dose engine.

OpenTPS consists of two packages: [opentps-core](./opentps_core/README.md) and [opent-gui](./opentps_gui/README.md) which share a common namespace opentps.

If you are using OpenTPS as part of your research, teaching, or other activities, we would be grateful if you could star the repository and/or cite our work.

If you want to cite OpenTPS, feel free to cite our white paper accessible [here](https://arxiv.org/abs/2303.00365) or with the following bibtex reference :
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

## Installation and start OpenTPS for windows

1. Install the latest version of Anaconda. Download the latest version from https://www.anaconda.com/.
2. Open the 'Anaconda Command Prompt'. You can find it in the Windows Start menu -> Anaconda3 (64-bit).
3. At the Anaconda command prompt: Go to your project directory, where the files 'install_opentps_windows.bat' and 'start_opentps_windows.bat' are located.
4. The first is to run install_opentps_windows.bat if the 'OpenTPS' environment does not exist in Anaconda.
5. Once created, you can start the GUI version of opentps by running the script start_opentps_windows.bat
