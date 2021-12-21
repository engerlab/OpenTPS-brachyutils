from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController


class ROIContourController(DataController):
    nameChangedSignal = pyqtSignal(str)
    dataChangedSignal = pyqtSignal(object)

    def __init__(self, contour):
        super().__init__(contour)
        self.binaryMasks = []

    def getName(self):
        return self.data.name

    def setName(self, name):
        self.data.name = name
        self.nameChangedSignal.emit(self.data.name)

    def notifyDataChange(self):
        self.dataChangedSignal.emit(self.data)

    def getBinaryMask(self, refImage):
        """
        Get the binary mask of the contour.

        Parameters
        ----------
        refImage: Image3D (or sub-class) object
            Reference image on which the contour mask will be generated. 
            The grid size, origin, and spacing properties of the reference image will be used to create the mask image.

        Returns
        -------
        mask: ROIMask object
            The function returns a binary mask of the contour with the same grid size, origin, and spacing as the reference image.

        """

        # check if the mask was previously generated and saved in the mask list of the controller
        for mask in self.binaryMasks:
            if(mask.origin == refImage.origin and mask.spacing == refImage.spacing and mask.data.shape == refImage.data.shape):
                return mask

        # mask not found in previously computed masks
        mask = self.data.generateBinaryMask(origin=refImage.origin, gridSize=refImage.data.shape, spacing=refImage.spacing)
        self.binaryMasks.append(mask)

        return mask