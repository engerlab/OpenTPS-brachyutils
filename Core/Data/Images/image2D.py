from Core.Data.patientData import PatientData


class Image2D(PatientData):
    def __init__(self, imageArray=None, name="2D Image", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1), angles=(0, 0, 0)):
        super().__init__(patientInfo=patientInfo)
        self.imageArray = imageArray
        self.name = name
        self.origin = origin
        self.spacing = spacing
        self.angles = angles

    def __str__(self):
        gs = self.getGridSize()
        s = 'Image3D ' + str(gs[0]) + 'x' +  str(gs[1]) + 'x' +  str(gs[2]) + '\n'
        return s

    def getGridSize(self):
        if self.data is None:
            return (0, 0)

        return self.data.shape
