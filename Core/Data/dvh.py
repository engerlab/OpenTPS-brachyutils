from Core.Data.patientData import PatientData


class DVH(PatientData):
    def __init__(self, dose=[], contour=[], maxDVH=100.0):
        super().__init__()
        self.doseSOPInstanceUID = ""
        self.contourSOPInstanceUID = ""
        self.roiName = ""
        self.roiDisplayColor = []
        self.lineStyle = "solid"
        self.dose = []
        self.volume = []
        self.volumeAbsolute = []
        self.dMean = 0
        self.d98 = 0
        self.d95 = 0
        self.d50 = 0
        self.d5 = 0
        self.d2 = 0
        self.dMin = 0
        self.dMax = 0

        if(dose != []):
            self.doseSOPInstanceUID = dose.sopInstanceUID

        if(contour != []):
            self.contourSOPInstanceUID = contour.sopInstanceUID
            self.roiName = contour.roiName
            self.roiDisplayColor = contour.roiDisplayColor

        if(dose != [] and contour != []):
            #compute_DVH(dose, Contour, maxDVH)
            pass


    def __str__(self):
        pass



