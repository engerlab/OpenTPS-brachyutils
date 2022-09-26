
__all__ = ['CTImage']

import pydicom
import copy

from opentps.core.data.images._image3D import Image3D


class CTImage(Image3D):
    def __init__(self, imageArray=None, name="CT image", origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0),
                 seriesInstanceUID="", frameOfReferenceUID="", sliceLocation=None, sopInstanceUIDs=None, patient=None):
        self.frameOfReferenceUID = frameOfReferenceUID
        self.sliceLocation = sliceLocation
        self.sopInstanceUIDs = sopInstanceUIDs

        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, angles=angles,
                         seriesInstanceUID=seriesInstanceUID, patient=patient)
    
    def __str__(self):
        return "CT image: " + self.seriesInstanceUID

    @classmethod
    def fromImage3D(cls, image, **kwargs):
        dic = {'imageArray': copy.deepcopy(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient}
        dic.update(kwargs)
        return cls(**dic)

    def copy(self):
        return CTImage(imageArray=copy.deepcopy(self.imageArray), name=self.name+'_copy', origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=pydicom.uid.generate_uid())

    # def dumpableCopy(self):
    #
    #     dumpableImg = CTImage(imageArray=self.imageArray, name=self.name, patientInfo=self.patientInfo, origin=self.origin,
    #             spacing=self.spacing, angles=self.angles, seriesInstanceUID=self.seriesInstanceUID,
    #             frameOfReferenceUID=self.frameOfReferenceUID, sliceLocation=self.sliceLocation,
    #             sopInstanceUIDs=self.sopInstanceUIDs)

        # dumpableImg.patient = self.patient

        return dumpableImg

