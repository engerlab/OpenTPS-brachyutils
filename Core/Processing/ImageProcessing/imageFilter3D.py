import numpy as np
import scipy.ndimage
import logging

try:
    import cupy
    import cupyx.scipy.ndimage
except:
    print('cupy not found.')

logger = logging.getLogger(__name__)


def gaussConv(data, sigma, truncate=2.5, mode="reflect"):
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

    if data.size>1e6:
        try:
            return cupy.asnumpy(cupyx.scipy.ndimage.gaussian_filter(cupy.asarray(data), sigma=sigma, truncate=truncate, mode=mode))
        except:
            logger.warning('cupy not used for gaussian smoothing.')

    return scipy.ndimage.gaussian_filter(data, sigma=sigma, truncate=truncate, mode=mode)


def normGaussConv(data, cert, sigma):
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

    data = gaussConv(np.multiply(data, cert), sigma=sigma, mode='constant')
    cert = gaussConv(cert, sigma=sigma, mode='constant')
    z = (cert == 0)
    data[z] = 0.0
    cert[z] = 1.0
    data = np.divide(data, cert)
    return data
