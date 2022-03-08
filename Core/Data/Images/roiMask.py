import numpy as np
import scipy
from scipy.ndimage import morphology
import copy

from Core.Data.Images.image3D import Image3D
from Core.event import Event


class ROIMask(Image3D):
    def __init__(self, imageArray=None, name="ROI contour", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), displayColor=(0, 0, 0)):
        super().__init__(imageArray=imageArray, name=name, patientInfo=patientInfo, origin=origin, spacing=spacing, angles=angles)

        self.colorChangedSignal = Event(object)

        self._displayColor = displayColor

    @classmethod
    def fromImage3D(cls, image: Image3D):
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
        return scipy.ndimage.measurements.center_of_mass(self._imageArray)*self.spacing + self.origin

    def copy(self):
        return ROIMask(imageArray=copy.deepcopy(self.imageArray), name=self.name + '_copy', origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=self.seriesInstanceUID)

    def dilate(self, radius:float):
        radius = 1/np.array(self.spacing)
        diameter = radius*2+1 # if margin=0, filt must be identity matrix. If margin=1, we want to dilate by 1 => Filt must have three 1's per row.
        diameter = diameter + (diameter+1)%2
        diameter = np.round(diameter).astype(int)

        filt = np.zeros((diameter[0]+2, diameter[1]+2, diameter[2]+2))
        filt[1:diameter[0]+2, 1:diameter[1]+2, 1:diameter[2]+2] = 1
        filt = filt.astype(bool)

        self._imageArray = morphology.binary_dilation(self._imageArray, structure=filt)

    def resample(self, gridSize, origin, spacing, fillValue=0, outputType=None):
        Image3D.resample(self, gridSize, origin, spacing, fillValue=fillValue, outputType='float32')
        self.data = self._imageArray >= 0.5
        if not(outputType is None):
            self.data = self.data.astype(outputType)

    def dumpableCopy(self):
        dumpableMask = ROIMask(imageArray=self.data, name=self.name, patientInfo=self.patientInfo, origin=self.origin, spacing=self.spacing, displayColor=self._displayColor)
        # dumpableMask.patient = self.patient
        return dumpableMask