import logging

from Core.Data.Images.image3D import Image3D


class CTImage(Image3D):
    def __init__(self, data=None, name=None, origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), seriesInstanceUID="", frameOfReferenceUID="", sliceLocation=[]):
        super().__init__(data=data, name=name, origin=origin, spacing=spacing, angles=angles)
        self.seriesInstanceUID = seriesInstanceUID
        
        self.frameOfReferenceUID = frameOfReferenceUID
        self.sliceLocation=sliceLocation
    
    def __str__(self):
        return "CT image: " + self.seriesInstanceUID

    