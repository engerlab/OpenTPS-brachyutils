import numpy as np
import math
from scipy.ndimage import morphology
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import copy
import logging
logger = logging.getLogger(__name__)

from opentps.core.processing.imageProcessing import sitkImageProcessing, cupyImageProcessing

def getMaskVolume(mask, inVoxels=False):
    volumeInvoxels = np.count_nonzero(mask.imageArray > 0)
    if inVoxels:
        return volumeInvoxels
    else:
        volumeInMMCube = volumeInvoxels * mask.spacing[0] * mask.spacing[1] * mask.spacing[2]
        return volumeInMMCube

def buildStructElem(radius):

    if type(radius) == float or type(radius) == int:
        radius = np.array([radius, radius, radius])
    diameter = np.ceil(radius).astype(int) * 2 + 1
    struct = np.zeros(tuple(diameter)).astype(bool)

    ellipsoidRadius = copy.copy(radius)
    for dimIdx in range(len(ellipsoidRadius)):
        if ellipsoidRadius[dimIdx] == 0:
            ellipsoidRadius[dimIdx] = 1

    for i in range(diameter[0]):
        for j in range(diameter[1]):
            for k in range(diameter[2]):
                y = i - math.floor(diameter[0] / 2)
                x = j - math.floor(diameter[1] / 2)
                z = k - math.floor(diameter[2] / 2)
                # generate ellipsoid structuring element
                if (y ** 2 / ellipsoidRadius[0] ** 2 + x ** 2 / ellipsoidRadius[1] ** 2 + z ** 2 / ellipsoidRadius[2] ** 2 <= 1):
                    struct[i, j, k] = True

    # testEllipsoid = skimage.draw.ellipsoid(5, 1, 7, levelset=False)

    # ## to visualize the used structural element
    # fig = plt.figure(figsize=(8, 8))
    # ax = fig.add_subplot(1, 1, 1, projection=Axes3D.name)
    # ax.voxels(struct)
    # plt.show()

    return struct

def dilateMask(mask, radius=1.0, struct=None, inPlace=True, tryGPU=True):
    """
    Dilates the binary mask image using either a 3D ellipsoid structuring element build from radius,
    or a given structural element (struct).

    Args:
    - radius: float or 3-tuple of floats, the radii in mm of the ellipsoid in each dimension. Default is 1.0.
    - filt: np.array of bools, the structuring element to use for dilation. If given, the radius is not used. Default is None.
    - tryGPU: bool, whether to attempt to use the GPU for dilation using the CuPy library. Default is False.

    Returns:
    - None if inPlace = True, a new dilated mask if inPlace = False
    """

    if not inPlace:
        maskCopy = mask.copy()
    else:
        maskCopy = mask

    if struct is None:
        struct = buildStructElem(radius / np.array(maskCopy.spacing))

    if maskCopy.imageArray.size > 1e5 and tryGPU:
        try:
            logger.info('Using cupy to dilate mask')
            cupyImageProcessing.dilateMask(maskCopy, radius=radius, struct=struct)
        except:
            logger.warning('Cupy not working to dilate mask.')
            tryGPU = False
    else:
        tryGPU = False

    if not tryGPU:
        try:
            logger.info('Using SITK to dilate mask.')
            radiusSITK = np.round(radius/np.array(maskCopy.spacing)).astype(int).tolist()
            sitkImageProcessing.dilateMask(maskCopy, radiusSITK)
        except:
            logger.warning('Scipy used to dilate mask.')
            dilateMaskScipy(maskCopy, radius=radius, struct=struct)

    if not inPlace:
        return maskCopy

def dilateMaskScipy(mask, radius=1.0, struct=None, inPlace=True):

    if struct is None:
        radius = radius / np.array(mask.spacing)
        struct = buildStructElem(radius)
    if inPlace:
        mask.imageArray = morphology.binary_dilation(mask.imageArray, structure=struct)
    else:
        maskCopy = mask.copy()
        maskCopy.imageArray = morphology.binary_dilation(mask.imageArray, structure=struct)
        return maskCopy

