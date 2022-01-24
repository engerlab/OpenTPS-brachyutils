import numpy as np

from Core.Data.patientData import PatientData

class Dynamic3DSequence(PatientData):

    def __init__(self, dyn3DImageList = [], timingsList = [], name="3D Dyn Seq", patientInfo=None):
        super().__init__(patientInfo=patientInfo, name=name)

        self.dyn3DImageList = dyn3DImageList

        if len(timingsList) > 0:
            self.timingsList = timingsList
        else:
            self.breathingPeriod = 4000
            self.inhaleDuration = 1800
            self.timingsList = self.prepareTimings()

        self.isDynamic = True

    def __str__(self):
        s = "Dyn series: " + self.name + '\n'
        for image in self.dyn3DImageList:
            s += str(image) + '\n'

        return s

    def print_dynSeries_info(self, prefix=""):
        print(prefix + "Dyn series: " + self.name)
        print(prefix, len(self.dyn3DImageList), ' 3D images in the serie')


    def prepareTimings(self):
        numberOfImages = len(self.dyn3DImageList)
        timingList = np.linspace(0, 4000, numberOfImages + 1)

        return timingList


    def dumpableCopy(self):
        dumpableImageCopiesList = [image.dumpableCopy() for image in self.dyn3DImageList]
        return Dynamic3DSequence(dyn3DImageList=dumpableImageCopiesList, timingsList=self.timingsList, name=self.name, patientInfo=self.patientInfo)