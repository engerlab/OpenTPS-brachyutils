import numpy as np
import logging

from Core.Data.Images.image3D import Image3D
import Core.Processing.ImageProcessing.imageFilter3D as imageFilter3D

logger = logging.getLogger(__name__)


class Registration:

    def __init__(self, fixed, moving):
        self.fixed = fixed
        self.moving = moving
        self.deformed = []
        self.roiBox = []

    def regularizeField(self, field, filterType="Gaussian", sigma=1.0, cert=None):

        """Regularize vector field using Gaussian convolution or normalized convolution.

        Parameters
        ----------
        field : numpy array
            vector field to be regularized.
        filterType : string
            type of filtering to be applied on the field.
        sigma : double
            standard deviation of the Gaussian.
        cert : numpy array
            certainty map associated to the data.
        """

        if filterType == "Gaussian":
            field.velocity._imageArray[:, :, :, 0] = imageFilter3D.gaussConv(field.velocity._imageArray[:, :, :, 0], sigma=sigma)
            field.velocity._imageArray[:, :, :, 1] = imageFilter3D.gaussConv(field.velocity._imageArray[:, :, :, 1], sigma=sigma)
            field.velocity._imageArray[:, :, :, 2] = imageFilter3D.gaussConv(field.velocity._imageArray[:, :, :, 2], sigma=sigma)
            return

        if filterType == "NormalizedGaussian":
            if cert is None:
                cert = np.ones_like(field.velocity._imageArray[:, :, :, 0])
            field.velocity._imageArray[:, :, :, 0] = imageFilter3D.normGaussConv(field.velocity._imageArray[:, :, :, 0], cert, sigma)
            field.velocity._imageArray[:, :, :, 1] = imageFilter3D.normGaussConv(field.velocity._imageArray[:, :, :, 1], cert, sigma)
            field.velocity._imageArray[:, :, :, 2] = imageFilter3D.normGaussConv(field.velocity._imageArray[:, :, :, 2], cert, sigma)
            return

        else:
            logger.error("Error: unknown filter for field regularizeField")
            return

    def setROI(self, ROI):
        profile = np.sum(ROI.Mask, (0, 2))
        box = [[0, 0, 0], [0, 0, 0]]
        x = np.where(np.any(ROI.Mask, axis=(1, 2)))[0]
        y = np.where(np.any(ROI.Mask, axis=(0, 2)))[0]
        z = np.where(np.any(ROI.Mask, axis=(0, 1)))[0]

        # box start
        box[0][0] = x[0]
        box[0][1] = y[0]
        box[0][2] = z[0]

        # box stop
        box[1][0] = x[-1]
        box[1][1] = y[-1]
        box[1][2] = z[-1]

        self.roiBox = box

    def translateOrigin(self, Image, translation):
        Image._origin[0] += translation[0]
        Image._origin[1] += translation[1]
        Image._origin[2] += translation[2]

        Image.VoxelX = Image._origin[0] + np.arange(Image.gridSize()[0]) * Image._spacing[0]
        Image.VoxelY = Image._origin[1] + np.arange(Image.gridSize()[1]) * Image._spacing[1]
        Image.VoxelZ = Image._origin[2] + np.arange(Image.gridSize()[2]) * Image._spacing[2]

    def translateAndComputeSSD(self, translation=None):

        if translation is None:
            translation = [0.0, 0.0, 0.0]

        # crop fixed image to ROI box
        if (self.roiBox == []):
            fixed = self.fixed._imageArray
            origin = self.fixed._origin
            gridSize = self.fixed.gridSize()
        else:
            start = self.roiBox[0]
            stop = self.roiBox[1]
            fixed = self.fixed._imageArray[start[0]:stop[0], start[1]:stop[1], start[2]:stop[2]]
            origin = self.fixed._origin + np.array(
                [start[1] * self.fixed._spacing[0], start[0] * self.fixed._spacing[1],
                 start[2] * self.fixed._spacing[2]])
            gridSize = list(fixed.shape)

        logger.info("Translation: " + str(translation))

        # deform moving image
        self.deformed = self.moving.copy()
        self.translateOrigin(self.deformed, translation)
        self.deformed.resample(gridSize, origin, self.fixed._spacing)

        # compute metric
        ssd = self.computeSSD(fixed, self.deformed._imageArray)
        return ssd

    def computeSSD(self, fixed, deformed):
        # compute metric
        ssd = np.sum(np.power(fixed - deformed, 2))
        return ssd

    def resampleMovingImage(self, keepFixedShape=True):
        if self.fixed == [] or self.moving == []:
            logger.error("Image not defined in registration object")
            return

        if keepFixedShape == True:
            resampled = self.moving.copy()
            resampled.resample_image(self.fixed.gridSize(), self.fixed._origin, self.fixed._spacing)

        else:
            X_min = min(self.fixed._origin[0], self.moving._origin[0])
            Y_min = min(self.fixed._origin[1], self.moving._origin[1])
            Z_min = min(self.fixed._origin[2], self.moving._origin[2])

            X_max = max(self.fixed.VoxelX[-1], self.moving.VoxelX[-1])
            Y_max = max(self.fixed.VoxelY[-1], self.moving.VoxelY[-1])
            Z_max = max(self.fixed.VoxelZ[-1], self.moving.VoxelZ[-1])

            origin = [X_min, Y_min, Z_min]
            gridSizeX = round((X_max - X_min) / self.fixed._spacing[0])
            gridSizeY = round((Y_max - Y_min) / self.fixed._spacing[1])
            gridSizeZ = round((Z_max - Z_min) / self.fixed._spacing[2])
            gridSize = [gridSizeX, gridSizeY, gridSizeZ]

            resampled = self.moving.copy()
            resampled.resample(gridSize, origin, self.fixed._spacing)

        return resampled

    def resampleFixedImage(self):

        if (self.fixed == [] or self.moving == []):
            logger.error("Image not defined in registration object")
            return

        X_min = min(self.fixed._origin[0], self.moving._origin[0])
        Y_min = min(self.fixed._origin[1], self.moving._origin[1])
        Z_min = min(self.fixed._origin[2], self.moving._origin[2])

        X_max = max(self.fixed.VoxelX[-1], self.moving.VoxelX[-1])
        Y_max = max(self.fixed.VoxelY[-1], self.moving.VoxelY[-1])
        Z_max = max(self.fixed.VoxelZ[-1], self.moving.VoxelZ[-1])

        origin = [X_min, Y_min, Z_min]
        gridSizeX = round((X_max - X_min) / self.fixed._spacing[0])
        gridSizeY = round((Y_max - Y_min) / self.fixed._spacing[1])
        gridSizeZ = round((Z_max - Z_min) / self.fixed._spacing[2])
        gridSize = [gridSizeX, gridSizeY, gridSizeZ]

        resampled = self.fixed.copy()
        resampled.resample(gridSize, origin, self.fixed._spacing)

        return resampled

    def computeImageDifference(self, keepFixedShape=True):

        if (self.fixed == [] or self.moving == []):
            logger.error("Image not defined in registration object")
            return

        if (keepFixedShape == True):
            diff = self.resampleMovingImage(keepFixedShape=True)
            diff.data = self.fixed._imageArray - diff.data

        else:
            diff = self.resampleMovingImage(keepFixedShape=False)
            tmp = self.resampleFixedImage()
            diff.data = tmp.data - diff.data

        return diff
