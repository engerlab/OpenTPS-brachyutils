import numpy as np
import logging

from Core.Data.Images.roiMask import ROIMask
import Core.Processing.Segmentation.segmentation as segmentation
import Core.Processing.ImageProcessing.sitkImageProcessing as stikImageProcessing

logger = logging.getLogger(__name__)


def compute3DStructuralElement(radiusXYZ, spacing = [1,1,1]):
    radiusXYZ = np.divide(radiusXYZ,spacing)
    filt = np.zeros((np.ceil(2*radiusXYZ[0]).astype(int)+1, np.ceil(2*radiusXYZ[1]).astype(int)+1, np.ceil(2*radiusXYZ[2]).astype(int)+1))
    center = (np.ceil(2*radiusXYZ[0])/2, np.ceil(2*radiusXYZ[1])/2, np.ceil(2*radiusXYZ[2])/2)
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

        body = segmentation.applyThreshold(self.ct,-750)
        temp = body.copy()

        compute3DStructuralElement([0,1,0],spacing=body.spacing)

        temp.open(filt = compute3DStructuralElement([1,30,1],spacing=body.spacing))
        temp._imageArray = np.logical_and(body.imageArray, np.logical_not(temp.imageArray))
        temp.open(filt = compute3DStructuralElement([3,1,3],spacing=body.spacing))
        tablePosition = np.max([0, np.argmax(temp._imageArray.sum(axis=2).sum(axis=0))-1])
        body._imageArray[:, tablePosition:, :] = False
        components = stikImageProcessing.connectComponents(body)
        body._imageArray = components.imageArray == 1

        return body


    def segmentBones(self, body=None):

        bones = ROIMask()
        return bones


    def segmentLungs(self, body=None):

        lungs = ROIMask()
        return lungs


