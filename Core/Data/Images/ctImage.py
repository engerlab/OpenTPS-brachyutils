import logging
import pydicom

from Core.Data.Images.image3D import Image3D


class CTImage(Image3D):
    def __init__(self, data=None, name="CT image", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), seriesInstanceUID="", frameOfReferenceUID="", sliceLocation=[], sopInstanceUIDs=[]):
        super().__init__(data=data, name=name, patientInfo=patientInfo, origin=origin, spacing=spacing, angles=angles, seriesInstanceUID=seriesInstanceUID)
        self.frameOfReferenceUID = frameOfReferenceUID
        self.seriesInstanceUID = seriesInstanceUID
        self.sliceLocation = sliceLocation
        self.sopInstanceUIDs = sopInstanceUIDs
    
    def __str__(self):
        return "CT image: " + self.seriesInstanceUID

    def copy(self):
        img = super().copy()
        img.seriesInstanceUID = pydicom.uid.generate_uid()
        return img

    def resample(self, gridSize, origin, spacing, fillValue=-1000, outputType=None):
        Image3D.resample(self, gridSize, origin, spacing, fillValue=fillValue, outputType=outputType)
