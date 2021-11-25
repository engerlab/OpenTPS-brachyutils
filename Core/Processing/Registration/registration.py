import numpy as np
import scipy.ndimage
import scipy.signal
import logging


def normGaussConv(data, cert, sigma):
    data = scipy.ndimage.gaussian_filter(np.multiply(data, cert), sigma=sigma)
    cert = scipy.ndimage.gaussian_filter(cert, sigma=sigma)
    z = (cert == 0)
    data[z] = 0.0
    cert[z] = 1.0
    data = np.divide(data, cert)
    return data


class Registration:

    def __init__(self, fixed, moving):
        self.fixed = fixed
        self.moving = moving
        self.deformed = []
        self.roiBox = []

    def fieldRegularization(self, field, filterType="Gaussian", sigma=1.0, cert=None):

        if filterType == "Gaussian":
            field.Velocity[:, :, :, 0] = scipy.ndimage.gaussian_filter(field.Velocity[:, :, :, 0], sigma=sigma)
            field.Velocity[:, :, :, 1] = scipy.ndimage.gaussian_filter(field.Velocity[:, :, :, 1], sigma=sigma)
            field.Velocity[:, :, :, 2] = scipy.ndimage.gaussian_filter(field.Velocity[:, :, :, 2], sigma=sigma)
            return

        if filterType == "NormalizedGaussian":
            if cert is None:
                cert = np.ones_like(field.Velocity[:, :, :, 0])
            field.Velocity[:, :, :, 0] = normGaussConv(field.Velocity[:, :, :, 0], cert, sigma)
            field.Velocity[:, :, :, 1] = normGaussConv(field.Velocity[:, :, :, 1], cert, sigma)
            field.Velocity[:, :, :, 2] = normGaussConv(field.Velocity[:, :, :, 2], cert, sigma)
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
        Image.ImagePositionPatient[0] += translation[0]
        Image.ImagePositionPatient[1] += translation[1]
        Image.ImagePositionPatient[2] += translation[2]

        Image.VoxelX = Image.ImagePositionPatient[0] + np.arange(Image.GridSize[0]) * Image.PixelSpacing[0]
        Image.VoxelY = Image.ImagePositionPatient[1] + np.arange(Image.GridSize[1]) * Image.PixelSpacing[1]
        Image.VoxelZ = Image.ImagePositionPatient[2] + np.arange(Image.GridSize[2]) * Image.PixelSpacing[2]

    def translateAndComputeSSD(self, translation=[0.0, 0.0, 0.0]):

        # crop fixed image to ROI box
        if (self.roiBox == []):
            fixed = self.fixed.Image
            Origin = self.fixed.ImagePositionPatient
            GridSize = self.fixed.GridSize
        else:
            start = self.roiBox[0]
            stop = self.roiBox[1]
            fixed = self.fixed.Image[start[0]:stop[0], start[1]:stop[1], start[2]:stop[2]]
            Origin = self.fixed.ImagePositionPatient + np.array(
                [start[1] * self.fixed.PixelSpacing[0], start[0] * self.fixed.PixelSpacing[1],
                 start[2] * self.fixed.PixelSpacing[2]])
            GridSize = list(fixed.shape)

        print("Translation: " + str(translation))

        # deform moving image
        self.deformed = self.moving.copy()
        self.translateOrigin(self.deformed, translation)
        self.deformed.resample_image(GridSize, Origin, self.fixed.PixelSpacing)

        # compute metric
        ssd = self.computeSSD(fixed, self.deformed.Image)
        return ssd

    def computeSSD(self, fixed, deformed):
        # compute metric
        ssd = np.sum(np.power(fixed - deformed, 2))
        # print("SSD: " + str(ssd))
        return ssd

    def resampleMovingImage(self, keepFixedShape=True):
        if (self.fixed == [] or self.moving == []):
            print("Image not defined in registration object")
            return

        if (keepFixedShape == True):
            resampled = self.moving.copy()
            resampled.resample_image(self.fixed.GridSize, self.fixed.ImagePositionPatient, self.fixed.PixelSpacing)

        else:
            X_min = min(self.fixed.ImagePositionPatient[0], self.moving.ImagePositionPatient[0])
            Y_min = min(self.fixed.ImagePositionPatient[1], self.moving.ImagePositionPatient[1])
            Z_min = min(self.fixed.ImagePositionPatient[2], self.moving.ImagePositionPatient[2])

            X_max = max(self.fixed.VoxelX[-1], self.moving.VoxelX[-1])
            Y_max = max(self.fixed.VoxelY[-1], self.moving.VoxelY[-1])
            Z_max = max(self.fixed.VoxelZ[-1], self.moving.VoxelZ[-1])

            Offset = [X_min, Y_min, Z_min]
            GridSize_x = round((X_max - X_min) / self.fixed.PixelSpacing[0])
            GridSize_y = round((Y_max - Y_min) / self.fixed.PixelSpacing[1])
            GridSize_z = round((Z_max - Z_min) / self.fixed.PixelSpacing[2])
            GridSize = [GridSize_x, GridSize_y, GridSize_z]

            resampled = self.moving.copy()
            resampled.resample_image(GridSize, Offset, self.fixed.PixelSpacing)

        return resampled

    def resampleFixedImage(self):

        if (self.fixed == [] or self.moving == []):
            print("Image not defined in registration object")
            return

        X_min = min(self.fixed.ImagePositionPatient[0], self.moving.ImagePositionPatient[0])
        Y_min = min(self.fixed.ImagePositionPatient[1], self.moving.ImagePositionPatient[1])
        Z_min = min(self.fixed.ImagePositionPatient[2], self.moving.ImagePositionPatient[2])

        X_max = max(self.fixed.VoxelX[-1], self.moving.VoxelX[-1])
        Y_max = max(self.fixed.VoxelY[-1], self.moving.VoxelY[-1])
        Z_max = max(self.fixed.VoxelZ[-1], self.moving.VoxelZ[-1])

        Offset = [X_min, Y_min, Z_min]
        GridSize_x = round((X_max - X_min) / self.fixed.PixelSpacing[0])
        GridSize_y = round((Y_max - Y_min) / self.fixed.PixelSpacing[1])
        GridSize_z = round((Z_max - Z_min) / self.fixed.PixelSpacing[2])
        GridSize = [GridSize_x, GridSize_y, GridSize_z]

        resampled = self.fixed.copy()
        resampled.resample_image(GridSize, Offset, self.fixed.PixelSpacing)

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
