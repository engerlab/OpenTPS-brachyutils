from typing import Optional

import numpy as np

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.image3D import Image3D
from Core.Data.Plan.planIonBeam import PlanIonBeam
import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D
from Core.Processing.ImageProcessing import resampler3D


class RSPImage(Image3D):
    def __init__(self, imageArray=None, name="RSP image", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1),
                 angles=(0, 0, 0), seriesInstanceUID="", frameOfReferenceUID="", sliceLocation=[], sopInstanceUIDs=[]):
        super().__init__(imageArray=imageArray, name=name, patientInfo=patientInfo, origin=origin, spacing=spacing,
                         angles=angles, seriesInstanceUID=seriesInstanceUID)
        self.frameOfReferenceUID = frameOfReferenceUID
        self.seriesInstanceUID = seriesInstanceUID
        self.sliceLocation = sliceLocation
        self.sopInstanceUIDs = sopInstanceUIDs

    def __str__(self):
        return "RSP image: " + self.seriesInstanceUID

    @classmethod
    def fromImage3D(cls, image: Image3D):
        return cls(imageArray=image.imageArray, origin=image.origin, spacing=image.spacing, angles=image.angles,
                   seriesInstanceUID=image.seriesInstanceUID)

    @classmethod
    def fromCT(cls, ct:CTImage, calibration:AbstractCTCalibration, energy:float=100.):
        newRSPImage = cls.fromImage3D(ct)
        newRSPImage.imageArray = calibration.convertHU2RSP(ct.imageArray, energy)

        return newRSPImage

    def computeCumulativeWEPL(self, beam:Optional[PlanIonBeam]=None, sad=np.Inf, roi=None) -> Image3D:
        if not (beam is None):
            rspIEC = imageTransform3D.dicomToIECGantry(self, beam, fillValue=0., cropROI=roi, cropDim0=True, cropDim1=True, cropDim2=False)
        else:
            rspIEC = self.__class__.fromImage3D(self)

        rspIEC.imageArray = np.cumsum(rspIEC.imageArray, axis=2)*rspIEC.spacing[2]

        if not (beam is None):
            outImage = imageTransform3D.iecGantryToDicom(rspIEC, beam, 0.)
            outImage = resampler3D.resampleImage3DOnImage3D(outImage, self, inPlace=True, fillValue=0.)
        else:
            outImage = rspIEC

        return outImage
