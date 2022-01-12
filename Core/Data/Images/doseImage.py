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
    
    
    
    def initializeFromMHD(self, imgName, mhdDose, ct, plan):
        """
        Initialize the DoseImage object from a MHDImage.

        Parameters
        ----------
        imgName : str
            Name of the dose image as it will be displayed to the user
        mhdDose : MHDImage object
            MHD image of the dose distribution
        ct : ctImage object
            CT image used for dose calculation
        plan : RTPlan object
            Treatment plan used for dose calculation
        """

        pass
    
    
    
    def initializeFromBeamletDose(self, imgName, beamlets, doseVector, ct):
        """
        Initialize the DoseImage object from a dose vector calculated using the beamlet matrix. 

        Parameters
        ----------
        imgName : str
            Name of the dose image as it will be displayed to the user
        beamlets : MHDImage object
            MHD image of the dose distribution
        doseVector : np Array
            1D vector resulting from the product of the beamlet matrix and the spot weight vector
        ct : ctImage object
            CT image used for dose calculation
        """

        pass
    
    
      
    def resampleToImageGrid(self, ct):
        pass



    def copy(self):
        return super().copy()
        
        
    def exportDicom(self, outputFile, planUID=[]):
        pass
