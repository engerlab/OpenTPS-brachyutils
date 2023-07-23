# OpenTPS

Python application for treatment planning in proton therapy, based on the MCsquare Monte Carlo dose engine.

The OpenTPS application 1.0.0 contains the packages opentps-core (version 1.0.7) and opentps-gui (version 1.0.5) which are also available separately.

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
