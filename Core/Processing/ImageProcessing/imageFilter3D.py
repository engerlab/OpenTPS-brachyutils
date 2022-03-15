import numpy as np
import scipy.ndimage
import logging


logger = logging.getLogger(__name__)


def gaussConv(data, sigma):
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

    return scipy.ndimage.gaussian_filter(data, sigma=sigma)


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

    data = scipy.ndimage.gaussian_filter(np.multiply(data, cert), sigma=sigma, truncate=2.5, mode='constant')
    cert = scipy.ndimage.gaussian_filter(cert, sigma=sigma, truncate=2.5, mode='constant')
    z = (cert == 0)
    data[z] = 0.0
    cert[z] = 1.0
    data = np.divide(data, cert)
    return data