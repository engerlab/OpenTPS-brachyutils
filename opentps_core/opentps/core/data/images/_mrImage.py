__all__ = ['MRImage']

import pydicom
import copy

from opentps.core.data.images._image3D import Image3D


class MRImage(Image3D):
    """
    Class for MR images. Inherits from Image3D.

    Attributes
    ----------
    name : str (default: "MR image")
        Name of the image.
    frameOfReferenceUID : str
        UID of the frame of reference.
    sliceLocation : float
        Location of the slice.
    sopInstanceUIDs : list of str
        List of SOP instance UIDs.
    bodyPartExamined : str
        Body part examined.
    scanningSequence : str
        Scanning sequence.
    sequenceVariant : str
        Sequence variant.
    scanOptions : str
        Scan options.
    mrArcquisitionType : str
        MR acquisition type.
    repetitionTime : float (default: 0.0)
        Repetition time.
    echoTime : float (default: 0.0)
        Echo time.
    nAverages : float (default: 0.0)
        Number of averages.
    imagingFrequency : str
        Imaging frequency.
    echoNumbers : int (default: 1)
        Number of echoes.
    magneticFieldStrength : float (default: 3.0)
        Magnetic field strength.
    spacingBetweenSlices : float (default: 2.0)
        Spacing between slices.
    nPhaseSteps : int (default: 1)
        Number of phase steps.
    echoTrainLength : int (default: 1)
        Echo train length.
    flipAngle : float (default: 90.0)
        Flip angle in degrees.
    sar : float (default: 0.0)
        Specific absorption rate.
    """
    def __init__(self, imageArray=None, name="MR image", origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0),
                 seriesInstanceUID="", frameOfReferenceUID="", sliceLocation=None, sopInstanceUIDs=None, patient=None):
        self.frameOfReferenceUID = frameOfReferenceUID
        self.sliceLocation = sliceLocation
        self.sopInstanceUIDs = sopInstanceUIDs
        self.bodyPartExamined = ""
        self.scanningSequence = "" 
        self.sequenceVariant= ""
        self.scanOptions = ""
        self.mrArcquisitionType = ""
        self.repetitionTime = 0.0
        self.echoTime = 0.0
        self.nAverages = 0.0
        self.imagingFrequency = ""
        self.echoNumbers = 1
        self.magneticFieldStrength = 3.0
        self.spacingBetweenSlices = 2.0
        self.nPhaseSteps = 1
        self.echoTrainLength = 1
        self.flipAngle = 90.0
        self.sar = 0.0

        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, angles=angles,
                         seriesInstanceUID=seriesInstanceUID, patient=patient)

    def __str__(self):
        return "MR image: " + self.seriesInstanceUID

    @classmethod
    def fromImage3D(cls, image, **kwargs):
        """
        Creates a MRImage from an Image3D.

        Parameters
        ----------
        image : Image3D
            Image3D to be converted to MRImage.
        kwargs : dict (optional)
            Additional keyword arguments.
                - imageArray : numpy.ndarray
                    Image array of the image.
                - origin : tuple of float
                    Origin of the image.
                - spacing : tuple of float
                    Spacing of the image.
                - angles : tuple of float
                    Angles of the image.
                - seriesInstanceUID : str
                    Series instance UID of the image.
                - patient : Patient
                    Patient object of the image.

        Returns
        -------
        MRImage
            MRImage created from the Image3D.
        """
        dic = {'imageArray': copy.deepcopy(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient}
        dic.update(kwargs)
        return cls(**dic)

    def copy(self):
        """
        Creates a copy of the MRImage.

        Returns
        -------
        MRImage
            Copy of the MRImage.
        """
        return MRImage(imageArray=copy.deepcopy(self.imageArray), name=self.name + '_copy', origin=self.origin,
                       spacing=self.spacing, angles=self.angles, seriesInstanceUID=pydicom.uid.generate_uid())



