import numpy as np
from pydicom.uid import generate_uid

from opentps.core.data._patientData import PatientData


class Dynamic3DSequence(PatientData):

    LOOPED_MODE = 'LOOP'
    ONESHOT_MODE = 'OS'

    def __init__(self, dyn3DImageList = [], timingsList = [], name="3D Dyn Seq", repetitionMode='LOOP'):
        super().__init__(name=name)

        self.dyn3DImageList = self.sortImgsByName(dyn3DImageList)

        if len(timingsList) > 0:
            self.timingsList = timingsList
        else:
            self.breathingPeriod = 4000
            self.inhaleDuration = 1800
            self.prepareTimings()

        # self.isDynamic = True
        self.repetitionMode = repetitionMode

        print('Dynamic 3D Sequence Created with ', len(self.dyn3DImageList), 'images')
        for img in self.dyn3DImageList:
            print('   ', img.name)

    @staticmethod
    def fromImagesInPatientList(selectedImages, newName):
        newSeq = Dynamic3DSequence(dyn3DImageList=selectedImages, name=newName)

        for image in selectedImages:
            patient = image.patient
            patient.removePatientData(image)

        newSeq.seriesInstanceUID = generate_uid()
        patient.appendPatientData(newSeq)


    def __str__(self):
        s = "Dyn series: " + self.name + '\n'
        for image in self.dyn3DImageList:
            s += str(image) + '\n'

        return s

    def __len__(self):
        return len(self.dyn3DImageList)


    def print_dynSeries_info(self, prefix=""):
        print(prefix + "Dyn series: " + self.name)
        print(prefix, len(self.dyn3DImageList), ' 3D images in the serie')


    def prepareTimings(self):
        numberOfImages = len(self.dyn3DImageList)
        self.timingsList = np.linspace(0, 4000, numberOfImages + 1)
        # print('in dynamic3DSequence prepareTimings', self.timingsList)


    def sortImgsByName(self, imgList):
        imgList = sorted(imgList, key=lambda img: img.name)
        return imgList


    def resampleOn(self, otherImage, fillValue=0, outputType=None, tryGPU=True):
        for i in range(len(self.dyn3DImageList)):
            self.dyn3DImageList[i].resample(otherImage.spacing, otherImage.gridSize, otherImage.origin, fillValue=fillValue, outputType=outputType, tryGPU=tryGPU)


    def resample(self, spacing, gridSize, origin, fillValue=0, outputType=None, tryGPU=True):
        for i in range(len(self.dyn3DImageList)):
            self.dyn3DImageList[i].resample(spacing, gridSize, origin, fillValue=fillValue, outputType=outputType, tryGPU=tryGPU)


    def dumpableCopy(self):
        dumpableImageCopiesList = [image.dumpableCopy() for image in self.dyn3DImageList]
        dumpableSeq = Dynamic3DSequence(dyn3DImageList=dumpableImageCopiesList, timingsList=self.timingsList, name=self.name)
        # dumpableSeq.patient = self.patient
        return dumpableSeq