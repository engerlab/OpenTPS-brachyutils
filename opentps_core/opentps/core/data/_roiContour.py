# from __future__ import annotations
# from typing import TYPE_CHECKING
#
# if TYPE_CHECKING:
#     from opentps.core.data.images import ROIMask

__all__ = ['ROIContour']


import numpy as np
from PIL import Image, ImageDraw
import logging

from opentps.core.data._patientData import PatientData

from opentps.core.processing.imageProcessing import resampler3D
from opentps.core import Event


class ROIContour(PatientData):
    """
    Class for storing a ROI contour. The contour is stored as a list of polygon meshes. Each polygon mesh is a list of
    coordinates (x,y,z) of the vertices of the polygon. The coordinates are in the patient coordinate system.
    A ROI contour can be converted to a binary mask image using the getBinaryMask() method.

    Parameters
    ----------
    name: str
        Name of the ROI contour.
    color: tuple
        Display color of the ROI contour.
    referencedFrameOfReferenceUID: str
        UID of the frame of reference that the ROI contour is referenced to.
    referencedSOPInstanceUIDs: list
        List of SOP instance UIDs of the images that the ROI contour is referenced to.
    polygonMesh: list
        List of polygon meshes that define the ROI contour. Each polygon mesh is a list of coordinates (x,y,z) of the
        vertices of the polygon. The coordinates are in the patient coordinate system.
    """
    def __init__(self, name="ROI contour", displayColor=(0,0,0), referencedFrameOfReferenceUID=None):
        super().__init__(name=name)

        self.colorChangedSignal = Event(object)

        self._displayColor = displayColor
        self.referencedFrameOfReferenceUID = referencedFrameOfReferenceUID
        self.referencedSOPInstanceUIDs = []
        self.polygonMesh = []
        # from opentps.core.data.images._roiMask import ROIMask
    @property
    def color(self):
        return self._displayColor

    @color.setter
    def color(self, color):
        self._displayColor = color
        self.colorChangedSignal.emit(self._displayColor)

    def getBinaryMask(self, origin=None, gridSize=None, spacing=None):
        """
        Convert the ROI contour to a binary mask image.

        Parameters
        ---------
        origin: array    (optional)
            Origin of the binary mask image.
        gridSize: array    (optional)
            Grid size of the binary mask image.
        spacing: array    (optional)
            Voxel spacing of the binary mask image.

        Returns
        -------
        mask: ROIMask
            Binary mask image.
        """
        minSpatialResolution = 1.

        contourOrigin = [0, 0, 0]
        contourSpacing = [0, 0, 0]
        contourGridSize = [0, 0, 0]

        allX = np.array([])
        allY = np.array([])
        allZ = np.array([])

        for contourData in self.polygonMesh:
            Xs = np.array(contourData[0::3])
            Ys = np.array(contourData[1::3])
            Z = contourData[2]

            allX = np.concatenate((allX, Xs))
            allY = np.concatenate((allY, Ys))
            allZ = np.concatenate((allZ, np.array([Z])))

        allX = np.sort(allX)
        allY = np.sort(allY)
        allZ = np.sort(allZ)

        xDiff = np.abs(np.diff(allX))
        xDiff[xDiff==0] = np.Inf
        yDiff = np.abs(np.diff(allY))
        yDiff[yDiff == 0] = np.Inf
        zDiff = np.abs(np.diff(allZ))
        zDiff[zDiff == 0] = np.Inf

        contourSpacing[0] = minSpatialResolution
        contourSpacing[1] = minSpatialResolution

        if len(zDiff) == 0:

            from opentps.core.data.images._roiMask import ROIMask
            return ROIMask(imageArray=None, name=self.name, origin=contourOrigin, spacing=contourSpacing,
                           displayColor=self._displayColor)

        else:
            if np.isfinite(zDiff[0]):
                contourSpacing[2] = zDiff[0]
            else:
                contourSpacing[2] = minSpatialResolution

        contourOrigin[0] = allX[0]
        contourOrigin[1] = allY[0]
        contourOrigin[2] = allZ[0]

        contourGridSize[0] = int(round((allX[-1] - contourOrigin[0]) / contourSpacing[0])) + 1
        contourGridSize[1] = int(round((allY[-1] - contourOrigin[1]) / contourSpacing[1])) + 1
        contourGridSize[2] = int(round((allZ[-1] - contourOrigin[2]) / contourSpacing[2])) + 1

        mask3D = np.zeros(contourGridSize).astype(bool)

        for contourData in self.polygonMesh:
            # extract contour coordinates and convert to image coordinates (voxels)
            coordXY = list(zip(((np.array(contourData[0::3]) - contourOrigin[0]) / contourSpacing[0]),
                               ((np.array(contourData[1::3]) - contourOrigin[1]) / contourSpacing[1])))
            coordZ = (float(contourData[2]) - contourOrigin[2]) / contourSpacing[2]
            sliceZ = int(round(coordZ))

            # convert polygon to mask (based on matplotlib - slow)
            # x, y = np.meshgrid(np.arange(gridSize[0]), np.arange(gridSize[1]))
            # points = np.transpose((x.ravel(), y.ravel()))
            # path = Path(coordXY)
            # mask2D = path.contains_points(points)
            # mask2D = mask.reshape((gridSize[0], gridSize[1]))

            # convert polygon to mask (based on PIL - fast)
            img = Image.new('L', (contourGridSize[0], contourGridSize[1]), 0)
            if (len(coordXY) > 1): ImageDraw.Draw(img).polygon(coordXY, outline=1, fill=1)
            mask2D = np.array(img).transpose(1, 0)
            mask3D[:, :, sliceZ] = np.logical_xor(mask3D[:, :, sliceZ], mask2D)

        from opentps.core.data.images._roiMask import ROIMask
        mask = ROIMask(imageArray=mask3D, name=self.name, origin=contourOrigin, spacing=contourSpacing,
                       displayColor=self._displayColor)

        if not (origin is None):
            mask3D = np.zeros(gridSize).astype(bool)
            referenceImage = ROIMask(imageArray=mask3D, spacing=spacing, origin=origin)

            resampler3D.resampleImage3DOnImage3D(mask, referenceImage, inPlace=True, fillValue=0)

        return mask

    def getBinaryMask_old(self, origin=(0, 0, 0), gridSize=(100,100,100), spacing=(1, 1, 1)):
        """
        Convert the polygon mesh to a binary mask image.

        Parameters
        ----------
        origin: tuple
            Origin coordinates of the generated mask image

        gridSize: tuple
            Number of voxels in each dimension of the generated mask image

        spacing: tuple
            Spacing between voxels of the generated mask image

        Returns
        -------
        mask: roiMask object
            The function returns the binary mask of the contour

        """
        mask3D = np.zeros(gridSize, dtype=np.bool)

        for contourData in self.polygonMesh:
            # extract contour coordinates and convert to image coordinates (voxels)
            coordXY = list(zip( ((np.array(contourData[0::3])-origin[0])/spacing[0]), ((np.array(contourData[1::3])-origin[1])/spacing[1]) ))
            coordZ = (float(contourData[2]) - origin[2]) / spacing[2]
            sliceZ = int(round(coordZ))

            if(sliceZ < 0 or sliceZ >= gridSize[2]):
                logging.warning("Warning: RTstruct slice outside mask boundaries has been ignored for contour " + self.name)
                continue

            # convert polygon to mask (based on matplotlib - slow)
            #x, y = np.meshgrid(np.arange(gridSize[0]), np.arange(gridSize[1]))
            #points = np.transpose((x.ravel(), y.ravel()))
            #path = Path(coordXY)
            #mask2D = path.contains_points(points)
            #mask2D = mask.reshape((gridSize[0], gridSize[1]))

            # convert polygon to mask (based on PIL - fast)
            img = Image.new('L', (gridSize[0], gridSize[1]), 0)
            if(len(coordXY) > 1): ImageDraw.Draw(img).polygon(coordXY, outline=1, fill=1)
            mask2D = np.array(img).transpose(1, 0)
            # mask3D[:, :, sliceZ] = np.logical_xor(mask3D[:, :, sliceZ], mask2D)
            mask3D[:, :, sliceZ] = mask3D[:, :, sliceZ] - mask2D
        from opentps.core.data.images._roiMask import ROIMask
        mask = ROIMask(imageArray=mask3D, name=self.name, origin=origin, spacing=spacing, displayColor=self._displayColor)

        return mask


    def getCenterOfMass(self, origin=None, gridSize=None, spacing=None):

        """
        Calculate the center of mass of the contour

        Parameters
        ----------
        origin: array
            Origin coordinates of the generated mask image
        gridSize: array
            Number of voxels in each dimension of the generated mask image
        spacing: array
            Spacing between voxels of the generated mask image

        Returns
        --------
        centerOfMass: array
            Center of mass of the contour
        """

        tempMask = self.getBinaryMask(origin=origin, gridSize=gridSize, spacing=spacing)
        centerOfMass = tempMask.centerOfMass

        return centerOfMass


    def getBinaryContourMask(self, origin=(0, 0, 0), gridSize=(100,100,100), spacing=(1, 1, 1)):
        """
        Convert the polygon mesh to a binary mask image.

        Parameters
        ----------
        origin: tuple
            Origin coordinates of the generated mask image
        gridSize: tuple
            Number of voxels in each dimension of the generated mask image
        spacing: tuple
            Spacing between voxels of the generated mask image

        Returns
        -------
        mask: roiMask object
            The function returns the binary mask of the contou
        """
        mask3D = np.zeros(gridSize, dtype=np.bool)

        for contourData in self.polygonMesh:
            # extract contour coordinates and convert to image coordinates (voxels)
            coordXY = list(zip(((np.array(contourData[0::3]) - origin[0]) / spacing[0]),
                               ((np.array(contourData[1::3]) - origin[1]) / spacing[1])))
            coordZ = (float(contourData[2]) - origin[2]) / spacing[2]
            sliceZ = int(round(coordZ))

            if (sliceZ < 0 or sliceZ >= gridSize[2]):
                logging.warning(
                    "Warning: RTstruct slice outside mask boundaries has been ignored for contour " + self.name)
                continue

            # convert polygon to mask (based on matplotlib - slow)
            # x, y = np.meshgrid(np.arange(gridSize[0]), np.arange(gridSize[1]))
            # points = np.transpose((x.ravel(), y.ravel()))
            # path = Path(coordXY)
            # mask2D = path.contains_points(points)
            # mask2D = mask.reshape((gridSize[0], gridSize[1]))

            # convert polygon to mask (based on PIL - fast)
            img = Image.new('L', (gridSize[0], gridSize[1]), 0)
            if (len(coordXY) > 1): ImageDraw.Draw(img).polygon(coordXY, outline=1, fill=0)
            mask2D = np.array(img).transpose(1, 0)
            mask3D[:, :, sliceZ] = np.logical_or(mask3D[:, :, sliceZ], mask2D)

        from opentps.core.data.images._roiMask import ROIMask
        contourMask = ROIMask(imageArray=mask3D, name=self.name, origin=origin, spacing=spacing,
                       displayColor=self._displayColor)

        return contourMask

