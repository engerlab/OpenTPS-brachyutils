import numpy as np
from pydicom.uid import generate_uid

from opentps.core.data._patientData import PatientData


class Dynamic3DSequence(PatientData):
    """
    Dynamic 3D sequence class. Inherits from PatientData.

    Attributes
    ----------
    name : str (default = "3D Dyn Seq")
        Name of the dynamic 3D sequence.
    dyn3DImageList : list
        List of 3D images.
    timingsList : array_like
        List of timings.
    repetitionMode : str (default = 'LOOP')
        Repetition mode of the dynamic 3D sequence.
    If no timingsList is provided, the default parameters for timings are:
        breathingPeriod = 4000
        inhaleDuration = 1800
    """

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
        """
        Create a new dynamic 3D sequence from a list of 3D images. The 3D images are removed from the patient. The new dynamic 3D sequence is added to the patient.

        Parameters
        ----------
        selectedImages : list[3DImage]
            List of 3D images.
        newName : str
            Name of the new dynamic 3D sequence.
        """
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
        """
        Print the information of the dynamic 3D sequence.
        """
        print(prefix + "Dyn series: " + self.name)
        print(prefix, len(self.dyn3DImageList), ' 3D images in the serie')


    def prepareTimings(self):
        """
        Prepare the timings of the dynamic 3D sequence in the case where it represent one breathing period.
        """
        numberOfImages = len(self.dyn3DImageList)
        self.timingsList = np.linspace(0, self.breathingPeriod, numberOfImages + 1)
        # print('in dynamic3DSequence prepareTimings', self.timingsList)


    def sortImgsByName(self, imgList):
        """
        Sort the 3D images by name.

        Parameters
        ----------
        imgList : list[3DImage]
            List of 3D images.

        Returns
        -------
        list[3DImage]
            Sorted list of 3D images.
        """
        imgList = sorted(imgList, key=lambda img: img.name)
        return imgList


    def resampleOn(self, otherImage, fillValue=0, outputType=None, tryGPU=True):
        """
        Resample the dynamic 3D sequence on another image.

        Parameters
        ----------
        otherImage : 3DImage
            Image on which the dynamic 3D sequence is resampled.
        fillValue : int (default = 0)
            Fill value.
        outputType : str (default = None)
            Output type.
        tryGPU : bool (default = True)
            Boolean indicating if the GPU is used.
        """
        for i in range(len(self.dyn3DImageList)):
            self.dyn3DImageList[i].resample(otherImage.spacing, otherImage.gridSize, otherImage.origin, fillValue=fillValue, outputType=outputType, tryGPU=tryGPU)


    def resample(self, spacing, gridSize, origin, fillValue=0, outputType=None, tryGPU=True):
        """
        Resample the dynamic 3D sequence.

        Parameters
        ----------
        spacing : array_like
            Spacing in mm.
        gridSize : array_like
            Grid size.
        origin : array_like
            Origin.
        fillValue : int (default = 0)
            Fill value.
        outputType : str (default = None)
            Output type.
        tryGPU : bool (default = True)
            Boolean indicating if the GPU is used.
        """
        for i in range(len(self.dyn3DImageList)):
            self.dyn3DImageList[i].resample(spacing, gridSize, origin, fillValue=fillValue, outputType=outputType, tryGPU=tryGPU)


    def dumpableCopy(self):
        """
        Create a dumpable copy of the dynamic 3D sequence.

        Returns
        -------
        Dynamic3DSequence
            Dumpable copy of the dynamic 3D sequence.
        """
        dumpableImageCopiesList = [image.dumpableCopy() for image in self.dyn3DImageList]
        dumpableSeq = Dynamic3DSequence(dyn3DImageList=dumpableImageCopiesList, timingsList=self.timingsList, name=self.name)
        # dumpableSeq.patient = self.patient
        return dumpableSeq