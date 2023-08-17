from typing import Sequence
import numpy as np
import logging

# from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data.images._image3D import Image3D
from opentps.core.data._roiContour import ROIContour

logger = logging.getLogger(__name__)


def applyThreshold(image, thresholdMin, thresholdMax=np.inf):
    """
    Apply a threshold to an image and return a ROIMask object (True if value > thresholdMin and value < thresholdMax)

    Parameters
    ----------
    image : Image3D
        The image to be thresholded
    thresholdMin : float
        The minimum threshold value
    thresholdMax : float
        The maximum threshold value (default: np.inf)

    Returns
    ----------
    mask : ROIMask
        The mask of the thresholded image
    """
    from opentps.core.data.images._roiMask import ROIMask
    mask = ROIMask.fromImage3D(image)
    mask._imageArray = np.logical_and(np.greater(image.imageArray,thresholdMin),np.less(image.imageArray,thresholdMax))
    return mask


def getBoxAroundROI(ROI) -> Sequence[Sequence[float]]:

    """
    Get the box around an ROI in scanner coordinates (using the ROI origin and spacing)

    Parameters
    ----------
    ROI : an ROIContour or ROIMask
        The contour that is contained in the desired box


    Returns
    ----------
    boxInUniversalCoords : list of tuples or list
        The box around which the data is cropped, under the form [[x1, X2], [y1, y2], [z1, z2]]

    """

    from opentps.core.data.images._roiMask import ROIMask

    if isinstance(ROI, ROIContour):
        ROIMaskObject = ROI.getBinaryMask()

    elif isinstance(ROI, ROIMask):
        ROIMaskObject = ROI

    ones = np.where(ROIMaskObject.imageArray == True)

    boxInVoxel = [[np.min(ones[0]), np.max(ones[0])],
                  [np.min(ones[1]), np.max(ones[1])],
                  [np.min(ones[2]), np.max(ones[2])]]

    logger.info(f'ROI box in voxels: {boxInVoxel}')

    boxInUniversalCoords = []
    for i in range(3):
        boxInUniversalCoords.append([ROI.origin[i] + (boxInVoxel[i][0] * ROI.spacing[i]), ROI.origin[i] + (boxInVoxel[i][1] * ROI.spacing[i])])

    logger.info(f'ROI box in scanner coordinates: {boxInUniversalCoords}')

    return boxInUniversalCoords


def getBoxAboveThreshold(data:Image3D, threshold=0.):
    """
    Get the box around an ROI in scanner coordinates and apply a threshold (using the ROI origin and spacing)

    Parameters
    ----------
    data : Image3D
        The image with the ROI to be thresholded
    threshold : float
        The minimum threshold value in the ROI(default: 0.)

    Returns
    ----------
    boundingBox : list of tuples or list
        The box around which the data is cropped and the threshold applied under the form [[x1, X2], [y1, y2], [z1, z2]]
    """
    from opentps.core.data.images._roiMask import ROIMask

    dataROI = ROIMask.fromImage3D(data)
    roiArray = np.zeros(dataROI.imageArray.shape)
    roiArray[data.imageArray > threshold] = 1
    dataROI.imageArray = roiArray.astype(bool)
    boundingBox = getBoxAroundROI(dataROI)

    return boundingBox
