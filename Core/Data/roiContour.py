import numpy as np
from PIL import Image, ImageDraw
import logging

from Core.Data.patientData import PatientData
from Core.Data.Images.roiMask import ROIMask
from Core.event import Event


class ROIContour(PatientData):
    def __init__(self, patientInfo=None, name="ROI contour", displayColor=(0,0,0), referencedFrameOfReferenceUID=None):
        super().__init__(patientInfo=patientInfo, name=name)

        self.colorChangedSignal = Event(object)

        self._displayColor = displayColor
        self.referencedFrameOfReferenceUID = referencedFrameOfReferenceUID
        self.referencedSOPInstanceUIDs = []
        self.polygonMesh = []

    @property
    def color(self):
        return self._displayColor

    @color.setter
    def color(self, color):
        self._displayColor = color
        self.colorChangedSignal.emit(self._displayColor)

    def getBinaryMask(self, origin=(0, 0, 0), gridSize=(100,100,100), spacing=(1, 1, 1)) -> ROIMask:
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
            mask2D = np.array(img).transpose(1,0)
            mask3D[:,:,sliceZ] = np.logical_or(mask3D[:,:,sliceZ], mask2D)

        mask = ROIMask(imageArray=mask3D, name=self.name, patientInfo=self.patientInfo, origin=origin, spacing=spacing, displayColor=self._displayColor)
        return mask