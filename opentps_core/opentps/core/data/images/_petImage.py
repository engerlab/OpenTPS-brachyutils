__all__ = ['PETImage']

import pydicom
import copy

from opentps.core.data.images._image3D import Image3D

class PETImage(Image3D):
    """
    Class for PET images. Inherits from Image3D.

    Attributes
    ----------
    name : str (default: "PET image")
        Name of the image.
    frameOfReferenceUID : str
        UID of the frame of reference.
    sliceLocation : float
        Location of the slice.
    sopInstanceUIDs : list of str
        List of SOP instance UIDs.
    bodyPartExamined : str
        Body part examined.
    suvType : str
        SUV type. (0x0054, 0x1006)
    countsSource : str
        Counts source. (0x0054, 0x1002)
    correctionApplied : str
        Correction applied. (0x0054, 0x1101)
    attenuationCorrectionMethod : str
        Attenuation correction method. (0x0054, 0x1101)
    scatterCorrectionMethod : str
        Scatter correction method. (0x0054, 0x1105)
    decayCorrection : str
        Decay correction. (0x0054, 0x1102)
    reconstructionDiameter : float
        Reconstruction diameter. (0x0018, 0x9758)
    convolutionKernel : str
        Convolution kernel. (0x0018, 0x1210)
    reconstructionMethod : str
        Reconstruction method. (0x0054, 0x1103)
    collimatorDetectorLinesUsed : str
        Collimator/Detector lines used. (0x0054, 0x1104)
    coincidenceWindowWidth : float
        Coincidence window width. (0x0018, 0x9755)
    imageType : str
        Image type. (0x0008, 0x0008)
    pixelRepresentation : int
        Pixel representation. (0x0028, 0x0103)
    bitsAllocated : int
        Bits allocated. (0x0028, 0x0100)
    bitsStored : int
        Bits stored. (0x0028, 0x0101)
    highBit : int
        High bit. (0x0028, 0x0102)
    rescaleIntercept : float
        Rescale intercept. (0x0028, 0x1052)
    rescaleSlope : float
        Rescale slope. (0x0028, 0x1053)
    frameReferenceTime : float
        Frame reference time. (0x0054, 0x1300)
    acquisitionDate : str
        Acquisition date. (0x0008, 0x0022)
    acquisitionTime : str
        Acquisition time. (0x0008, 0x0032)
    actualFrameDuration : float
        Actual frame duration. (0x0018, 0x1242)
    primaryCountsAccumulated : int
        Primary counts accumulated. (0x0054, 0x1310)
    sliceSensitivityFactor : float
        Slice sensitivity factor. (0x0054, 0x1324)
    decayFactor : float
        Decay factor. (0x0054, 0x1321)
    doseCalibrationFactor : float
        Dose calibration factor. (0x0054, 0x1322)
    scatterFractionFactor : float
        Scatter fraction factor. (0x0054, 0x1323)
    deadTimeCorrectionFactor : float
        Dead time correction factor. (0x0054, 0x1324)
    triggerTime : float
        Trigger time. (0x0018, 0x1060)
    frameTime : float
        Frame time. (0x0018, 0x1063)
    lowRRValue : float
        Low R-R value. (0x0018, 0x1081)
    highRRValue : float
        High R-R value. (0x0018, 0x1082)
    patientName : str
        Patient name. (0x0010, 0x0010)
    patientID : str
        Patient ID. (0x0010, 0x0020)
    patientBirthDate : str
        Patient birth date. (0x0010, 0x0030)
    patientSex : str
        Patient sex. (0x0010, 0x0040)
    studyInstanceUID : str
        Study instance UID. (0x0020, 0x000D)
    seriesInstanceUID : str
        Series instance UID. (0x0020, 0x000E)
    sopInstanceUID : str
        SOP instance UID. (0x0008, 0x0018)
    modality : str
        Modality. (0x0008, 0x0060)
    rows : int
        Rows. (0x0028, 0x0010)
    columns : int
        Columns. (0x0028, 0x0011)
    pixelSpacing : tuple
        Pixel spacing. (0x0028, 0x0030)
    sliceThickness : float
        Slice thickness. (0x0018, 0x0050)
    imagePositionPatient : tuple
        Image position patient. (0x0020, 0x0032)
    imageOrientationPatient : tuple
        Image orientation patient. (0x0020, 0x0037)
    """
    def __init__(self, imageArray=None, name="PET image", origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0),
                 seriesInstanceUID="", frameOfReferenceUID="", sliceLocation=None, sopInstanceUIDs=None, patient=None):
        self.frameOfReferenceUID = frameOfReferenceUID
        self.sliceLocation = sliceLocation
        self.sopInstanceUIDs = sopInstanceUIDs
        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, angles=angles,
                         seriesInstanceUID=seriesInstanceUID, patient=patient)
    def __str__(self):
        return "PET image: " + self.seriesInstanceUID
    
    @classmethod
    def fromImage3D(cls, image, **kwargs):
        """
        Creates a PETImage from an Image3D.

        Parameters
        ----------
        image : Image3D
            Image3D to be converted to PETImage.
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
        PETImage
            PETImage created from the Image3D.
        """
        dic = {'imageArray': copy.deepcopy(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient}
        dic.update(kwargs)
        return cls(**dic)

    def copy(self):
        """
        Creates a copy of the PETImage.

        Returns
        -------
        PETImage
            Copy of the PETImage.
        """
        return PETImage(imageArray=copy.deepcopy(self.imageArray), name=self.name + '_copy', origin=self.origin,
                       spacing=self.spacing, angles=self.angles, seriesInstanceUID=pydicom.uid.generate_uid())

