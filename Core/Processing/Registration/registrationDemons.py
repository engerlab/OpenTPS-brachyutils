import numpy as np
import logging

from Core.Data.Images.deformationField import DeformationField
from Core.Processing.Registration.registration import Registration


class RegistrationDemons(Registration):

    def __init__(self, fixed, moving, nIter=15):

        Registration.__init__(self, fixed, moving)
        self.nIter = nIter

    def compute(self):

        # Resample moving image
        if not self.fixed.is_same_grid(self.moving):
            self.moving = self.resampleMovingImage()

        # Initialization
        gradFixed = np.gradient(self.fixed.Image)
        deformed = self.moving.Image.copy()
        field = DeformationField()
        field.initFieldWithZeros(self.fixed.getGridSize(), origin=self.fixed.origin,
                                 spacing=self.fixed.spacing)

        # Iterative loop
        for i in range(self.nIter):
            ssd = self.computeSSD(self.fixed.Image, deformed)
            print('Iteration ' + str(i + 1) + ': SSD=' + str(ssd))
            gradMoving = np.gradient(deformed)
            squaredDiff = np.square(self.fixed.Image - deformed)
            squaredNormGrad = np.square(gradFixed[0] + gradMoving[0]) + np.square(
                gradFixed[1] + gradMoving[1]) + np.square(gradFixed[2] + gradMoving[2])

            # demons formula
            field.velocity[:, :, :, 0] += 2 * (self.fixed.Image - deformed) * (gradFixed[0] + gradMoving[0]) / (
                    squaredDiff + squaredNormGrad + 1e-5)
            field.velocity[:, :, :, 1] += 2 * (self.fixed.Image - deformed) * (gradFixed[1] + gradMoving[1]) / (
                    squaredDiff + squaredNormGrad + 1e-5)
            field.velocity[:, :, :, 2] += 2 * (self.fixed.Image - deformed) * (gradFixed[2] + gradMoving[2]) / (
                    squaredDiff + squaredNormGrad + 1e-5)

            # Regularization (Gaussian filter)
            self.fieldRegularization(field, filterType="Gaussian", sigma=1.0)

            # deformation
            deformed = field.deformImage(self.moving)

        self.deformed = self.moving.copy()
        self.deformed.Image = deformed

        return field
