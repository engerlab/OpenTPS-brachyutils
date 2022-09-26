from typing import Sequence
import numpy as np
import logging

from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data.images._image3D import Image3D
from opentps.core.data._roiContour import ROIContour

logger = logging.getLogger(__name__)


def applyThreshold(image, thresholdMin, thresholdMax=np.inf):
    mask = ROIMask.fromImage3D(image)
    mask._imageArray = np.logical_and(np.greater(image.imageArray,thresholdMin),np.less(image.imageArray,thresholdMax))
    return mask


def getBoxAroundROI(ROI) -> Sequence[Sequence[float]]:

    """
    Get the box around an ROI in scanner coordinates (using the ROI origin and spacing)
    It s kind of stupid to get the ROI as an array to get the coordinates back using numpy.where ...

    Parameters
    ----------
    ROI : an ROIContour or ROIMask
        The contour that is contained in the desired box


    Returns
    ----------
    boxInUniversalCoords : list of tuples or list
        The box around which the data is cropped, under the form [[x1, X2], [y1, y2], [z1, z2]]

    """

    if isinstance(ROI, ROIContour):
        ROIMaskObject = ROI.getBinaryMask()

    elif isinstance(ROI, ROIMask):
        ROIMaskObject = ROI

    ones = np.where(ROIMaskObject.imageArray == True)

    boxInVoxel = [[np.min(ones[0]), np.max(ones[0])],
                  [np.min(ones[1]), np.max(ones[1])],
                  [np.min(ones[2]), np.max(ones[2])]]

    print('ROI box in voxels:', boxInVoxel)

    boxInUniversalCoords = []
    for i in range(3):
        boxInUniversalCoords.append([ROI.origin[i] + (boxInVoxel[i][0] * ROI.spacing[i]), ROI.origin[i] + (boxInVoxel[i][1] * ROI.spacing[i])])

    print('ROI box in scanner coordinates:', boxInUniversalCoords)

    return boxInUniversalCoords


def getBoxAboveThreshold(data:Image3D, threshold=0.):
    dataROI = ROIMask.fromImage3D(data)
    roiArray = np.zeros(dataROI.imageArray.shape)
    roiArray[data.imageArray > threshold] = 1
    dataROI.imageArray = roiArray.astype(bool)
    boundingBox = getBoxAroundROI(dataROI)

    return boundingBox
