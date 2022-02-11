from Core.Data.patientData import PatientData


class Image2D(PatientData):
    def __init__(self, imageArray=None, name="2D Image", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1), angles=(0, 0, 0), seriesInstanceUID=""):
        super().__init__(patientInfo=patientInfo, name=name, seriesInstanceUID=seriesInstanceUID)
        self.imageArray = imageArray
        self.origin = origin
        self.spacing = spacing
        self.angles = angles

    def __str__(self):
        gs = self.getGridSize()
        s = 'Image2D ' + str(self.imageArray.shape[0]) + 'x' +  str(self.imageArray.shape[1]) + '\n'
        return s

    def getGridSize(self):
        if self.imageArray is None:
            return (0, 0)

        return self.imageArray.shape
