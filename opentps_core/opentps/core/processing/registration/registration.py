import numpy as np
import logging

import opentps.core.processing.imageProcessing.filter3D as imageFilter3D

logger = logging.getLogger(__name__)


class Registration:
    """
    Base class for registration.

    Attributes
    ----------
    fixed : image3D
        fixed image.
    moving : image3D
        moving image.
    deformed : image3D
        deformed moving image.
    roiBox : list
        region of interest for registration.
    """
    def __init__(self, fixed, moving):
        self.fixed = fixed
        self.moving = moving
        self.deformed = []
        self.roiBox = []

    def regularizeField(self, field, filterType="Gaussian", sigma=1.0, cert=None, tryGPU=True):

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
            field.setVelocityArrayXYZ(imageFilter3D.gaussConv(field.velocity.imageArray[:, :, :, 0], sigma=sigma, tryGPU=tryGPU),
                imageFilter3D.gaussConv(field.velocity.imageArray[:, :, :, 1], sigma=sigma, tryGPU=tryGPU),
                imageFilter3D.gaussConv(field.velocity.imageArray[:, :, :, 2], sigma=sigma, tryGPU=tryGPU))
            return

        if filterType == "NormalizedGaussian":
            if cert is None:
                cert = np.ones_like(field.velocity.imageArray[:, :, :, 0])
            field.setVelocityArrayXYZ(imageFilter3D.normGaussConv(field.velocity.imageArray[:, :, :, 0], cert, sigma, tryGPU=tryGPU),
                imageFilter3D.normGaussConv(field.velocity.imageArray[:, :, :, 1], cert, sigma, tryGPU=tryGPU),
                imageFilter3D.normGaussConv(field.velocity.imageArray[:, :, :, 2], cert, sigma, tryGPU=tryGPU))
            return

        else:
            logger.error("Error: unknown filter for field regularizeField")
            return

    def setROI(self, ROI):
        """
        Set the ROI to be used for registration.

        Parameters
        ----------
        ROI : roiMask
            ROI to be used for registration.
        """
        profile = np.sum(ROI.imageArray, (0, 2))
        box = [[0, 0, 0], [0, 0, 0]]
        x = np.where(np.any(ROI.imageArray, axis=(1, 2)))[0]
        y = np.where(np.any(ROI.imageArray, axis=(0, 2)))[0]
        z = np.where(np.any(ROI.imageArray, axis=(0, 1)))[0]

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
        """
        Translate the origin of an image.

        Parameters
        ----------
        Image : 3DImage
            Image from which the origin is translated.
        translation : list
            Translation vector.
        """
        Image.origin[0] += translation[0]
        Image.origin[1] += translation[1]
        Image.origin[2] += translation[2]

        Image.VoxelX = Image.origin[0] + np.arange(Image.gridSize[0]) * Image.spacing[0]
        Image.VoxelY = Image.origin[1] + np.arange(Image.gridSize[1]) * Image.spacing[1]
        Image.VoxelZ = Image.origin[2] + np.arange(Image.gridSize[2]) * Image.spacing[2]

    def translateAndComputeSSD(self, translation=None, tryGPU=True):
        """
        Translate the moving image and compute the SSD metric.
        Parameters
        ----------
        translation : list
            Translation vector.
        tryGPU : bool
            If True, try to use GPU.

        Returns
        -------
        ssd : double
            SSD metric value after translation.
        """

        if translation is None:
            translation = [0.0, 0.0, 0.0]

        # crop fixed image to ROI box
        if (self.roiBox == []):
            fixed = self.fixed.imageArray
            origin = self.fixed.origin
            gridSize = self.fixed.gridSize
        else:
            start = self.roiBox[0]
            stop = self.roiBox[1]
            fixed = self.fixed.imageArray[start[0]:stop[0], start[1]:stop[1], start[2]:stop[2]]
            origin = self.fixed.origin + np.array(
                [start[1] * self.fixed.spacing[0], start[0] * self.fixed.spacing[1],
                 start[2] * self.fixed.spacing[2]])
            gridSize = list(fixed.shape)

        logger.info("Translation: " + str(translation))

        # deform moving image
        self.deformed = self.moving.copy()
        self.translateOrigin(self.deformed, translation)
        self.deformed.resample(self.fixed.spacing, gridSize, origin, tryGPU=tryGPU)

        # compute metric
        ssd = self.computeSSD(fixed, self.deformed.imageArray)
        return ssd

    def computeSSD(self, fixed, deformed):
        """
        Compute the SSD metric between two images.

        Parameters
        ----------
        fixed : numpy array
            Fixed image.
        deformed : numpy array
            Deformed image.

        Returns
        -------
        ssd : double
            SSD metric value.
        """
        # compute metric
        ssd = np.sum(np.power(fixed - deformed, 2))
        return ssd

    def resampleMovingImage(self, keepFixedShape=True, tryGPU=True):
        """
        Resample the moving image to the fixed image grid.

        Parameters
        ----------
        keepFixedShape : bool
            If True, the moving image is resampled to the fixed image grid.
            If False, the fixed image is resampled to the moving image grid.
        tryGPU : bool
            If True, try to use GPU.

        Returns
        -------
        resampled : 3DImage
            Resampled image.
        """
        if self.fixed == [] or self.moving == []:
            logger.error("Image not defined in registration object")
            return

        if keepFixedShape == True:
            resampled = self.moving.copy()
            print('in registration resampleMovingImage')
            resampled.resampleOpenMP(self.fixed.gridSize(), self.fixed._origin, self.fixed._spacing)

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
            resampled.resampleOpenMP(gridSize, origin, self.fixed._spacing, tryGPU=tryGPU)

        return resampled

    def resampleFixedImage(self, tryGPU=True):
        """
        Resample the fixed image to the moving image grid.

        Parameters
        ----------
        tryGPU : bool
            If True, try to use GPU.

        Returns
        -------
        resampled : 3DImage
        """
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
        resampled.resampleOpenMP(gridSize, origin, self.fixed._spacing, tryGPU=tryGPU)

        return resampled

    def computeImageDifference(self, keepFixedShape=True, tryGPU=True):
        """
        Compute the difference between the fixed and moving image.

        Parameters
        ----------
        keepFixedShape : bool
            If True, the moving image is resampled to the fixed image grid.
            If False, the fixed image is resampled to the moving image grid.
        tryGPU : bool
            If True, try to use GPU.

        Returns
        -------
        diff : 3DImage
            Difference between the 2 images.
        """
        if (self.fixed == [] or self.moving == []):
            logger.error("Image not defined in registration object")
            return

        if (keepFixedShape == True):
            diff = self.resampleMovingImage(keepFixedShape=True, tryGPU=tryGPU)
            diff.data = self.fixed._imageArray - diff.data

        else:
            diff = self.resampleMovingImage(keepFixedShape=False, tryGPU=tryGPU)
            tmp = self.resampleFixedImage(tryGPU=tryGPU)
            diff.data = tmp.data - diff.data

        return diff
