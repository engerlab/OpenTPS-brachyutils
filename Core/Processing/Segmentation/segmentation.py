import numpy as np
import logging

from Core.Data.Images.roiMask import ROIMask

logger = logging.getLogger(__name__)


def applyThreshold(image, thresholdMin, thresholdMax=np.inf):
    mask = ROIMask.fromImage3D(image)
    mask._imageArray = np.logical_and(np.greater(image.imageArray,thresholdMin),np.less(image.imageArray,thresholdMax))
    return mask
