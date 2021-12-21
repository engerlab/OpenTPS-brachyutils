from Core.Data.Images.image3D import Image3D

class ROIMask(Image3D):
    def __init__(self, data=None, name="ROI contour", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1), displayColor=(0,0,0)):
        super().__init__(data=data, name=name, patientInfo=patientInfo, origin=origin, spacing=spacing)
        self.displayColor = displayColor

    def changeColor(self, color):
        """
        Change the color of the ROIContour.

        Parameters
        ----------
        color : str
            RGB of the new color, format : 'r,g,b' like '0,0,0' for black for instance
        """
        self.displayColor = color