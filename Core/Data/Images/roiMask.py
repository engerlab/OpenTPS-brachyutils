import numpy as np
import scipy
from scipy.ndimage import morphology

import copy
import logging

from Core.Data.Images.image3D import Image3D
from Core.event import Event


try:
    import cupy
    import cupyx.scipy.ndimage
except:
    print("Module cupy not installed")
    pass

logger = logging.getLogger(__name__)


class ROIMask(Image3D):
    def __init__(self, imageArray=None, name="ROI contour", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), displayColor=(0, 0, 0)):
        super().__init__(imageArray=imageArray, name=name, patientInfo=patientInfo, origin=origin, spacing=spacing, angles=angles)

        self.colorChangedSignal = Event(object)

        self._displayColor = displayColor

    @classmethod
    def fromImage3D(cls, image:Image3D):
        return cls(imageArray=copy.deepcopy(image.imageArray), origin=image.origin, spacing=image.spacing, angles=image.angles)

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

    def copy(self):
        return ROIMask(imageArray=copy.deepcopy(self.imageArray), name=self.name + '_copy', origin=self.origin, spacing=self.spacing, angles=self.angles)

    def dilate(self, radius=1.0, filt=None, tryGPU=True):

        if filt is None:
            radius = radius/np.array(self.spacing)
            diameter = radius*2+1 # if margin=0, filt must be identity matrix. If margin=1, we want to dilate by 1 => Filt must have three 1's per row.
            diameter = diameter + (diameter+1)%2
            diameter = np.round(diameter).astype(int)

            filt = np.zeros((diameter[0]+2, diameter[1]+2, diameter[2]+2))
            filt[1:diameter[0]+2, 1:diameter[1]+2, 1:diameter[2]+2] = 1
            filt = filt.astype(bool)

        if self._imageArray.size > 1e5 and tryGPU:
            try:
                self._imageArray = cupy.asnumpy(cupyx.scipy.ndimage.binary_dilation(cupy.asarray(self._imageArray), structure=cupy.asarray(filt)))
            except:
                logger.warning('cupy not used to dilate mask.')
                self._imageArray = morphology.binary_dilation(self._imageArray, structure=filt)
        else:
            self._imageArray = morphology.binary_dilation(self._imageArray, structure=filt)

    def erode(self, radius=1.0, filt=None, tryGPU=True):

        if filt is None:
            radius = radius/np.array(self.spacing)
            diameter = radius*2+1 # if margin=0, filt must be identity matrix. If margin=1, we want to dilate by 1 => Filt must have three 1's per row.
            diameter = diameter + (diameter+1)%2
            diameter = np.round(diameter).astype(int)

            filt = np.zeros((diameter[0]+2, diameter[1]+2, diameter[2]+2))
            filt[1:diameter[0]+2, 1:diameter[1]+2, 1:diameter[2]+2] = 1
            filt = filt.astype(bool)

        if self._imageArray.size > 1e5 and tryGPU:
            try:
                self._imageArray = cupy.asnumpy(cupyx.scipy.ndimage.binary_erosion(cupy.asarray(self._imageArray), structure=cupy.asarray(filt)))
            except:
                logger.warning('cupy not used to erode mask.')
                self._imageArray = morphology.binary_erosion(self._imageArray, structure=filt)
        else:
            self._imageArray = morphology.binary_erosion(self._imageArray, structure=filt)

    def open(self, radius=1.0, filt=None, tryGPU=True):

        if filt is None:
            radius = radius/np.array(self.spacing)
            diameter = radius*2+1 # if margin=0, filt must be identity matrix. If margin=1, we want to dilate by 1 => Filt must have three 1's per row.
            diameter = diameter + (diameter+1)%2
            diameter = np.round(diameter).astype(int)

            filt = np.zeros((diameter[0]+2, diameter[1]+2, diameter[2]+2))
            filt[1:diameter[0]+2, 1:diameter[1]+2, 1:diameter[2]+2] = 1
            filt = filt.astype(bool)

        if self._imageArray.size > 1e5 and tryGPU:
            try:
                self._imageArray = cupy.asnumpy(cupyx.scipy.ndimage.binary_opening(cupy.asarray(self._imageArray), structure=cupy.asarray(filt)))
            except:
                logger.warning('cupy not used to open mask.')
                self._imageArray = morphology.binary_opening(self._imageArray, structure=filt)
        else:
            self._imageArray = morphology.binary_opening(self._imageArray, structure=filt)

    def close(self, radius=1.0, filt=None, tryGPU=True):

        if filt is None:
            radius = radius/np.array(self.spacing)
            diameter = radius*2+1 # if margin=0, filt must be identity matrix. If margin=1, we want to dilate by 1 => Filt must have three 1's per row.
            diameter = diameter + (diameter+1)%2
            diameter = np.round(diameter).astype(int)

            filt = np.zeros((diameter[0]+2, diameter[1]+2, diameter[2]+2))
            filt[1:diameter[0]+2, 1:diameter[1]+2, 1:diameter[2]+2] = 1
            filt = filt.astype(bool)

        if self._imageArray.size > 1e5 and tryGPU:
            try:
                self._imageArray = cupy.asnumpy(cupyx.scipy.ndimage.binary_closing(cupy.asarray(self._imageArray), structure=cupy.asarray(filt)))
            except:
                logger.warning('cupy not used to close mask.')
                self._imageArray = morphology.binary_closing(self._imageArray, structure=filt)
        else:
            self._imageArray = morphology.binary_closing(self._imageArray, structure=filt)


    def getROIContour(self):

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


        from Core.Data.roiContour import ROIContour  ## this is done here to avoir circular imports issue
        contour = ROIContour(name=self.name, patientInfo=self.patientInfo, displayColor=self._displayColor)
        contour.polygonMesh = polygonMeshList

        return contour


    # def dumpableCopy(self):
    #     dumpableMask = ROIMask(imageArray=self.data, name=self.name, patientInfo=self.patientInfo, origin=self.origin, spacing=self.spacing, displayColor=self._displayColor)
    #     # dumpableMask.patient = self.patient
    #     return dumpableMask