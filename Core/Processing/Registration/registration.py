import numpy as np
import scipy.ndimage
import scipy.signal
import logging


class Registration:

    def __init__(self, fixed, moving):
        self.fixed = fixed
        self.moving = moving
        self.deformed = []
        self.roiBox = []

    def normGaussConv(self, data, cert, sigma):
        data = scipy.ndimage.gaussian_filter(np.multiply(data, cert), sigma=sigma)
        cert = scipy.ndimage.gaussian_filter(cert, sigma=sigma)
        z = (cert == 0)
        data[z] = 0.0
        cert[z] = 1.0
        data = np.divide(data, cert)
        return data

    def fieldRegularization(self, field, filterType="Gaussian", sigma=1.0, cert=None):

        if filterType == "Gaussian":
            field.velocity[:, :, :, 0] = scipy.ndimage.gaussian_filter(field.velocity[:, :, :, 0], sigma=sigma)
            field.velocity[:, :, :, 1] = scipy.ndimage.gaussian_filter(field.velocity[:, :, :, 1], sigma=sigma)
            field.velocity[:, :, :, 2] = scipy.ndimage.gaussian_filter(field.velocity[:, :, :, 2], sigma=sigma)
            return

        if filterType == "NormalizedGaussian":
            if cert is None:
                cert = np.ones_like(field.velocity[:, :, :, 0])
            field.velocity[:, :, :, 0] = self.normGaussConv(field.velocity[:, :, :, 0], cert, sigma)
            field.velocity[:, :, :, 1] = self.normGaussConv(field.velocity[:, :, :, 1], cert, sigma)
            field.velocity[:, :, :, 2] = self.normGaussConv(field.velocity[:, :, :, 2], cert, sigma)
            return

        else:
            print("Error: unknown filter for field fieldRegularization")
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
        Image.origin[0] += translation[0]
        Image.origin[1] += translation[1]
        Image.origin[2] += translation[2]

        Image.VoxelX = Image.origin[0] + np.arange(Image.getGridSize()[0]) * Image.spacing[0]
        Image.VoxelY = Image.origin[1] + np.arange(Image.getGridSize()[1]) * Image.spacing[1]
        Image.VoxelZ = Image.origin[2] + np.arange(Image.getGridSize()[2]) * Image.spacing[2]

    def translateAndComputeSSD(self, translation=None):

        if translation is None: 
            translation = [0.0, 0.0, 0.0]

        # crop fixed image to ROI box
        if (self.roiBox == []):
            fixed = self.fixed.Image
            origin = self.fixed.origin
            gridSize = self.fixed.getGridSize()
        else:
            start = self.roiBox[0]
            stop = self.roiBox[1]
            fixed = self.fixed.Image[start[0]:stop[0], start[1]:stop[1], start[2]:stop[2]]
            origin = self.fixed.origin + np.array(
                [start[1] * self.fixed.spacing[0], start[0] * self.fixed.spacing[1],
                 start[2] * self.fixed.spacing[2]])
            gridSize = list(fixed.shape)

        print("Translation: " + str(translation))

        # deform moving image
        self.deformed = self.moving.copy()
        self.translateOrigin(self.deformed, translation)
        self.deformed.resample_image(gridSize, origin, self.fixed.spacing)

        # compute metric
        ssd = self.computeSSD(fixed, self.deformed.Image)
        return ssd

    def computeSSD(self, fixed, deformed):
        # compute metric
        ssd = np.sum(np.power(fixed - deformed, 2))
        # print("SSD: " + str(ssd))
        return ssd

    def resampleMovingImage(self, keepFixedShape=True):
        if self.fixed == [] or self.moving == []:
            print("Image not defined in registration object")
            return

        if keepFixedShape == True:
            resampled = self.moving.copy()
            resampled.resample_image(self.fixed.getGridSize(), self.fixed.origin, self.fixed.spacing)

        else:
            X_min = min(self.fixed.origin[0], self.moving.origin[0])
            Y_min = min(self.fixed.origin[1], self.moving.origin[1])
            Z_min = min(self.fixed.origin[2], self.moving.origin[2])

            X_max = max(self.fixed.VoxelX[-1], self.moving.VoxelX[-1])
            Y_max = max(self.fixed.VoxelY[-1], self.moving.VoxelY[-1])
            Z_max = max(self.fixed.VoxelZ[-1], self.moving.VoxelZ[-1])

            origin = [X_min, Y_min, Z_min]
            gridSizeX = round((X_max - X_min) / self.fixed.spacing[0])
            gridSizeY = round((Y_max - Y_min) / self.fixed.spacing[1])
            gridSizeZ = round((Z_max - Z_min) / self.fixed.spacing[2])
            gridSize = [gridSizeX, gridSizeY, gridSizeZ]

            resampled = self.moving.copy()
            resampled.resample_image(gridSize, origin, self.fixed.spacing)

        return resampled

    def resampleFixedImage(self):

        if (self.fixed == [] or self.moving == []):
            print("Image not defined in registration object")
            return

        X_min = min(self.fixed.origin[0], self.moving.origin[0])
        Y_min = min(self.fixed.origin[1], self.moving.origin[1])
        Z_min = min(self.fixed.origin[2], self.moving.origin[2])

        X_max = max(self.fixed.VoxelX[-1], self.moving.VoxelX[-1])
        Y_max = max(self.fixed.VoxelY[-1], self.moving.VoxelY[-1])
        Z_max = max(self.fixed.VoxelZ[-1], self.moving.VoxelZ[-1])

        origin = [X_min, Y_min, Z_min]
        gridSizeX = round((X_max - X_min) / self.fixed.spacing[0])
        gridSizeY = round((Y_max - Y_min) / self.fixed.spacing[1])
        gridSizeZ = round((Z_max - Z_min) / self.fixed.spacing[2])
        gridSize = [gridSizeX, gridSizeY, gridSizeZ]

        resampled = self.fixed.copy()
        resampled.resample_image(gridSize, origin, self.fixed.spacing)

        return resampled

    def computeImageDifference(self, keepFixedShape=True):

        if (self.fixed == [] or self.moving == []):
            print("Image not defined in registration object")
            return

        if (keepFixedShape == True):
            diff = self.resampleMovingImage(keepFixedShape=True)
            diff.Image = self.fixed.Image - diff.Image

        else:
            diff = self.resampleMovingImage(keepFixedShape=False)
            tmp = self.resampleFixedImage()
            diff.Image = tmp.Image - diff.Image

        return diff
