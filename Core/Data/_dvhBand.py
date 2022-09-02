
__all__ = ['DVHBand']


from Core.Data._patientData import PatientData


class DVHBand(PatientData):
    def __init__(self, doses=[], contour=[], maxDVH=100.0):
        super().__init__()
        self.doseSOPInstanceUIDs = []
        self.contourSOPInstanceUID = ""
        self.roiName = ""
        self.roiDisplayColor = []
        self.lineStyle = "solid"
        self.nominalDVH = []
        self.dose = []
        self.volumeLow = []
        self.volumeHigh = []
        self.volumeAbsoluteLow = []
        self.volumeAbsoluteHigh = []
        self.dMean = [0, 0]
        self.d98 = [0, 0]
        self.d95 = [0, 0]
        self.d50 = [0, 0]
        self.d5 = [0, 0]
        self.d2 = [0, 0]
        self.dMin = [0, 0]
        self.dMax = [0, 0]



    def __str__(self):
        pass