def erodeMask(mask, radius=1.0, struct=None, inPlace=True, tryGPU=True):
    """
    Erodes the binary mask image using either a 3D ellipsoid structuring element build from radius,
    or a given structural element (struct).

    Args:
    - radius: float or 3-tuple of floats, the radii in mm of the ellipsoid in each dimension. Default is 1.0.
    - filt: np.array of bools, the structuring element to use for erosion. If given, the radius is not used. Default is None.
    - tryGPU: bool, whether to attempt to use the GPU for erosion using the CuPy library. Default is False.

    Returns:
    - None if inPlace = True, a new eroded mask if inPlace = False
    """

    if not inPlace:
        maskCopy = mask.copy()
    else:
        maskCopy = mask

    if struct is None:
        struct = buildStructElem(radius / np.array(maskCopy.spacing))

    if maskCopy.imageArray.size > 1e5 and tryGPU:
        try:
            logger.info('Using cupy to erode mask')
            cupyImageProcessing.dilateMask(maskCopy, radius=radius, struct=struct)
        except:
            logger.warning('Cupy not working to erode mask.')
            tryGPU = False
    else:
        tryGPU = False

    if not tryGPU:
        logger.warning('Scipy used to erode mask.')
        erodeMaskScipy(maskCopy, radius=radius, struct=struct)

    if not inPlace:
        return maskCopy

def erodeMaskScipy(mask, radius=1.0, struct=None, inPlace=True):

    if struct is None:
        radius = radius / np.array(mask.spacing)
        struct = buildStructElem(radius)
    if inPlace:
        mask.imageArray = morphology.binary_erosion(mask.imageArray, structure=struct)
    else:
        maskCopy = mask.copy()
        maskCopy.imageArray = morphology.binary_erosion(mask.imageArray, structure=struct)
        return maskCopy

def openMask(mask, radius=1.0, struct=None, inPlace=True, tryGPU=True):

    if not inPlace:
        maskCopy = mask.copy()
    else:
        maskCopy = mask

    if struct is None:
        struct = buildStructElem(radius / np.array(maskCopy.spacing))

    if maskCopy.imageArray.size > 1e5 and tryGPU:
        try:
            logger.info('Using cupy to open mask')
            cupyImageProcessing.openMask(maskCopy, radius=radius, struct=struct)
        except:
            logger.warning('Cupy not working to open mask.')
            tryGPU = False

    if not tryGPU:
        logger.warning('Scipy used to open mask.')
        openMaskScipy(maskCopy, radius=radius, struct=struct)

def openMaskScipy(mask, radius=1.0, struct=None, inPlace=True):

    if struct is None:
        radius = radius / np.array(mask.spacing)
        struct = buildStructElem(radius)
    if inPlace:
        mask.imageArray = morphology.binary_opening(mask.imageArray, structure=struct)
    else:
        maskCopy = mask.copy()
        maskCopy.imageArray = morphology.binary_opening(mask.imageArray, structure=struct)
        return maskCopy

def closeMask(mask, radius=1.0, struct=None, inPlace=True, tryGPU=True):
    if not inPlace:
        maskCopy = mask.copy()
    else:
        maskCopy = mask

    if struct is None:
        struct = buildStructElem(radius / np.array(maskCopy.spacing))

    if maskCopy.imageArray.size > 1e5 and tryGPU:
        try:
            logger.info('Using cupy to open mask')
            cupyImageProcessing.closeMask(maskCopy, radius=radius, struct=struct)
        except:
            logger.warning('Cupy not working to open mask.')
            tryGPU = False

    if not tryGPU:
        logger.warning('Scipy used to open mask.')
        closeMaskScipy(maskCopy, radius=radius, struct=struct)

def closeMaskScipy(mask, radius=1.0, struct=None, inPlace=True):

    if struct is None:
        radius = radius / np.array(mask.spacing)
        struct = buildStructElem(radius)
    if inPlace:
        mask.imageArray = morphology.binary_closing(mask.imageArray, structure=struct)
    else:
        maskCopy = mask.copy()
        maskCopy.imageArray = morphology.binary_closing(mask.imageArray, structure=struct)
        return maskCopy