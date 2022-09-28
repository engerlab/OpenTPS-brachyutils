
__all__ = ['RTStruct']


from typing import Sequence

from opentps.core.data._patientData import PatientData
from opentps.core.data._roiContour import ROIContour
from opentps.core import Event


class RTStruct(PatientData):

    def __init__(self, name="RT-struct", seriesInstanceUID="", sopInstanceUID=""):
        super().__init__(name=name, seriesInstanceUID=seriesInstanceUID)

        self.contourAddedSignal = Event(ROIContour)
        self.contourRemovedSignal = Event(ROIContour)

        self._contours = []
        self.sopInstanceUID = sopInstanceUID

    def __str__(self):
        return "RTstruct " + self.seriesInstanceUID

    def __getitem__(self, item):
        return self._contours[item]

    def __len__(self):
        return len(self._contours)

    @property
    def contours(self) -> Sequence[ROIContour]:
        # Doing this ensures that the user can't append directly to contours
        return [contour for contour in self._contours]
    
    def appendContour(self, contour:ROIContour):
        """
        Add a ROIContour to the list of contours of the ROIStruct.

        Parameters
        ----------
        contour : ROIContour
        """
        self._contours.append(contour)
        self.contourAddedSignal.emit(contour)


    def removeContour(self, contour:ROIContour):
        """
        Remove a ROIContour to the list of contours of the ROIStruct.

        Parameters
        ----------
        contour : ROIContour
        """
        self._contours.remove(contour)
        self.contourRemovedSignal.emit(contour)


    def getContourByName(self, contour_name:str) -> ROIContour:
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