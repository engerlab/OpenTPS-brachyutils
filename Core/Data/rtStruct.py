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


    def get_contour_by_name(self, contour_name):
        """
        Get a ROIContour that has name contour_name from the list of contours of the ROIStruct.

        Parameters
        ----------
        contour_name : str
        """
        for contour in self._contours:
            if contour.name == contour_name:
                return contour
        print(f'No contour with name {contour_name} found in the list of contours')

    def print_ROINames(self):
        print("\nRT Struct UID: " + self.seriesInstanceUID)
        count = -1
        for contour in self._contours:
            count += 1
            print('  [' + str(count) + ']  ' + contour.name)