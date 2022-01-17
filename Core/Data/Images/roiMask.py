from Core.Data.Images.image3D import Image3D
from Core.event import Event


class ROIMask(Image3D):
    def __init__(self, imageArray=None, name="ROI contour", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1), displayColor=(0, 0, 0)):
        super().__init__(imageArray=imageArray, name=name, patientInfo=patientInfo, origin=origin, spacing=spacing)

        self.colorChangedSignal = Event(object)

        self._displayColor = displayColor

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

    def resample(self, gridSize, origin, spacing, fillValue=0, outputType=None):
        Image3D.resample(self, gridSize, origin, spacing, fillValue=fillValue, outputType='float32')
        self.data = self._imageArray >= 0.5
        if not(outputType is None):
            self.data = self.data.astype(outputType)

    def dumpableCopy(self):
        return ROIMask(imageArray=self.data, name=self.name, patientInfo=self.patientInfo, origin=self.origin, spacing=self.spacing, displayColor=self._displayColor)