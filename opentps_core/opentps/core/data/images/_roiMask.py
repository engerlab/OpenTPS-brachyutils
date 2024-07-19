
__all__ = ['ROIMask']

import numpy as np
import scipy
import copy
import logging

from opentps.core.data.images._image3D import Image3D
from opentps.core import Event
from opentps.core.processing.imageProcessing import sitkImageProcessing, cupyImageProcessing
from opentps.core.processing.imageProcessing import roiMasksProcessing
from opentps.core.processing.imageProcessing.resampler3D import crop3DDataAroundBox
from opentps.core.processing.segmentation.segmentation3D import getBoxAroundROI

logger = logging.getLogger(__name__)


class ROIMask(Image3D):
    """
    Class for ROI mask. Inherits from Image3D. It is a binary image with 1 inside the ROI and 0 outside.

    Attributes
    ----------
    name : str (default: 'ROI contour')
        Name of the ROI mask
    color : str (default: '0,0,0')
        RGB of the color of the ROI mask, format : 'r,g,b' like '0,0,0' for black for instance
    centerOfMass : numpy.ndarray
        Center of mass of the ROI mask
    """
    def __init__(self, imageArray=None, name="ROI contour", origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), displayColor=(0, 0, 0), patient=None, seriesInstanceUID=None):
        self.colorChangedSignal = Event(object)
        self._displayColor = displayColor
        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, angles=angles,
                         patient=patient, seriesInstanceUID=seriesInstanceUID) # We want to trigger super signal only when the object is fully initialized

    @classmethod
    def fromImage3D(cls, image, **kwargs):
        """
        Create a ROIContour from an Image3D. The imageArray of the ROIContour is the same as the imageArray of the Image3D.

        Parameters
        ----------
        image : Image3D
            Image3D from which the ROIContour is created
        kwargs : dict (optional)
            Additional arguments to be passed to the constructor of the ROIContour
                - imageArray : numpy.ndarray
                    Image array of the image.
                - origin : tuple of float
                    Origin of the image.
                - spacing : tuple of float
                    Spacing of the image.
                - angles : tuple of float
                    Angles of the image.
                - seriesInstanceUID : str
                    Series instance UID of the image.
                - patient : Patient
                    Patient object of the image.
                - name : str
                    Name of the image.
        """
        dic = {'imageArray': copy.deepcopy(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient, 'name': image.name}
        dic.update(kwargs)
        return cls(**dic)

    @property
    def color(self):
        return self._displayColor

    @color.setter
    def color(self, color):
        """
        Change the color of the ROIContour.

        Parameters
        ----------
        color : str
            RGB of the new color, format : 'r,g,b' like '0,0,0' for black for instance
        """
        self._displayColor = color
        self.colorChangedSignal.emit(self._displayColor)

    @property
    def centerOfMass(self) -> np.ndarray:
        COM = np.array(scipy.ndimage.measurements.center_of_mass(self._imageArray))
        return (COM * self.spacing) + self.origin

    def getVolume(self, inVoxels=False):
        """
        Get the volume of the ROI mask.

        Parameters
        ----------
        inVoxels : bool (default: False)
            If True, the volume is returned in voxels, otherwise in mm^3.
        """
        return roiMasksProcessing.getMaskVolume(self, inVoxels=inVoxels)

    def copy(self):
        """
        Create a copy of the ROI mask.

        Returns
        -------
        ROIMask
            Copy of the ROI mask.
        """
        return ROIMask(imageArray=copy.deepcopy(self.imageArray), name=self.name + '_copy', origin=self.origin, spacing=self.spacing, angles=self.angles)

    def dilateMask(self, radius=1.0, struct=None, tryGPU=False):
        """
        Dilate the ROI mask.

        Parameters
        ----------
        radius : float (default: 1.0)
            Radius of the dilation in mm.
        struct : numpy.ndarray (default: None)
            Structuring element for the dilation.
        tryGPU : bool (default: False)
            If True, the dilation is performed on the GPU if possible.
        """
        roiMasksProcessing.dilateMask(self, radius=radius, struct=struct, inPlace=True, tryGPU=tryGPU)

    def erodeMask(self, radius=1.0, struct=None, tryGPU=True):
        """
        Erode the ROI mask.

        Parameters
        ----------
        radius : float (default: 1.0)
            Radius of the erosion in mm.
        struct : numpy.ndarray (default: None)
            Structuring element for the erosion.
        tryGPU : bool (default: False)
            If True, the erosion is performed on the GPU if possible.
        """
        roiMasksProcessing.erodeMask(self, radius=radius, struct=struct, inPlace=True, tryGPU=tryGPU)

    def createMaskRings(self, nRings, radius):
        """
        Create a ring ROI to obtain nice gradient dose around the ROI

        Parameters
        ----------
        nRings: int
            Number of rings to be created
        radius: float
            thickness of each ring in mm
        """
        rings = []
        roiSizes = [self]
        maskCopy = self.copy()

        for i in range(nRings):
            maskCopy.dilateMask(radius)
            roiSizes.append(maskCopy.copy())

        for i in range(nRings):
            ringMask = self.copy()
            ringMask.imageArray = np.logical_xor(roiSizes[i + 1].imageArray, roiSizes[i].imageArray)
            ringMask.name = 'ring_' + str(i + 1)
            rings.append(ringMask)
        return rings

    def openMask(self, radius=1.0, struct=None, tryGPU=True):
        """
        Open the ROI mask.

        Parameters
        ----------
        radius : float (default: 1.0)
            Radius of the opening in mm.
        struct : numpy.ndarray (default: None)
            Structuring element for the opening.
        tryGPU : bool (default: False)
            If True, the opening is performed on the GPU if possible.
        """
        roiMasksProcessing.openMask(self, radius=radius, struct=struct, inPlace=True, tryGPU=tryGPU)

    def closeMask(self, radius=1.0, struct=None, tryGPU=True):
        """
        Close the ROI mask.

        Parameters
        ----------
        radius : float (default: 1.0)
            Radius of the closing in mm.
        struct : numpy.ndarray (default: None)
            Structuring element for the closing.
        tryGPU : bool (default: False)
            If True, the closing is performed on the GPU if possible.
        """
        roiMasksProcessing.closeMask(self, radius=radius, struct=struct, inPlace=True, tryGPU=tryGPU)

    def getBinaryContourMask(self, internalBorder=False):
        """
        Get the binary contour mask of the ROI mask.

        Parameters
        ----------
        internalBorder : bool (default: False)
            If True the ROI is eroded before getting the contour mask, otherwise it is dilated.

        Returns
        -------
        ROIMask
            Binary contour mask of the ROI mask.
        """

        if internalBorder:
            erodedROI = ROIMask.fromImage3D(self)
            erodedROI.imageArray = np.array(erodedROI.imageArray)
            erodedROI.erodeMask(radius=erodedROI.spacing)
            imageArray = np.logical_xor(erodedROI.imageArray, self.imageArray)

            erodedROI.imageArray = imageArray

            return erodedROI

        else:
            dilatedROI = ROIMask.fromImage3D(self)
            dilatedROI.imageArray = np.array(dilatedROI.imageArray)
            dilatedROI.dilateMask(radius=dilatedROI.spacing)
            imageArray = np.logical_xor(dilatedROI.imageArray, self.imageArray)

            dilatedROI.imageArray = imageArray

            return dilatedROI

    def getROIContour(self):
        """
        Get the ROI contour.

        Returns
        -------
        ROIContour
            ROI contour of the ROI mask.
        """

        try:
            from skimage.measure import label, find_contours
            from skimage.segmentation import find_boundaries
        except:
            print('Module skimage (scikit-image) not installed, ROIMask cannot be converted to ROIContour')
            return 0

        polygonMeshList = []
        for zSlice in range(self._imageArray.shape[2]):

            labeledImg, numberOfLabel = label(self._imageArray[:, :, zSlice], return_num=True)

            for i in range(1, numberOfLabel + 1):

                singleLabelImg = labeledImg == i
                contours = find_contours(singleLabelImg.astype(np.uint8), level=0.6)

                if len(contours) > 0:

                    if len(contours) == 2:

                        ## use a different threshold in the case of an interior contour
                        contours2 = find_contours(singleLabelImg.astype(np.uint8), level=0.4)

                        interiorContour = contours2[1]
                        polygonMesh = []
                        for point in interiorContour:

                            xCoord = np.round(point[1]) * self.spacing[1] + self.origin[1]
                            yCoord = np.round(point[0]) * self.spacing[0] + self.origin[0]
                            zCoord = zSlice * self.spacing[2] + self.origin[2]

                            polygonMesh.append(yCoord)
                            polygonMesh.append(xCoord)
                            polygonMesh.append(zCoord)

                        polygonMeshList.append(polygonMesh)

                    contour = contours[0]

                    polygonMesh = []
                    for point in contour:

                        xCoord = np.round(point[1]) * self.spacing[1] + self.origin[1]
                        yCoord = np.round(point[0]) * self.spacing[0] + self.origin[0]
                        zCoord = zSlice * self.spacing[2] + self.origin[2]

                        polygonMesh.append(yCoord)
                        polygonMesh.append(xCoord)
                        polygonMesh.append(zCoord)

                    polygonMeshList.append(polygonMesh)


        from opentps.core.data._roiContour import ROIContour  ## this is done here to avoir circular imports issue
        contour = ROIContour(name=self.name, displayColor=self._displayColor)
        contour.polygonMesh = polygonMeshList

        return contour

    def compressData(self):
        """
        If ROIMask imageArray is not empty, crop it around the rectangle box containing the non-zeros values,
        else, put it to None.

        This can be used for more size efficient data storage
        """
        if 1 in self.imageArray:
            croppingBox = getBoxAroundROI(self)
            crop3DDataAroundBox(self, croppingBox, marginInMM=(2, 2, 2))
            self.imageArray = self.imageArray.astype(bool)
        else:
            self.imageArray = None


