
__all__ = ['DoseImage']


import numpy as np
import copy
import pydicom

from opentps.core.data.images._image3D import Image3D
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data.images._ctImage import CTImage

class DoseImage(Image3D):

    def __init__(self, imageArray=None, name="Dose image", origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0),
                 seriesInstanceUID=None, sopInstanceUID=None, referencePlan:RTPlan = None, referenceCT:CTImage = None, patient=None):
        self.referenceCT = referenceCT
        self.sopInstanceUID = sopInstanceUID
        self.referencePlan = referencePlan

        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, angles=angles,
                         seriesInstanceUID=seriesInstanceUID, patient=patient)

    @classmethod
    def fromImage3D(cls, image: Image3D, **kwargs):
        dic = {'imageArray': copy.deepcopy(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient}
        dic.update(kwargs)

        cl = cls(**dic)
        if isinstance(image, DoseImage):
            cl.referenceCT = image.referenceCT
            cl.referencePlan = image.referencePlan
        return cl

    def copy(self):
        dose = DoseImage(imageArray=copy.deepcopy(self.imageArray), name=self.name+'_copy', origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=pydicom.uid.generate_uid(), referencePlan=self.referencePlan, referenceCT=self.referenceCT)
        dose.patient = self.patient
        return dose

    def exportDicom(self, outputFile, planUID=[]):
        pass

    def dumpableCopy(self):
        dumpableDose = DoseImage(imageArray=self.imageArray, name=self.name, origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=self.seriesInstanceUID, frameOfReferenceUID=self.frameOfReferenceUID, sopInstanceUID=self.sopInstanceUID, planSOPInstanceUID=self.planSOPInstanceUID)
        # dumpableDose.patient = self.patient
        return dumpableDose

    @classmethod
    def createEmptyDoseWithSameMetaData(cls, image:Image3D, **kwargs):
        dic = {'imageArray': np.zeros_like(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient}
        dic.update(kwargs)

        cl = cls(**dic)
        if isinstance(image, DoseImage):
            cl.referenceCT = image.referenceCT
            cl.referencePlan = image.referencePlan
        return cl