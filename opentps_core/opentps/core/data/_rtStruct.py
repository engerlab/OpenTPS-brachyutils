
__all__ = ['RTStruct']

import numpy as np
from typing import Sequence

from opentps.core.data._patientData import PatientData
from opentps.core.data._roiContour import ROIContour
from opentps.core.data.images._roiMask import ROIMask
from opentps.core import Event
from opentps.core.data.images._ctImage import CTImage


class RTStruct(PatientData):
    """
    Class for storing RTStruct data. Inherits from PatientData.

    Parameters
    ----------
    name : str
        Name of the RTStruct
    seriesInstanceUID : str
        Series Instance UID of the RTStruct
    sopInstanceUID : str
        SOP Instance UID of the RTStruct
    contours : list
        List of ROIContour objects
    """
    def __init__(self, name="RT-struct", seriesInstanceUID="", sopInstanceUID=""):
        super().__init__(name=name, seriesInstanceUID=seriesInstanceUID)

        self.contourAddedSignal = Event(ROIContour)
        self.contourRemovedSignal = Event(ROIContour)

        self._contours = []
        self.sopInstanceUID = sopInstanceUID

    def __str__(self):
        """
        Returns a string representation of the RTStruct.

        Returns
        -------
        str
            String representation of the RTStruct
        """
        return "RTstruct " + self.seriesInstanceUID

    def __getitem__(self, item):
        """
        Returns the ROIContour at index item.

        Parameters
        ----------
        item : int
            Index of the ROIContour to return
        Returns
        -------
        ROIContour
            ROIContour at index item
        """
        return self._contours[item]

    def __len__(self):
        """
        Returns the number of ROIContours in the RTStruct.

        Returns
        -------
        int
            Number of ROIContours in the RTStruct
        """
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
        """
        Print the names of the ROIContours in the RTStruct.
        """
        print("\nRT Struct UID: " + self.seriesInstanceUID)
        count = -1
        for contour in self._contours:
            count += 1
            print('  [' + str(count) + ']  ' + contour.name)

    def make1ContourFromSeveral(self, contour_names:str, ct:CTImage) -> ROIContour:
        """
        Draw 1 ROIContour from the names of several ROI contour to be used in dose computation

        Parameters
        -------------
        contour_names : str
            Names of the contours we want to add
        ct: CTImage
            CT image of the patient

        Returns
        ----------
        ROIContour: The addition of all the contours.
        """
        contour_names = contour_names.split(' ')
        final_mask = ROIMask(name='all_target', origin=ct.origin, spacing=ct.spacing, patient=self.patient)
        final_mask.imageArray = np.full(ct.imageArray.shape,False)
        for name in contour_names:
            contour = self.getContourByName(name)
            mask = contour.getBinaryMask(origin=ct.origin, gridSize=ct.gridSize, spacing=ct.spacing)
            final_mask.imageArray += mask.imageArray
        final_contour = final_mask.getROIContour()
        return final_contour

