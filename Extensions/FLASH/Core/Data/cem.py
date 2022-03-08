import numpy as np

from Core.Data.Images.image2D import Image2D
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Extensions.FLASH.Core.Data.abstractCTObject import AbstractCTObject


class CEM(AbstractCTObject, Image2D):
    def __init__(self):
        Image2D.__init__(self)

    def fromBeam(self, beam:PlanIonBeam):
        pass

    def computeROI(self) -> ROIMask:
        pass
