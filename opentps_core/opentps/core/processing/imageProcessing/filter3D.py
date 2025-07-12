import numpy as np
import scipy.ndimage
import logging

logger = logging.getLogger(__name__)

from opentps.core.processing.imageProcessing import cupyImageProcessing
def gaussConv(data, sigma, truncate=2.5, mode="reflect", tryGPU=True):
    """Apply Gaussian convolution on input data.

    Parameters
    ----------
    data : numpy array
        data to be convolved.
    sigma : double
        standard deviation of the Gaussian.

    Returns
    -------
    numpy array
        Convolved data.
    """

    if data.size > 1e6 and tryGPU:
        try:
            return cupyImageProcessing.gaussianSmoothing(data, sigma=sigma, truncate=truncate, mode=mode)
        except:
            logger.warning('cupy not used for gaussian smoothing.')

    return scipy.ndimage.gaussian_filter(data, sigma=sigma, truncate=truncate, mode=mode)


def normGaussConv(data, cert, sigma, tryGPU=True):
    """Apply normalized Gaussian convolution on input data.

    Parameters
    ----------
    data : numpy array
        data to be convolved.
    cert : numpy array
        certainty map associated to the data.
    sigma : double
        standard deviation of the Gaussian.

    Returns
    -------
    numpy array
        Convolved data.
    """

    data = gaussConv(np.multiply(data, cert), sigma=sigma, mode='constant', tryGPU=tryGPU)
    cert = gaussConv(cert, sigma=sigma, mode='constant', tryGPU=tryGPU)
    z = (cert == 0)
    data[z] = 0.0
    cert[z] = 1.0
    data = np.divide(data, cert)
    return data
