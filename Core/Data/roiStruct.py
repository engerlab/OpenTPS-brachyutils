from Core.Data.patientData import PatientData

class ROIStruct(PatientData):
    def __init_(self, patientInfo=None):
        super().__init__(patientInfo=patientInfo)
        self.contours = []
        self.numContours = 0
        self.seriesInstanceUID = ""
        self.refImageSeriesInstanceUID = ""

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
        self.numContours += 1

    def removeContour(self, contour):
        """
        Remove a ROIContour to the list of contours of the ROIStruct.

        Parameters
        ----------
        contour : ROIContour
        """
        self.contours.remove(contour)
        self.numContours -= 1
