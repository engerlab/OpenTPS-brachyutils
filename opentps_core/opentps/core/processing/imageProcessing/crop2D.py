from typing import Sequence

import numpy as np

from opentps.core.data.images._image2D import Image2D


def crop2DDataAroundBox(data:Image2D, box, marginInMM=[0, 0, 0]):
    """
    Crop the data around the box with a margin in mm

    Parameters
    ----------
    data : Image2D
        data to be cropped.
    box : Sequence[Sequence[float]]
        [[Xmin,xMax],
        [Ymin,Ymax]] :coordinates of the box to be cropped around.
    marginInMM : Sequence[float]
        margin in mm to be added to the box.
    """
    for i in range(3):
        if marginInMM[i] < 0:
            raise ValueError('Negative margin not allowed')

    ## get the box in voxels with a min/max check to limit the box to the image border (that could be reached with the margin)
    XIndexInVoxels = [max(0, int(np.round((box[0][0] - marginInMM[0] - data.origin[0]) / data.spacing[0]))),
                      min(data.gridSize[0], int(np.round((box[0][1] + marginInMM[0] - data.origin[0]) / data.spacing[0])))]
    YIndexInVoxels = [max(0, int(np.round((box[1][0] - marginInMM[1] - data.origin[1]) / data.spacing[1]))),
                      min(data.gridSize[1], int(np.round((box[1][1] + marginInMM[1] - data.origin[1]) / data.spacing[1])))]

    data.imageArray = data.imageArray[XIndexInVoxels[0]:XIndexInVoxels[1], YIndexInVoxels[0]:YIndexInVoxels[1]]
    # data.imageArray = croppedArray

    origin = data.origin
    origin[0] += XIndexInVoxels[0] * data.spacing[0]
    origin[1] += YIndexInVoxels[0] * data.spacing[1]

    data.origin = origin


def getBoxAroundROI(ROI:Image2D) -> Sequence[Sequence[float]]:
    """
    Get the box universal coordinates around the ROI ([[Xmin,xMax],
                                                      [Ymin,Ymax]])

    Parameters
    ----------
    ROI : Image2D
        ROI to be cropped.

    Returns
    -------
    Sequence[Sequence[float]]
        [[Xmin,xMax],
        [Ymin,Ymax]] :coordinates of the box.
    """
    if not ROI.imageArray.dtype == bool:
        raise ValueError('ROI must have a boolean array')

    ones = np.where(ROI.imageArray == True)

    boxInVoxel = [[np.min(ones[0]), np.max(ones[0])],
                  [np.min(ones[1]), np.max(ones[1])]]

    boxInUniversalCoords = []
    for i in range(2):
        boxInUniversalCoords.append([ROI.origin[i] + (boxInVoxel[i][0] * ROI.spacing[i]), ROI.origin[i]])

    return boxInUniversalCoords
