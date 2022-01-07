import numpy as np

from Core.Data.patientData import PatientData

class Dynamic3DSequence(PatientData):

    def __init__(self, imageList = [], timingsList = [], name="3D Dyn Seq", patientInfo=None):
        super().__init__(patientInfo=patientInfo, name=name)

        self.dyn3DImageList = imageList

        if timingsList:
            self.timingsList = timingsList
        else:
            self.breathingPeriod = 4000
            self.inhaleDuration = 1800
            self.timingsList = self.prepareTimingsForViewer()


    def print_dynSeries_info(self, prefix=""):
        print(prefix + "Dyn series: " + self.name)
        print(prefix, len(self.dyn3DImageList), ' 3D images in the serie')


    def prepareTimingsForViewer(self):
        numberOfImages = len(self.dyn3DImageList)
        timingList = np.linspace(0, 4000, numberOfImages + 1)

        return timingList