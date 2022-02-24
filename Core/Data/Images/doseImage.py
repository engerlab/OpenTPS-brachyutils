import numpy as np

from Core.Data.Images.image3D import Image3D


class DoseImage(Image3D):

    def __init__(self, imageArray=None, name="Dose image", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), seriesInstanceUID="", frameOfReferenceUID="", sopInstanceUID="", planSOPInstanceUID=""):
        super().__init__(imageArray=imageArray, name=name, patientInfo=patientInfo, origin=origin, spacing=spacing, angles=angles, seriesInstanceUID=seriesInstanceUID)
        self.seriesInstanceUID = seriesInstanceUID
        self.frameOfReferenceUID = frameOfReferenceUID
        self.sopInstanceUID = sopInstanceUID
        self.planSOPInstanceUID = planSOPInstanceUID



    def __str__(self):
        """
        Overload __str__ function that is called when one print the object.
        """

        pass
    
    
    @classmethod
    def fromImage(cls, image:Image3D):
        doseImage = cls()
        doseImage.imageArray = np.array(image.imageArray)
        doseImage.origin = np.array(image.origin)
        doseImage.spacing = np.array(image.spacing)
        doseImage.angles = np.array(image.angles)
        doseImage.seriesInstanceUID = image.seriesInstanceUID
    
        return doseImage

      
    def resampleToImageGrid(self, ct):
        pass



    def copy(self):
        return super().copy()
        
        
    def exportDicom(self, outputFile, planUID=[]):
        pass

    def dumpableCopy(self):
        dumpableDose = DoseImage(imageArray=self.imageArray, name=self.name, patientInfo=self.patientInfo, origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=self.seriesInstanceUID, frameOfReferenceUID=self.frameOfReferenceUID, sopInstanceUID=self.sopInstanceUID, planSOPInstanceUID=self.planSOPInstanceUID)
        # dumpableDose.patient = self.patient
        return dumpableDose