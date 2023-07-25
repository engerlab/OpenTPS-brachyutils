# OpenTPS

Python application for treatment planning in proton therapy, based on the MCsquare Monte Carlo dose engine.

The OpenTPS application 1.0.0 contains the packages opentps-core (version 1.0.7) and opentps-gui (version 1.0.5) which are also available separately.

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

## Installating and starting OpenTPS

1. Install the latest version of Anaconda. Download the latest version from https://www.anaconda.com/.
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
