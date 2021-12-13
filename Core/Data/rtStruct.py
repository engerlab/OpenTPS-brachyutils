from Core.Data.image3D import Image3D
from Core.Data.patientData import PatientData

class RTstruct(PatientData):
    def __init_(self):
        self.contours = []
        self.numContours = 0
        self.imageSeriesInstanceUID = ""
        self.seriesInstanceUID = ""

    def __str__(self):
        return "RTstruct " + self.seriesInstanceUID  
    
    def appendContour(self, contour):
        self.contours.append(contour)
        self.numContours += 1

    def removeContour(self, contour):
        self.contours.remove(contour)
        self.numContours -= 1

class ROIcontour(Image3D):
    def __init__(self, data=None, name=None, origin=(0, 0, 0), spacing=(1, 1, 1), contourMask = None):
        super().__init__(self,data=data, name=name, origin=origin, spacing=spacing)
        self.seriesInstanceUID = ""
        self.displayColor = ""
        self.contourMask = contourMask
        
