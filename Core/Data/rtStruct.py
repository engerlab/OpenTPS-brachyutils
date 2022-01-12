from Core.Data.patientData import PatientData
from Core.Data.roiContour import ROIContour
from Core.event import Event


class RTStruct(PatientData):

    def __init__(self, name="RT-struct", patientInfo=None, seriesInstanceUID="", sopInstanceUID=""):
        super().__init__(patientInfo=patientInfo, name=name, seriesInstanceUID=seriesInstanceUID)

        self.contourAddedSignal = Event(ROIContour)
        self.contourRemovedSignal = Event(ROIContour)

        self._contours = []
        self.sopInstanceUID = sopInstanceUID

    def __str__(self):
        return "RTstruct " + self.seriesInstanceUID

    @property
    def contours(self):
        # Doing this ensures that the user can't append directly to contours
        return [contour for contour in self._contours]
    
    def appendContour(self, contour):
        """
        Add a ROIContour to the list of contours of the ROIStruct.

        Parameters
        ----------
        contour : ROIContour
        """
        self._contours.append(contour)
        self.contourAddedSignal.emit(contour)


    def removeContour(self, contour):
        """
        Remove a ROIContour to the list of contours of the ROIStruct.

        Parameters
        ----------
        contour : ROIContour
        """
        self._contours.remove(contour)
        self.contourRemovedSignal.emit(contour)