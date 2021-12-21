
from Core.Data.patientData import PatientData

class ROIContour(PatientData):
    def __init__(self, patientInfo=None, name="ROI contour", displayColor=(0,0,0), referencedFrameOfReferenceUID=None):
        super().__init__(patientInfo=patientInfo)
        self.name = name
        self.displayColor = displayColor
        self.referencedFrameOfReferenceUID = referencedFrameOfReferenceUID
        self.referencedSOPInstanceUIDs = []
        self.polygonMesh = []

