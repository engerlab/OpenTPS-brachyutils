import numpy as np
import math
import logging
logger = logging.getLogger(__name__)

try:
    import tomopy
except:
    logger.warning("Module tomopy not installed")
    pass

def forwardProjectionTomopy(ct, angleInRad, nCores=1):
    """
    Forward project a CT volume using Tomopy

    Parameters
    ----------
    ct : ndarray
        CT volume
    angleInRad : ndarray
        Projection angles in radians

    Returns
    -------
    drrImage : ndarray
        Digital reconstructed radiograph
    """
    drrImage = tomopy.project(ct, angleInRad, ncore=nCores)[0]
    # drrImage = tomopy.sim.project.add_gaussian(drrImage, mean=0, std=1)
    return drrImage