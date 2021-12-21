
from Core.Data.patientData import PatientData

class RTStruct(PatientData):
    def __init__(self, name="RT-struct", patientInfo=None, seriesInstanceUID="", sopInstanceUID=""):
        super().__init__(patientInfo=patientInfo)
        self.name = name
        self.contours = []
        self.seriesInstanceUID = seriesInstanceUID
        self.sopInstanceUID = sopInstanceUID

    def __str__(self):
        return "RTstruct " + self.seriesInstanceUID  
    
    def appendContour(self, contour):
        """
        Add a ROIContour to the list of contours of the ROIStruct.

        Parameters
        ----------
        contour : ROIContour
        """
        self.contours.append(contour)

    def removeContour(self, contour):
        """
        Remove a ROIContour to the list of contours of the ROIStruct.

        Parameters
        ----------
        contour : ROIContour
        """
        self.contours.remove(contour)
