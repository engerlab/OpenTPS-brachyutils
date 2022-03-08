import numpy as np

from Core.Data.patientData import PatientData
from Core.event import Event


class Image2D(PatientData):
    def __init__(self, imageArray=None, name="2D Image", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1), angles=(0, 0, 0), seriesInstanceUID=""):
        super().__init__(patientInfo=patientInfo, name=name, seriesInstanceUID=seriesInstanceUID)

        self.dataChangedSignal = Event()

        self.imageArray = imageArray
        self._origin = np.array(origin)
        self._spacing = np.array(spacing)
        self._angles = np.array(angles)

    def __str__(self):
        gs = self.getGridSize()
        s = 'Image2D ' + str(self.imageArray.shape[0]) + 'x' +  str(self.imageArray.shape[1]) + '\n'
        return s

    @property
    def origin(self):
        return self._origin

    @origin.setter
    def origin(self, origin):
        self._origin = np.array(origin)
        self.dataChangedSignal.emit()

    @property
    def spacing(self):
        return self._spacing

    @spacing.setter
    def spacing(self, spacing):
        self._spacing = np.array(spacing)
        self.dataChangedSignal.emit()

    @property
    def angles(self):
        return self._angles

    @angles.setter
    def angles(self, angles):
        self._angles = np.array(angles)
        self.dataChangedSignal.emit()

    def getGridSize(self):
        if self.imageArray is None:
            return (0, 0)

        return self.imageArray.shape
