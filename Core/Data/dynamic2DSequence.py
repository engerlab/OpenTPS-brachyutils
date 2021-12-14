import numpy as np

from Core.Data.patientData import PatientData

class Dynamic2DSequence(PatientData):

    def __init__(self, imageList = [], timingsList = [], sequenceName = "newSequence"):
        super().__init__()
        self.sequenceName = sequenceName
        self.dyn2DImageList = imageList
        self.timingsList = timingsList
        self.breathingPeriod = 4000
        self.inhaleDuration = 1800


    def print_dynSeries_info(self, prefix=""):
        print(prefix + "Dyn series: " + self.SequenceName)
        print(prefix, len(self.dyn2DImageList), ' 3D images in the serie')


    def prepareTimingsForViewer(self):

        numberOfImages = len(self.dyn2DImageList)
        timingList = np.linspace(0, 4000, numberOfImages+1)

        return timingList