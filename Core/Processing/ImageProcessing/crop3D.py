import numpy as np

from Core.Data.Images.image3D import Image3D
from Core.Data.DynamicData.dynamic3DModel import Dynamic3DModel
from Core.Data.DynamicData.dynamic3DSequence import Dynamic3DSequence
from Core.Data.Images.roiMask import ROIMask
from Core.Data.roiContour import ROIContour
from Core.api import API


@API.loggedViaAPI
def crop3DDataAroundBox(data, box, marginInMM=[10, 10, 10]):

    """
    Crop a 3D data around a box given in scanner coordinates

    Parameters
    ----------
    data : Image3D, Dynamic3DModel or Dynamic3DSequence
        The 3D data that will be cropped
    box : list of tuples or list
        The box around which the data is cropped, under the form [[x1, X2], [y1, y2], [z1, z2]]
    marginInMM : list of float for the margin in mm for each dimension
        The margins in mm that is added around the box before cropping
    """

    for i in range(3):
        if marginInMM[i] < 0:
            print('In crop3DDataAroundBox, negative margins not allowed')
            marginInMM[i] = 0

    if isinstance(data, Image3D):
        print('Before crop image 3D origin and grid size:', data.origin, data.gridSize)

        ## get the box in voxels with a min/max check to limit the box to the image border (that could be reached with the margin)
        XIndexInVoxels = [max(0, int(np.round((box[0][0] - marginInMM[0] - data.origin[0]) / data.spacing[0]))),
                          min(data.gridSize[0], int(np.round((box[0][1] + marginInMM[0] - data.origin[0]) / data.spacing[0])))]
        YIndexInVoxels = [max(0, int(np.round((box[1][0] - marginInMM[1] - data.origin[1]) / data.spacing[1]))),
                          min(data.gridSize[1], int(np.round((box[1][1] + marginInMM[1] - data.origin[1]) / data.spacing[1])))]
        ZIndexInVoxels = [max(0, int(np.round((box[2][0] - marginInMM[2] - data.origin[2]) / data.spacing[2]))),
                          min(data.gridSize[2], int(np.round((box[2][1] + marginInMM[2] - data.origin[2]) / data.spacing[2])))]

        data.imageArray = data.imageArray[XIndexInVoxels[0]:XIndexInVoxels[1], YIndexInVoxels[0]:YIndexInVoxels[1], ZIndexInVoxels[0]:ZIndexInVoxels[1]]
        # data.imageArray = croppedArray

        origin = data.origin
        origin[0] += XIndexInVoxels[0] * data.spacing[0]
        origin[1] += YIndexInVoxels[0] * data.spacing[1]
        origin[2] += ZIndexInVoxels[0] * data.spacing[2]

        data.origin = origin

        print('After crop origin and grid size:', data.origin, data.gridSize)

    elif isinstance(data, Dynamic3DModel):
        print('Crop dynamic 3D model')
        print('Crop dynamic 3D model - midp image')
        crop3DDataAroundBox(data.midp, box, marginInMM=marginInMM)
        for field in data.deformationList:
            if field.velocity != None:
                print('Crop dynamic 3D model - velocity field')
                crop3DDataAroundBox(field.velocity, box, marginInMM=marginInMM)
            if field.displacement != None:
                print('Crop dynamic 3D model - displacement field')
                crop3DDataAroundBox(field.displacement, box, marginInMM=marginInMM)


    elif isinstance(data, Dynamic3DSequence):
        print('Crop dynamic 3D sequence')

        for image3D in data.dyn3DImageList:
            crop3DDataAroundBox(image3D, box, marginInMM=marginInMM)



def getBoxAroundROI(ROI):

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


def getBoxAboveThreshold(data, threshold=0.):
    dataROI = ROIMask.fromImage3D(data)
    roiArray = np.zeros(dataROI.imageArray.shape)
    roiArray[data.imageArray > threshold] = 1
    dataROI.imageArray = roiArray.astype(bool)
    boundingBox = getBoxAroundROI(dataROI)

    return boundingBox