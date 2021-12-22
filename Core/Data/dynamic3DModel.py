import numpy as np
import logging

from Core.Data.patientData import PatientData
import Core.Processing.Registration.midPosition as midPosition

logger = logging.getLogger(__name__)


class Dynamic3DModel(PatientData):

    def __init__(self, name="new3DModel", midp=None, deformationList=[]):
        super().__init__()
        self.name = name
        self.midp = midp
        self.deformationList = deformationList

    def computeMidPositionImage(self, CT4D, refIndex=0, baseResolution=2.5, nbProcesses=-1):

        if refIndex >= len(CT4D.dyn3DImageList):
            logger.error("Reference index is out of bound")

        self.midp, self.deformationList = midPosition.compute(CT4D, refIndex=refIndex, baseResolution=baseResolution, nbProcesses=nbProcesses)


    def generate3DImage(self, phase, amplitude=1.0):
        if self.midp is None or self.deformationList is None:
            logger.error('Model is empty. Mid-position image and deformation fields must be computed first.')
            return

        phase *= len(self.deformationList)
        phase1 = np.floor(phase) % len(self.deformationList)
        phase2 = np.ceil(phase) % len(self.deformationList)

        field = self.deformationList[int(phase1)].copy()
        field.displacement = None
        if phase1 == phase2:
            field.velocity.data = amplitude * self.deformationList[int(phase1)].velocity.data
        else:
            w1 = abs(phase - np.ceil(phase))
            w2 = abs(phase - np.floor(phase))
            if abs(w1+w2-1.0) > 1e-6:
                logger.error('Error in phase interpolation.')
                return
            field.velocity = amplitude * (w1 * self.deformationList[int(phase1)].velocity + w2 * self.deformationList[int(phase2)].velocity)

        return field.deformImage(self.midp, fillValue='closest')
