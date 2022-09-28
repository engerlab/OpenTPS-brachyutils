import numpy as np
import logging

from opentps.core.data._patientData import PatientData
import opentps.core.processing.registration.midPosition as midPosition
from concurrent.futures import ProcessPoolExecutor

logger = logging.getLogger(__name__)


class Dynamic3DModel(PatientData):

    def __init__(self, name="new3DModel", midp=None, deformationList=[]):
        super().__init__()
        self.name = name
        self.midp = midp
        self.deformationList = deformationList

    def copy(self):
        return Dynamic3DModel(midp=self.midp, deformationList=self.deformationList)

    def computeMidPositionImage(self, CT4D, refIndex=0, baseResolution=2.5, nbProcesses=1, tryGPU=True):
        """Compute the mid-position image from the 4DCT by means of deformable registration between breathing phases.

            Parameters
            ----------
            CT4D : dynamic3DSequence
                4D CT
            refIndex : int
                index of the reference phase in the 4D CT (default = 0)
            baseResolution : float
                smallest voxel resolution for deformable registration multi-scale processing
            nbProcesses : int
                number of processes to be used in the deformable registration
            """

        if refIndex >= len(CT4D.dyn3DImageList):
            logger.error("Reference index is out of bound")

        self.midp, self.deformationList = midPosition.compute(CT4D, refIndex=refIndex, baseResolution=baseResolution, nbProcesses=nbProcesses, tryGPU=tryGPU)
        self.midp.name = 'MidP Image'


    def generate3DDeformation(self, phase, amplitude=1.0):
        """Generate a deformation from the mid-position to a specified phase of the breathing cycle, optionally using a magnification factor for this deformation.

            Parameters
            ----------
            phase : float
                respiratory phase indicating which (combination of) deformation fields to be used in image generation
            amplitude : float
                magnification factor applied on the deformation to the selected phase

            Returns
            -------
            Deformation3D
                generated deformation.
            """

        if self.midp is None or self.deformationList is None:
            logger.error('Model is empty. Mid-position image and deformation fields must be computed first using computeMidPositionImage().')
            return

        phase *= len(self.deformationList)
        phase1 = np.floor(phase) % len(self.deformationList)
        phase2 = np.ceil(phase) % len(self.deformationList)

        field = self.deformationList[int(phase1)].copy()
        if phase1 == phase2:
            field.setVelocityArray(amplitude * self.deformationList[int(phase1)].velocity.imageArray)
        else:
            w1 = abs(phase - np.ceil(phase))
            w2 = abs(phase - np.floor(phase))
            if abs(w1+w2-1.0) > 1e-6:
                logger.error('Error in phase interpolation.')
                return
            field.setVelocityArray(amplitude * (w1 * self.deformationList[int(phase1)].velocity.imageArray + w2 * self.deformationList[int(phase2)].velocity.imageArray))

        return field


    def generate3DImage(self, phase, amplitude=1.0, tryGPU=True):
        """Generate a 3D image by deforming the mid-position according to a specified phase of the breathing cycle, optionally using a magnification factor for this deformation.

            Parameters
            ----------
            phase : float
                respiratory phase indicating which (combination of) deformation fields to be used in image generation
            amplitude : float
                magnification factor applied on the deformation to the selected phase

            Returns
            -------
            image3D
                generated 3D image.
            """

        field = self.generate3DDeformation(phase, amplitude)
        return field.deformImage(self.midp, fillValue='closest', tryGPU=tryGPU)


    def computeAllDisplacementFields(self): ## not working for now, the field.displacement is None after the function

        print('Compute all model displacement fields using multiprocessing')

        with ProcessPoolExecutor() as executor:
            executor.map(self.computeDisplacementField, self.deformationList)


    def computeDisplacementField(self, field):
        field.displacement = field.velocity.exponentiateField()


    def dumpableCopy(self):

        dumpableDefList = [deformation.dumpableCopy() for deformation in self.deformationList]
        dumpableModel = Dynamic3DModel(name=self.name, midp=self.midp.dumpableCopy(), deformationList=dumpableDefList)
        dumpableModel.patient = self.patient
        return dumpableModel
