from Core.Data.Images.image3D import Image3D


class LETImage(Image3D):

    def __init__(self):
        self.ctSeriesInstanceUID = ""
        self.planSOPInstanceUID = ""
        self.frameOfReferenceUID = ""
        self.imgName = ""


    def __str__(self):
        pass

    
    def printLETInfo(self, prefix=""):
        pass
    
    
    
    def prepareImageForViewer(self, allowNegative=False):
        pass


    
    def initializeFromMHD(self, imgName, mhdDose, ct, plan):
        pass
    
    
    
    def initializeFromBeamletDose(self, imgName, beamlets, doseVector, ct):
        pass



    def copy(self):
        return super().copy()
