import numpy as np
import logging

from Core.Data.Images.deformation3D import Deformation3D
from Core.Processing.Registration.registration import Registration

logger = logging.getLogger(__name__)


class RegistrationDemons(Registration):

    def __init__(self, fixed, moving, baseResolution=2.5):

        Registration.__init__(self, fixed, moving)
        self.baseResolution = baseResolution

    def compute(self):

        scales = self.baseResolution * np.asarray([11.3137, 8.0, 5.6569, 4.0, 2.8284, 2.0, 1.4142, 1.0])
        iterations = [10, 10, 10, 10, 10, 10, 5, 2]

        deformation = Deformation3D()

        for s in range(len(scales)):

            # Compute grid for new scale
            newGridSize = [round(self.fixed.spacing[1] / scales[s] * self.fixed.getGridSize()[0]),
                           round(self.fixed.spacing[0] / scales[s] * self.fixed.getGridSize()[1]),
                           round(self.fixed.spacing[2] / scales[s] * self.fixed.getGridSize()[2])]
            newVoxelSpacing = [self.fixed.spacing[0] * (self.fixed.getGridSize()[1] - 1) / (newGridSize[1] - 1),
                               self.fixed.spacing[1] * (self.fixed.getGridSize()[0] - 1) / (newGridSize[0] - 1),
                               self.fixed.spacing[2] * (self.fixed.getGridSize()[2] - 1) / (newGridSize[2] - 1)]

            logger.info('Demons scale:' + str(s + 1) + '/' + str(len(scales)) + ' (' + str(round(newVoxelSpacing[0] * 1e2) / 1e2 ) + 'x' + str(round(newVoxelSpacing[1] * 1e2) / 1e2) + 'x' + str(round(newVoxelSpacing[2] * 1e2) / 1e2) + 'mm3)')

            # Resample fixed and moving images and deformation according to the considered scale (voxel spacing)
            fixedResampled = self.fixed.copy()
            fixedResampled.resample(newGridSize, self.fixed.origin, newVoxelSpacing)
            movingResampled = self.moving.copy()
            movingResampled.resample(fixedResampled.getGridSize(), fixedResampled.origin, fixedResampled.spacing)
            gradFixed = np.gradient(fixedResampled.data)

            if s != 0:
                deformation.resampleToImageGrid(fixedResampled)
            else:
                deformation.initFromImage(fixedResampled)

            for i in range(iterations[s]):

                # Deform moving image
                deformed = deformation.deformImage(movingResampled, fillValue='closest')

                ssd = self.computeSSD(fixedResampled.data, deformed.data)
                logger.info('Iteration ' + str(i + 1) + ': SSD=' + str(ssd))
                gradMoving = np.gradient(deformed.data)
                squaredDiff = np.square(fixedResampled.data - deformed.data)
                squaredNormGrad = np.square(gradFixed[0] + gradMoving[0]) + np.square(
                    gradFixed[1] + gradMoving[1]) + np.square(gradFixed[2] + gradMoving[2])

                # demons formula
                deformation.velocity.data[:, :, :, 0] += 2 * (fixedResampled.data - deformed.data) * (
                            gradFixed[0] + gradMoving[0]) / ( squaredDiff + squaredNormGrad + 1e-5) * \
                                                         deformation.velocity.spacing[0]
                deformation.velocity.data[:, :, :, 1] += 2 * (fixedResampled.data - deformed.data) * (
                            gradFixed[1] + gradMoving[1]) / ( squaredDiff + squaredNormGrad + 1e-5) * \
                                                         deformation.velocity.spacing[0]
                deformation.velocity.data[:, :, :, 2] += 2 * (fixedResampled.data - deformed.data) * (
                            gradFixed[2] + gradMoving[2]) / ( squaredDiff + squaredNormGrad + 1e-5) * \
                                                         deformation.velocity.spacing[0]

                # Regularize velocity deformation and certainty
                self.regularizeField(deformation, filterType="Gaussian", sigma=1.25)

        self.deformed = deformation.deformImage(self.moving, fillValue='closest')

        return deformation

