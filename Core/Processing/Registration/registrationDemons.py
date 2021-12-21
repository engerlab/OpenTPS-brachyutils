import numpy as np
import logging

from Core.Data.Images.deformation3D import Deformation3D
from Core.Processing.Registration.registration import Registration

logger = logging.getLogger(__name__)


class RegistrationDemons(Registration):

    def __init__(self, fixed, moving, nIter=15):

        Registration.__init__(self, fixed, moving)
        self.nIter = nIter

    def compute(self):

        # Resample moving image
        if not self.fixed.hasSameGrid(self.moving):
            self.moving = self.resampleMovingImage()

        # Initialization
        gradFixed = np.gradient(self.fixed.data)
        self.deformed = self.moving.copy()
        field = Deformation3D()
        field.initFromImage(self.fixed)

        # Iterative loop
        for i in range(self.nIter):
            ssd = self.computeSSD(self.fixed.data, self.deformed.data)
            logger.info('Iteration ' + str(i + 1) + ': SSD=' + str(ssd))
            gradMoving = np.gradient(self.deformed.data)
            squaredDiff = np.square(self.fixed.data - self.deformed.data)
            squaredNormGrad = np.square(gradFixed[0] + gradMoving[0]) + np.square(
                gradFixed[1] + gradMoving[1]) + np.square(gradFixed[2] + gradMoving[2])

            # demons formula
            field.velocity.data[:, :, :, 0] += 2 * (self.fixed.data - self.deformed.data) * (gradFixed[0] + gradMoving[0]) / (
                    squaredDiff + squaredNormGrad + 1e-5)
            field.velocity.data[:, :, :, 1] += 2 * (self.fixed.data - self.deformed.data) * (gradFixed[1] + gradMoving[1]) / (
                    squaredDiff + squaredNormGrad + 1e-5)
            field.velocity.data[:, :, :, 2] += 2 * (self.fixed.data - self.deformed.data) * (gradFixed[2] + gradMoving[2]) / (
                    squaredDiff + squaredNormGrad + 1e-5)

            # Regularization (Gaussian filter)
            self.regularizeField(field, filterType="Gaussian", sigma=1.0)

            # deformation
            self.deformed = field.deformImage(self.moving)

        return field
