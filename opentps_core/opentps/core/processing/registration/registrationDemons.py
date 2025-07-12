import numpy as np
import logging

from opentps.core.data.images._deformation3D import Deformation3D
from opentps.core.processing.registration.registration import Registration

logger = logging.getLogger(__name__)


class RegistrationDemons(Registration):
    """
    Perform Demons registration between fixed and moving images. inherited from Registration class.

    Attributes
    ----------
    fixed : Image3D
        Fixed image.
    moving : Image3D
        Moving image.
    baseResolution : float
        Base resolution for registration.
    tryGPU : bool
        Try to use GPU for registration.
    """
    def __init__(self, fixed, moving, baseResolution=2.5, tryGPU=True):

        Registration.__init__(self, fixed, moving)
        self.baseResolution = baseResolution
        self.tryGPU = tryGPU

    def compute(self):

        """Perform Demon registration between fixed and moving images.

            Returns
            -------
            numpy array
                Deformation from moving to fixed images.
            """

        scales = self.baseResolution * np.asarray([11.3137, 8.0, 5.6569, 4.0, 2.8284, 2.0, 1.4142, 1.0])
        iterations = [10, 10, 10, 10, 10, 10, 5, 2]

        deformation = Deformation3D()

        for s in range(len(scales)):

            # Compute grid for new scale
            newGridSize = np.array([round(self.fixed.spacing[1] / scales[s] * self.fixed.gridSize[0]),
                                    round(self.fixed.spacing[0] / scales[s] * self.fixed.gridSize[1]),
                                    round(self.fixed.spacing[2] / scales[s] * self.fixed.gridSize[2])])
            newVoxelSpacing = np.array([self.fixed.spacing[0] * (self.fixed.gridSize[1] - 1) / (newGridSize[1] - 1),
                                        self.fixed.spacing[1] * (self.fixed.gridSize[0] - 1) / (newGridSize[0] - 1),
                                        self.fixed.spacing[2] * (self.fixed.gridSize[2] - 1) / (newGridSize[2] - 1)])

            logger.info('Demons scale:' + str(s + 1) + '/' + str(len(scales)) + ' (' + str(round(newVoxelSpacing[0] * 1e2) / 1e2 ) + 'x' + str(round(newVoxelSpacing[1] * 1e2) / 1e2) + 'x' + str(round(newVoxelSpacing[2] * 1e2) / 1e2) + 'mm3)')

            # Resample fixed and moving images and deformation according to the considered scale (voxel spacing)
            # Resample fixed and moving images and deformation according to the considered scale (voxel spacing)
            fixedResampled = self.fixed.copy()
            fixedResampled.resample(newVoxelSpacing, newGridSize, self.fixed.origin, tryGPU=self.tryGPU)
            movingResampled = self.moving.copy()
            movingResampled.resample(fixedResampled.spacing, fixedResampled.gridSize, fixedResampled.origin, tryGPU=self.tryGPU)
            gradFixed = np.gradient(fixedResampled.imageArray)

            if s != 0:
                deformation.resample(fixedResampled.spacing, fixedResampled.gridSize, fixedResampled.origin, tryGPU=self.tryGPU)
            else:
                deformation.initFromImage(fixedResampled)

            for i in range(iterations[s]):

                # Deform moving image then reset displacement field
                deformed = deformation.deformImage(movingResampled, fillValue='closest')
                deformation.displacement = None

                ssd = self.computeSSD(fixedResampled.imageArray, deformed.imageArray)
                logger.info('Iteration ' + str(i + 1) + ': SSD=' + str(ssd))
                gradMoving = np.gradient(deformed.imageArray)
                squaredDiff = np.square(fixedResampled.imageArray - deformed.imageArray)
                squaredNormGrad = np.square(gradFixed[0] + gradMoving[0]) + np.square(
                    gradFixed[1] + gradMoving[1]) + np.square(gradFixed[2] + gradMoving[2])

                # demons formula
                deformation.setVelocityArrayXYZ(
                    deformation.velocity.imageArray[:, :, :, 0] + 2 * (fixedResampled.imageArray - deformed.imageArray) * (gradFixed[0] + gradMoving[0]) / ( squaredDiff + squaredNormGrad + 1e-5) * deformation.velocity.spacing[0],
                    deformation.velocity.imageArray[:, :, :, 1] + 2 * (fixedResampled.imageArray - deformed.imageArray) * (gradFixed[1] + gradMoving[1]) / ( squaredDiff + squaredNormGrad + 1e-5) * deformation.velocity.spacing[0],
                    deformation.velocity.imageArray[:, :, :, 2] + 2 * (fixedResampled.imageArray - deformed.imageArray) * (gradFixed[2] + gradMoving[2]) / ( squaredDiff + squaredNormGrad + 1e-5) * deformation.velocity.spacing[0])

                # Regularize velocity deformation and certainty
                self.regularizeField(deformation, filterType="Gaussian", sigma=1.25, tryGPU=self.tryGPU)

        self.deformed.setName(self.moving.name + '_registered_to_' + self.fixed.name)

        return deformation

