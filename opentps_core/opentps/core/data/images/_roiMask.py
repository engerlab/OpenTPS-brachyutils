
__all__ = ['ROIMask']

import math

import numpy as np
import scipy
from scipy.ndimage import morphology

import copy
import logging

from opentps.core.data.images._image3D import Image3D
from opentps.core import Event


try:
    import cupy
    import cupyx.scipy.ndimage
except:
    print("Module cupy not installed")
    pass

logger = logging.getLogger(__name__)


class ROIMask(Image3D):
    def __init__(self, imageArray=None, name="ROI contour", origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), displayColor=(0, 0, 0), patient=None, seriesInstanceUID=None):
        self.colorChangedSignal = Event(object)
        self._displayColor = displayColor
        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, angles=angles,
                         patient=patient, seriesInstanceUID=seriesInstanceUID) # We want to trigger super signal only when the object is fully initialized

    @classmethod
    def fromImage3D(cls, image, **kwargs):
        dic = {'imageArray': copy.deepcopy(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient}
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

    def copy(self):
        return ROIMask(imageArray=copy.deepcopy(self.imageArray), name=self.name + '_copy', origin=self.origin, spacing=self.spacing, angles=self.angles)

    def dilate(self, radius=1.0, filt=None, tryGPU=True):
        if filt is None:
            radius = radius/np.array(self.spacing)
            if np.min(radius)<=0:
                return
            diameter = np.ceil(radius).astype(int) * 2 + 1
            filt = np.zeros(tuple(diameter)).astype(bool)
            for i in range(diameter[0]):
                for j in range(diameter[1]):
                    for k in range(diameter[2]):
                        y = i - math.floor(diameter[0] / 2)
                        x = j - math.floor(diameter[1] / 2)
                        z = k - math.floor(diameter[2] / 2)
                        if (
                                y ** 2 / radius[1] ** 2 + x ** 2 / radius[0] ** 2 + z ** 2 / radius[2] ** 2 <= 1):  # generate ellipsoid structuring element
                            filt[i, j, k] = True

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
            radius = radius / np.array(self.spacing)
            if np.min(radius) <= 0:
                return
            diameter = np.ceil(radius).astype(int) * 2 + 1
            filt = np.zeros(tuple(diameter)).astype(bool)
            for i in range(diameter[0]):
                for j in range(diameter[1]):
                    for k in range(diameter[2]):
                        y = i - math.floor(diameter[0] / 2)
                        x = j - math.floor(diameter[1] / 2)
                        z = k - math.floor(diameter[2] / 2)
                        if (
                                y ** 2 / radius[1] ** 2 + x ** 2 / radius[0] ** 2 + z ** 2 / radius[
                            2] ** 2 <= 1):  # generate ellipsoid structuring element
                            filt[i, j, k] = True

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
            radius = radius / np.array(self.spacing)
            if np.min(radius) <= 0:
                return
            diameter = np.ceil(radius).astype(int) * 2 + 1
            filt = np.zeros(tuple(diameter)).astype(bool)
            for i in range(diameter[0]):
                for j in range(diameter[1]):
                    for k in range(diameter[2]):
                        y = i - math.floor(diameter[0] / 2)
                        x = j - math.floor(diameter[1] / 2)
                        z = k - math.floor(diameter[2] / 2)
                        if (
                                y ** 2 / radius[1] ** 2 + x ** 2 / radius[0] ** 2 + z ** 2 / radius[
                            2] ** 2 <= 1):  # generate ellipsoid structuring element
                            filt[i, j, k] = True

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
            radius = radius / np.array(self.spacing)
            if np.min(radius) <= 0:
                return
            diameter = np.ceil(radius).astype(int) * 2 + 1
            filt = np.zeros(tuple(diameter)).astype(bool)
            for i in range(diameter[0]):
                for j in range(diameter[1]):
                    for k in range(diameter[2]):
                        y = i - math.floor(diameter[0] / 2)
                        x = j - math.floor(diameter[1] / 2)
                        z = k - math.floor(diameter[2] / 2)
                        if (
                                y ** 2 / radius[1] ** 2 + x ** 2 / radius[0] ** 2 + z ** 2 / radius[
                            2] ** 2 <= 1):  # generate ellipsoid structuring element
                            filt[i, j, k] = True

        if self._imageArray.size > 1e5 and tryGPU:
            try:
                self._imageArray = cupy.asnumpy(cupyx.scipy.ndimage.binary_closing(cupy.asarray(self._imageArray), structure=cupy.asarray(filt)))
            except:
                logger.warning('cupy not used to close mask.')
                self._imageArray = morphology.binary_closing(self._imageArray, structure=filt)
        else:
            self._imageArray = morphology.binary_closing(self._imageArray, structure=filt)

    def getBinaryContourMask(self):
        dilatedROI = ROIMask.fromImage3D(self)
        dilatedROI.imageArray = np.array(dilatedROI.imageArray)
        dilatedROI.dilate(radius=dilatedROI.spacing)
        imageArray = np.logical_xor(dilatedROI.imageArray, self.imageArray)

        dilatedROI.imageArray = imageArray

        return dilatedROI


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


        from opentps.core.data._roiContour import ROIContour  ## this is done here to avoir circular imports issue
        contour = ROIContour(name=self.name, displayColor=self._displayColor)
        contour.polygonMesh = polygonMeshList

        return contour


    # def dumpableCopy(self):
    #     dumpableMask = ROIMask(imageArray=self.data, name=self.name, patientInfo=self.patientInfo, origin=self.origin, spacing=self.spacing, displayColor=self._displayColor)
    #     # dumpableMask.patient = self.patient
    #     return dumpableMask