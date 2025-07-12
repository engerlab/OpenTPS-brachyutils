import numpy as np
import logging

import opentps.core.processing.segmentation.segmentation3D as seg
import opentps.core.processing.imageProcessing.sitkImageProcessing as stik

logger = logging.getLogger(__name__)


def compute3DStructuralElement(radiusXYZ, spacing=[1,1,1]):
    """
    Compute a 3D structural element for morphological operations (e.g. dilation, erosion).

    Parameters
    ----------
    radiusXYZ : list
        The radius of the structural element in each direction
    spacing : list
        The spacing of the image in each direction (default: [1,1,1])

    Returns
    ----------
    filt : bool numpy array
        The structural element (bool mask)
    """
    
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
    """
    Class for CT segmentation

    Parameters
    ----------
    ct : Image3D
        The CT image to be segmented

    Attributes
    ----------
    ct : Image3D
        The CT image to be segmented
    """

    def __init__(self, ct):
        self.ct = ct

    def segmentBody(self):
        """
        Segment the body from the CT image

        Returns
        ----------
        body : Image3D
            The body mask (bool mask)
        """

        # Air detection
        body = seg.applyThreshold(self.ct, -750)

        # Table detection
        temp = body.copy()
        temp.openMask(struct= compute3DStructuralElement([1, 30, 1], spacing=body.spacing))
        temp._imageArray = np.logical_and(body.imageArray, np.logical_not(temp.imageArray))
        temp.openMask(struct= compute3DStructuralElement([3, 1, 3], spacing=body.spacing))
        tablePosition = np.max([0, np.argmax(temp._imageArray.sum(axis=2).sum(axis=0))-1])
        if tablePosition>body.gridSize[1]/2:
            body._imageArray[:, tablePosition:, :] = False

        # Body definition
        temp = body.copy()
        temp.erodeMask(struct=compute3DStructuralElement([5, 5, 5], spacing=body.spacing))
        temp.closeMask(struct=compute3DStructuralElement([10, 10, 10], spacing=body.spacing))
        body._imageArray = np.logical_and(np.logical_not(body.imageArray), np.logical_not(temp.imageArray))
        labels = stik.connectComponents(body)
        body._imageArray = labels.imageArray != 1
        body.openMask(struct=compute3DStructuralElement([3, 5, 1], spacing=body.spacing))
        labels = stik.connectComponents(body)
        body._imageArray = labels.imageArray == 1

        return body

    def segmentBones(self, body=None):
        """
        Segment the bones from the CT image

        Parameters
        ----------
        body : Image3D
            The body mask (bool mask)

        Returns
        ----------
        bones : Image3D
            The bones mask (bool mask)
        """
        bones = seg.applyThreshold(self.ct, 200)
        bones.closeMask(struct=compute3DStructuralElement([2, 2, 2], spacing=bones.spacing))
        bones.openMask(struct=compute3DStructuralElement([3, 3, 3], spacing=bones.spacing))
        return bones

    def segmentLungs(self, body=None):
        """
        Segment the lungs from the CT image

        Parameters
        ----------
        body : Image3D
            The body mask (bool mask)

        Returns
        ----------
        lungs : Image3D
            The lungs mask (bool mask)
        """
        if body is None:
            body = self.segmentBody()
        else:
            body = body.copy()
        body.dilateMask(struct=compute3DStructuralElement([4, 4, 4], spacing=body.spacing))

        lungs = seg.applyThreshold(self.ct, -950, thresholdMax=-350)
        lungs._imageArray = np.logical_and(lungs._imageArray,body.imageArray)
        lungs.openMask(struct=compute3DStructuralElement([3, 3, 4], spacing=lungs.spacing))
        lungs.closeMask(struct=compute3DStructuralElement([3, 3, 4], spacing=lungs.spacing))

        labels = stik.connectComponents(lungs)
        lungs._imageArray = np.logical_and(labels.imageArray >0, labels.imageArray <3)

        return lungs
