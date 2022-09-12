
__all__ = ['DoseImage']


import numpy as np
import copy
import pydicom

from Core.Data.Images._image3D import Image3D
from Core.Data.Plan._rtPlan import RTPlan
from Core.Data.Images._ctImage import CTImage

class DoseImage(Image3D):

    def __init__(self, imageArray=None, name="Dose image", origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), seriesInstanceUID="", sopInstanceUID="", referencePlan:RTPlan = None, referenceCT:CTImage = None):
        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, angles=angles, seriesInstanceUID=seriesInstanceUID)
        self.seriesInstanceUID = seriesInstanceUID
        self.referenceCT = referenceCT
        self.sopInstanceUID = sopInstanceUID
        self.referencePlan = referencePlan

    @classmethod
    def fromImage3D(cls, image: Image3D):
        return cls(imageArray=copy.deepcopy(image.imageArray), origin=image.origin, spacing=image.spacing, angles=image.angles)


    def copy(self):
        return DoseImage(imageArray=copy.deepcopy(self.imageArray), name=self.name+'_copy', origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=pydicom.uid.generate_uid())


    def exportDicom(self, outputFile, planUID=[]):
        pass

    def dumpableCopy(self):
        dumpableDose = DoseImage(imageArray=self.imageArray, name=self.name, origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=self.seriesInstanceUID, frameOfReferenceUID=self.frameOfReferenceUID, sopInstanceUID=self.sopInstanceUID, planSOPInstanceUID=self.planSOPInstanceUID)
        # dumpableDose.patient = self.patient
        return dumpableDose

    @classmethod
    def createEmptyDoseWithSameMetaData(cls, image:Image3D):
        return cls(imageArray=np.zeros_like(image.imageArray), origin=image.origin, spacing=image.spacing, angles=image.angles)