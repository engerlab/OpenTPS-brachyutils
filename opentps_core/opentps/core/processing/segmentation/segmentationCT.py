import numpy as np
import logging

import opentps.core.processing.segmentation.segmentation3D as seg
import opentps.core.processing.imageProcessing.sitkImageProcessing as stik

logger = logging.getLogger(__name__)


def compute3DStructuralElement(radiusXYZ, spacing=[1,1,1]):
    radiusXYZ = np.divide(radiusXYZ,spacing)
    filt = np.zeros((2*np.ceil(radiusXYZ[0]).astype(int)+1, 2*np.ceil(radiusXYZ[1]).astype(int)+1, 2*np.ceil(radiusXYZ[2]).astype(int)+1))
    center = (np.ceil(radiusXYZ[0]), np.ceil(radiusXYZ[1]), np.ceil(radiusXYZ[2]))
    x = np.arange(filt.shape[1])
    y = np.arange(filt.shape[0])
    z = np.arange(filt.shape[2])
    xi = np.array(np.meshgrid(x, y, z))
    filt = (np.square(xi[1]-center[0])/np.square(radiusXYZ[0]+np.finfo(np.float32).eps) + np.square(xi[0]-center[1])/np.square(radiusXYZ[1]+np.finfo(np.float32).eps) + np.square(xi[2]-center[2])/np.square(radiusXYZ[2]+np.finfo(np.float32).eps)) <=1
    return filt

class SegmentationCT():

    def __init__(self, ct):
        self.ct = ct

    def segmentBody(self):

        # Air detection
        body = seg.applyThreshold(self.ct, -750)

        # Table detection
        temp = body.copy()
        temp.open(filt = compute3DStructuralElement([1,30,1],spacing=body.spacing))
        temp._imageArray = np.logical_and(body.imageArray, np.logical_not(temp.imageArray))
        temp.open(filt = compute3DStructuralElement([3,1,3],spacing=body.spacing))
        tablePosition = np.max([0, np.argmax(temp._imageArray.sum(axis=2).sum(axis=0))-1])
        if tablePosition>body.gridSize[1]/2:
            body._imageArray[:, tablePosition:, :] = False

        # Body definition
        temp = body.copy()
        temp.erode(filt=compute3DStructuralElement([5, 5, 5], spacing=body.spacing))
        temp.close(filt=compute3DStructuralElement([10, 10, 10], spacing=body.spacing))
        body._imageArray = np.logical_and(np.logical_not(body.imageArray), np.logical_not(temp.imageArray))
        labels = stik.connectComponents(body)
        body._imageArray = labels.imageArray != 1
        body.open(filt=compute3DStructuralElement([3, 5, 1], spacing=body.spacing))
        labels = stik.connectComponents(body)
        body._imageArray = labels.imageArray == 1

        return body

    def segmentBones(self, body=None):

        bones = seg.applyThreshold(self.ct, 200)
        bones.close(filt=compute3DStructuralElement([2, 2, 2], spacing=bones.spacing))
        bones.open(filt=compute3DStructuralElement([3, 3, 3], spacing=bones.spacing))
        return bones

    def segmentLungs(self, body=None):

        if body is None:
            body = self.segmentBody()
        else:
            body = body.copy()
        body.dilate(filt=compute3DStructuralElement([4, 4, 4], spacing=body.spacing))

        lungs = seg.applyThreshold(self.ct, -950, thresholdMax=-350)
        lungs._imageArray = np.logical_and(lungs._imageArray,body.imageArray)
        lungs.open(filt=compute3DStructuralElement([3, 3, 4], spacing=lungs.spacing))
        lungs.close(filt=compute3DStructuralElement([3, 3, 4], spacing=lungs.spacing))

        labels = stik.connectComponents(lungs)
        lungs._imageArray = np.logical_and(labels.imageArray >0, labels.imageArray <3)

        return lungs
