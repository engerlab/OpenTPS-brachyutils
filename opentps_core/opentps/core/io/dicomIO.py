import copy
import datetime
import os
import pydicom
import numpy as np
import logging

from opentps.core.data import Patient
from opentps.core.data.plan._rangeShifter import RangeShifter

from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data.plan._planIonBeam import PlanIonBeam
from opentps.core.data.plan._planIonLayer import PlanIonLayer
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._mrImage import MRImage
from opentps.core.data.images._doseImage import DoseImage
from opentps.core.data._rtStruct import RTStruct
from opentps.core.data._roiContour import ROIContour
from opentps.core.data.images._vectorField3D import VectorField3D
from opentps.core.data._transform3D import Transform3D

logger = logging.getLogger(__name__)

def floatToDS(v):
    return pydicom.valuerep.DSfloat(v,auto_format=True)

def arrayToDS(ls):
    return list(map(floatToDS, ls))

def setFrameOfReferenceUID(value):
    if (value == '' or value is None):
        return pydicom.uid.generate_uid()
    else:
        return value

################### CT Image ###########
def readDicomCT(dcmFiles):
    """
    Generate a CT image object from a list of dicom CT slices.

    Parameters
    ----------
    dcmFiles: list
        List of paths for Dicom CT slices to be imported.

    Returns
    -------
    image: ctImage object
        The function returns the imported CT image
    """

    # read dicom slices
    images = []
    sopInstanceUIDs = []
    sliceLocation = np.zeros(len(dcmFiles), dtype='float')
    dt = datetime.datetime.now()

    for i in range(len(dcmFiles)):
        dcm = pydicom.dcmread(dcmFiles[i])
        sliceLocation[i] = float(dcm.ImagePositionPatient[2])
        images.append(dcm.pixel_array * dcm.RescaleSlope + dcm.RescaleIntercept)
        sopInstanceUIDs.append(dcm.SOPInstanceUID)


    # sort slices according to their location in order to reconstruct the 3d image
    sortIndex = np.argsort(sliceLocation)
    sliceLocation = sliceLocation[sortIndex]
    sopInstanceUIDs = [sopInstanceUIDs[n] for n in sortIndex]
    images = [images[n] for n in sortIndex]
    imageData = np.dstack(images).astype("float32").transpose(1, 0, 2)

    # verify reconstructed volume
    if imageData.shape[0:2] != (dcm.Columns, dcm.Rows):
        logging.warning("WARNING: GridSize " + str(imageData.shape[0:2]) + " different from Dicom Columns (" + str(
            dcm.Columns) + ") and Rows (" + str(dcm.Rows) + ")")

    # collect image information
    meanSliceDistance = (sliceLocation[-1] - sliceLocation[0]) / (len(images) - 1)
    if (hasattr(dcm, 'SliceThickness') and (
            type(dcm.SliceThickness) == int or type(dcm.SliceThickness) == float) and abs(
            meanSliceDistance - dcm.SliceThickness) > 0.001):
        logging.warning(
            "WARNING: Mean Slice Distance (" + str(meanSliceDistance) + ") is different from Slice Thickness (" + str(
                dcm.SliceThickness) + ")")

    if (hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""):
        imgName = dcm.SeriesDescription
    else:
        imgName = dcm.SeriesInstanceUID

    pixelSpacing = (float(dcm.PixelSpacing[1]), float(dcm.PixelSpacing[0]), meanSliceDistance)
    imagePositionPatient = (float(dcm.ImagePositionPatient[0]), float(dcm.ImagePositionPatient[1]), sliceLocation[0])

    # collect patient information
    if hasattr(dcm, 'PatientID'):
        birth = dcm.PatientBirthDate if hasattr(dcm, 'PatientBirthDate') else ""
        sex = dcm.PatientSex if hasattr(dcm, 'PatientSex') else None

        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=birth, sex=sex)
    else:
        patient = Patient()

    # generate CT image object
    FrameOfReferenceUID = dcm.FrameOfReferenceUID if hasattr(dcm, 'FrameOfReferenceUID') else pydicom.uid.generate_uid()
    image = CTImage(imageArray=imageData, name=imgName, origin=imagePositionPatient,
                    spacing=pixelSpacing, seriesInstanceUID=dcm.SeriesInstanceUID,
                    frameOfReferenceUID=FrameOfReferenceUID, sliceLocation=sliceLocation,
                    sopInstanceUIDs=sopInstanceUIDs)
    image.patient = patient
    image.patientPosition = dcm.PatientPosition if hasattr(dcm, 'PatientPosition') else ""
    image.seriesNumber = dcm.SeriesNumber if hasattr(dcm, 'SeriesNumber') else "1"
    image.photometricInterpretation = dcm.PhotometricInterpretation if hasattr(dcm, 'PhotometricInterpretation') else None
    image.sopInstanceUIDs = sopInstanceUIDs
    image.sopClassUID = dcm.SOPClassUID if hasattr(dcm, 'SOPClassUID') else "1.2.840.10008.5.1.4.1.1.2"
    image.softwareVersions = dcm.SoftwareVersions if hasattr(dcm, 'SoftwareVersions') else "10.0.100.1 (Dicom Export)"
    image.studyDate = dcm.StudyDate if hasattr(dcm, 'StudyDate') else dt.strftime('%Y%m%d')
    image.seriesNumber = dcm.SeriesNumber if(hasattr(dcm, 'SeriesNumber')) else '1'
    image.fileMetaInformationGroupLength = dcm.file_meta.FileMetaInformationGroupLength if hasattr(dcm.file_meta, 'FileMetaInformationGroupLength') else 0
    image.mediaStorageSOPClassUID = dcm.file_meta.MediaStorageSOPClassUID if hasattr(dcm.file_meta, 'MediaStorageSOPClassUID') else "1.2.840.10008.5.1.4.1.1.2"    
    image.mediaStorageSOPInstanceUID = dcm.file_meta.MediaStorageSOPInstanceUID if hasattr(dcm.file_meta, 'MediaStorageSOPInstanceUID') else ""
    image.implementationClassUID = dcm.file_meta.ImplementationClassUID if hasattr(dcm.file_meta, 'ImplementationClassUID') else "1.2.826.0.1.3680043.1.2.100.6.40.0.76"
    image.studyID = dcm.StudyID if hasattr(dcm, 'StudyID') else ""
    image.studyTime = dcm.StudyTime if hasattr(dcm, 'StudyTime') else dt.strftime('%H%M%S.%f')
    image.implementationVersionName = dcm.file_meta.ImplementationVersionName if hasattr(dcm.file_meta, 'ImplementationVersionName') else "DicomObjects.NET"
    image.contentDate = dcm.ContentDate if hasattr(dcm, 'ContentDate') else dt.strftime('%Y%m%d')
    image.frameOfReferenceUID = dcm.FrameOfReferenceUID if hasattr(dcm, 'FrameOfReferenceUID') else None
    image.imageOrientationPatient = dcm.ImageOrientationPatient if hasattr(dcm, 'imageOrientationPatient') else ""
    image.seriesDate = dcm.SeriesDate if hasattr(dcm, 'SeriesDate') else dt.strftime('%Y%m%d')
    image.studyInstanceUID = dcm.StudyInstanceUID if hasattr(dcm, 'StudyInstanceUID') else pydicom.uid.generate_uid()
    image.bitsAllocated = dcm.BitsAllocated if hasattr(dcm, 'BitsAllocated') else 16
    image.modality = dcm.Modality if hasattr(dcm, 'Modality') else "CT"
    image.bitsStored = dcm.BitsStored if hasattr(dcm, 'BitsStored') else 16
    image.highBit = dcm.HighBit if hasattr(dcm, 'HighBit') else 15
    image.approvalStatus = dcm.ApprovalStatus if hasattr(dcm, 'ApprovalStatus') else 'UNAPPROVED'
    image.fileMetaInformationVersion = dcm.file_meta.FileMetaInformationVersion if hasattr(dcm.file_meta, 'FileMetaInformationVersion') else bytes([0,1])
    image.specificCharacterSet = dcm.SpecificCharacterSet if hasattr(dcm, 'SpecificCharacterSet') else "ISO_IR 100"
    image.accessionNumber = dcm.AccessionNumber if hasattr(dcm, 'AccessionNumber') else ""
    image.sopInstanceUID = dcm.SOPInstanceUID if hasattr(dcm, 'SOPInstanceUID') else ""
    image.referringPhysicianName = dcm.ReferringPhysicianName if hasattr(dcm, 'ReferringPhysicianName') else ""
    image.acquisitionNumber = dcm.AcquisitionNumber if hasattr(dcm, 'AcquisitionNumber') else "3"

    return image


def writeDicomCT(ct: CTImage, outputFolderPath:str, outputFileName:str=None):
    """
    Write image and generate the DICOM file

    Parameters
    ----------
    ct: CTImage object
        The ct image object
    outputFolderPath: str
        The output folder path

    Returns
    -------
    SeriesInstanceUID:
        The function returns the series instance UID for these images.
    """

    if not os.path.exists(outputFolderPath):
        os.mkdir(outputFolderPath)
    outdata = ct.imageArray.copy()
    dt = datetime.datetime.now()

    # meta data
    meta = pydicom.dataset.FileMetaDataset()
    meta.MediaStorageSOPClassUID = ct.mediaStorageSOPClassUID if hasattr(ct, 'mediaStorageSOPClassUID') else '1.2.840.10008.5.1.4.1.1.2'   
    meta.ImplementationClassUID = ct.implementationClassUID if hasattr(ct, 'implementationClassUID') else '1.2.826.0.1.3680043.1.2.100.6.40.0.76'
    meta.FileMetaInformationGroupLength = ct.fileMetaInformationGroupLength if hasattr(ct, 'fileMetaInformationGroupLength') else 0
    meta.ImplementationVersionName = ct.implementationVersionName if hasattr(ct, 'implementationVersionName') else "DicomObjects.NET" 
    meta.FileMetaInformationVersion = ct.fileMetaInformationVersion if hasattr(ct, 'fileMetaInformationVersion') else bytes([0,1])
    
    # dicom dataset
    dcm_file = pydicom.dataset.FileDataset(outputFolderPath, {}, file_meta=meta, preamble=b"\0" * 128)
    dcm_file.SOPClassUID = ct.sopClassUID if hasattr(ct, 'sopClassUID') else "1.2.840.10008.5.1.4.1.1.2"
    dcm_file.ImageType = ['DERIVED', 'SECONDARY', 'AXIAL']
    dcm_file.SpecificCharacterSet = ct.specificCharacterSet if hasattr(ct, 'specificCharacterSet') else "ISO_IR 100"
    dcm_file.AccessionNumber = ct.accessionNumber if hasattr(ct, 'accessionNumber') else ""
    dcm_file.SoftwareVersions = ct.softwareVersions if hasattr(ct, 'softwareVersions') else "10.0.100.1 (Dicom Export)"
    
    # patient information
    patient = ct.patient
    if not (patient is None):
        dcm_file.PatientName = "exported_" + patient.name
        dcm_file.PatientID = patient.id
        dcm_file.PatientBirthDate = patient.birthDate if hasattr(patient, 'birthDate') else ""
        dcm_file.PatientSex = patient.sex
    else:
        dcm_file.PatientName = 'ANONYMOUS'
        dcm_file.PatientID = 'ANONYMOUS'
        dcm_file.PatientBirthDate = ""
        dcm_file.PatientSex = 'Helicopter'
    dcm_file.OtherPatientNames = 'None'
    dcm_file.PatientAge = '099Y'
    dcm_file.IssuerOfPatientID = ''

    # Study information
    dcm_file.StudyDate = ct.studyDate if hasattr(ct, 'studyDate') else dt.strftime('%Y%m%d')
    dcm_file.StudyTime = ct.studyTime if hasattr(ct, 'studyTime') else dt.strftime('%H%M%S.%f')
    dcm_file.SeriesTime = dt.strftime('%H%M%S.%f')
    dcm_file.StudyID = ct.studyID if hasattr(ct, 'studyID') else ""
    dcm_file.StudyInstanceUID = ct.studyInstanceUID if hasattr(ct, 'studyInstanceUID') else pydicom.uid.generate_uid()


    # content information
    dcm_file.ContentDate = dt.strftime('%Y%m%d')
    dcm_file.ContentTime = dt.strftime('%H%M%S.%f')
    dcm_file.InstanceCreationDate = dt.strftime('%Y%m%d')
    dcm_file.InstanceCreationTime = dt.strftime('%H%M%S.%f')
    dcm_file.Modality = ct.modality if hasattr(ct, 'modality') else 'CT'
    dcm_file.Manufacturer = 'OpenTPS'
    # dcm_file.InstitutionName = ''
    dcm_file.ReferringPhysicianName = ct.referringPhysicianName if hasattr(ct, 'referringPhysicianName') else ""
    dcm_file.StudyDescription = 'OpenTPS simulation'
    dcm_file.SeriesDescription = 'OpenTPS created image'
    dcm_file.ManufacturerModelName = 'OpenTPS'
    # dcm_file.ManufacturerModelName = ''
    # dcm_file.ScanOptions = 'HELICAL_CT'
    dcm_file.SliceThickness = floatToDS(ct.spacing[2])
    # dcm_file.SliceThickness = ct.spacing[2]
    # dcm_file.KVP = '120.0'
    # dcm_file.SpacingBetweenSlices = ct.spacing[2]
    dcm_file.SpacingBetweenSlices = floatToDS(ct.spacing[2])
    # dcm_file.DataCollectionDiameter = '550.0'
    # dcm_file.DeviceSerialNumber = ''
    # dcm_file.ProtocolName = ''
    # dcm_file.ReconstructionDiameter = ''
    # dcm_file.GantryDetectorTilt = ''
    # dcm_file.TableHeight = ''
    # dcm_file.RotationDirection = ''
    # dcm_file.ExposureTime = ''
    # dcm_file.XRayTubeCurrent = ''
    # dcm_file.Exposure = ''
    # dcm_file.GeneratorPower = ''
    # dcm_file.ConvolutionKernel = ''
    dcm_file.PatientPosition = ct.patientPosition if hasattr(ct, 'patientPosition') else "" 
    # dcm_file.CTDIvol = 

    dcm_file.SeriesInstanceUID = ct.seriesInstanceUID
    dcm_file.SeriesNumber = ct.seriesNumber if hasattr(ct, 'seriesNumber') else "1"
    dcm_file.AcquisitionNumber = ct.acquisitionNumber if hasattr(ct, 'acquisitionNumber') else '3'
    dcm_file.ImagePositionPatient = arrayToDS(ct.origin)
    dcm_file.ImageOrientationPatient = [1, 0, 0, 0, 1,
                                        0]  # HeadFirstSupine=1,0,0,0,1,0  FeetFirstSupine=-1,0,0,0,1,0  HeadFirstProne=-1,0,0,0,-1,0  FeetFirstProne=1,0,0,0,-1,0
    dcm_file.FrameOfReferenceUID = ct.frameOfReferenceUID if hasattr(ct, 'frameOfReferenceUID') else pydicom.uid.generate_uid()
    # dcm_file.NumberOfStudyRelatedInstances = ''
    # dcm_file.RespiratoryIntervalTime =
    dcm_file.SamplesPerPixel = 1
    dcm_file.PhotometricInterpretation = ct.photometricInterpretation if hasattr(ct, 'photometricInterpretation') else 'MONOCHROME2'
    dcm_file.Rows = ct.gridSize[1]
    dcm_file.Columns = ct.gridSize[0]
    dcm_file.PixelSpacing = arrayToDS(ct.spacing[0:2])
    dcm_file.BitsAllocated = ct.bitsAllocated if hasattr(ct, 'bitsAllocated') else 16
    dcm_file.BitsStored = ct.bitsStored if hasattr(ct, 'bitsStored') else 16
    dcm_file.HighBit = ct.highBit if hasattr(ct, 'highBit') else 15
    dcm_file.PixelRepresentation = 1
    dcm_file.ApprovalStatus = ct.approvalStatus if hasattr(ct, 'approvalStatus') else 'UNAPPROVED'
    # dcm_file.WindowCenter = '40.0'
    # dcm_file.WindowWidth = '400.0'

    # NEW: Rescale image intensities if pixel data does not fit into INT16
    RescaleSlope = 1
    RescaleIntercept = 0
    dataMin = np.min(outdata)
    dataMax = np.max(outdata)
    if (dataMin<-2**15) or (dataMax>=2**15):
        dataRange = dataMax-dataMin
        if dataRange>=2**16:
            RescaleSlope = dataRange/(2**16-1)
        outdata = np.round((outdata-dataMin)/RescaleSlope - 2**15)
        RescaleIntercept = dataMin + RescaleSlope*2**15

    ##
    ## OLD RESCALE CODE
    ##
    # RescaleSlope = 1
    # RescaleIntercept = np.floor(np.min(outdata))
    # outdata[np.isinf(outdata)]=np.min(outdata)
    # outdata[np.isnan(outdata)]=np.min(outdata)

    # while np.max(np.abs(outdata))>=2**15:
    #     print('Pixel values are too large to be stored in INT16. Entire image is divided by 2...')
    #     RescaleSlope = RescaleSlope/2
    #     outdata = outdata/2
    # if np.max(np.abs(outdata))<2**6:
    #     print('Intensity range is too small. Entire image is rescaled...');
    #     RescaleSlope = (np.max(outdata)-RescaleIntercept)/2**12
    # if not(RescaleSlope):
    #     RescaleSlope = 1
    # outdata = (outdata-RescaleIntercept)/RescaleSlope

    # Reduce 'rounding' errors...
    outdata = np.round(outdata)

    # Update dicom tags
    dcm_file.RescaleSlope = str(RescaleSlope)
    dcm_file.RescaleIntercept = str(RescaleIntercept)

    # dcm_file.ScheduledProcedureStepStartDate = ''
    # dcm_file.ScheduledProcedureStepStartTime = ''
    # dcm_file.ScheduledProcedureStepEndDate = ''
    # dcm_file.ScheduledProcedureStepEndTime = ''
    # dcm_file.PerformedProcedureStepStartDate = ''
    # dcm_file.PerformedProcedureStepStartTime = ''
    # dcm_file.PerformedProcedureStepID = ''
    # dcm_file.ConfidentialityCode = ''
    dcm_file.ContentLabel = 'CT'
    dcm_file.ContentDescription = ''
    dcm_file.Laterality = ""
    # dcm_file.StructureSetLabel = ''
    # dcm_file.StructureSetDate = ''
    # dcm_file.StructureSetTime = ''
    dcm_file.PositionReferenceIndicator = ""
    
    # transfer syntax
    dcm_file.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    dcm_file.is_little_endian = True
    dcm_file.is_implicit_VR = False


    # pydicom.dataset.validate_file_meta(dcm_file.file_meta, enforce_standard=True)
    for slice in range(ct.gridSize[2]):
        dcm_slice = copy.deepcopy(dcm_file)
        # meta data
        # meta = pydicom.dataset.FileMetaDataset()
        
        if (hasattr(ct, 'sopInstanceUIDs') and not ct.sopInstanceUIDs is None):
            dcm_slice.file_meta.MediaStorageSOPInstanceUID = ct.sopInstanceUIDs[slice]
            # meta.MediaStorageSOPInstanceUID = ct.sopInstanceUIDs[slice]
        else:
            dcm_slice.file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
            # meta.MediaStorageSOPInstanceUID = dcm_slice.file_meta.MediaStorageSOPInstanceUID
            
        # dcm_slice = copy.deepcopy(dcm_file)
        dcm_file.SOPClassUID = ct.mediaStorageSOPClassUID if hasattr(ct, 'mediaStorageSOPClassUID') else '1.2.840.10008.5.1.4.1.1.2'
        # dcm_slice.SOPInstanceUID = ct.sopInstanceUIDs[slice]
        dcm_slice.SOPInstanceUID = dcm_slice.file_meta.MediaStorageSOPInstanceUID
        dcm_slice.ImagePositionPatient[2] = floatToDS(slice*ct.spacing[2]+ct.origin[2])

        dcm_slice.SliceLocation = str(slice*ct.spacing[2]+ct.origin[2])
        dcm_slice.InstanceNumber = str(slice+1)

        # dcm_slice.SmallestImagePixelValue = np.min(outdata[:,:,slice]).astype(np.int16)
        # dcm_slice.LargestImagePixelValue  = np.max(outdata[:,:,slice]).astype(np.int16)
        # This causes an error because double backslash b'\\' is interpreted as a split leading
        # to interpretation as pydicom.multival.MultiValue instead of bytes

        dcm_slice.SmallestImagePixelValue = 0
        dcm_slice['SmallestImagePixelValue']._value = np.min(outdata[:,:,slice]).astype(np.int16).tobytes()

        dcm_slice.LargestImagePixelValue = 0
        dcm_slice['LargestImagePixelValue']._value = np.max(outdata[:,:,slice]).astype(np.int16).tobytes()

        dcm_slice.PixelData = outdata[:,:,slice].T.astype(np.int16).tobytes()

        if outputFileName:
            CTName = ''.join(letter for letter in outputFileName if letter.isalnum())
            filename = f'CT_{CTName}_{slice+1:04d}.dcm'
        elif hasattr(dcm_slice, 'SOPInstanceUID'):
            filename = f'CT_{dcm_slice.SOPInstanceUID}_{slice+1:04d}.dcm'
        else : 
            filename = f'CT_{slice+1:04d}.dcm'
        dcm_slice.save_as(os.path.join(outputFolderPath, filename))
        logger.info("Export dicom CT: " + filename + " in " + outputFolderPath)
    
    return dcm_file.SeriesInstanceUID


################### MRI Image ####################

def readDicomMRI(dcmFiles):
    """
    Generate a MR image object from a list of dicom MR slices.

    Parameters
    ----------
    dcmFiles: list
        List of paths for Dicom MR slices to be imported.

    Returns
    -------
    image: mrImage object
        The function returns the imported MR image
    """

    # read dicom slices
    images = []
    sopInstanceUIDs = []
    sliceLocation = np.zeros(len(dcmFiles), dtype='float')
    firstdcm = dcmFiles[0]
    
    if hasattr(firstdcm,'RescaleSlope') == False:
        logging.warning('no RescaleSlope, image could be wrong')
        for i in range(len(dcmFiles)):
            dcm = pydicom.dcmread(dcmFiles[i])
            sliceLocation[i] = float(dcm.ImagePositionPatient[2])
            images.append(dcm.pixel_array)
            sopInstanceUIDs.append(dcm.SOPInstanceUID)
    else :
        for i in range(len(dcmFiles)):
            dcm = pydicom.dcmread(dcmFiles[i])
            sliceLocation[i] = float(dcm.ImagePositionPatient[2])
            images.append(dcm.pixel_array * dcm.RescaleSlope + dcm.RescaleIntercept)
            sopInstanceUIDs.append(dcm.SOPInstanceUID)       

    # sort slices according to their location in order to reconstruct the 3d image
    sortIndex = np.argsort(sliceLocation)
    sliceLocation = sliceLocation[sortIndex]
    sopInstanceUIDs = [sopInstanceUIDs[n] for n in sortIndex]
    images = [images[n] for n in sortIndex]
    imageData = np.dstack(images).astype("float32").transpose(1, 0, 2)

    # verify reconstructed volume
    if imageData.shape[0:2] != (dcm.Columns, dcm.Rows):
        logging.warning("WARNING: GridSize " + str(imageData.shape[0:2]) + " different from Dicom Columns (" + str(
            dcm.Columns) + ") and Rows (" + str(dcm.Rows) + ")")

    # collect image information
    meanSliceDistance = (sliceLocation[-1] - sliceLocation[0]) / (len(images) - 1)
    if (hasattr(dcm, 'SliceThickness') and (
            type(dcm.SliceThickness) == int or type(dcm.SliceThickness) == float) and abs(
            meanSliceDistance - dcm.SliceThickness) > 0.001):
        logging.warning(
            "WARNING: Mean Slice Distance (" + str(meanSliceDistance) + ") is different from Slice Thickness (" + str(
                dcm.SliceThickness) + ")")

    if (hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""):
        imgName = dcm.SeriesDescription
    else:
        imgName = dcm.SeriesInstanceUID

    pixelSpacing = (float(dcm.PixelSpacing[1]), float(dcm.PixelSpacing[0]), meanSliceDistance)
    imagePositionPatient = (float(dcm.ImagePositionPatient[0]), float(dcm.ImagePositionPatient[1]), sliceLocation[0])

    # collect patient information
    if hasattr(dcm, 'PatientID'):
        birth = dcm.PatientBirthDate if hasattr(dcm, 'PatientBirthDate') else ""
        sex = dcm.PatientSex if hasattr(dcm, 'PatientSex') else None

        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=birth, sex=sex)
    else:
        patient = Patient()

    # generate MR image object
    FrameOfReferenceUID = dcm.FrameOfReferenceUID if hasattr(dcm, 'FrameOfReferenceUID') else pydicom.uid.generate_uid()
        
    image = MRImage(imageArray=imageData, name=imgName, origin=imagePositionPatient,
                    spacing=pixelSpacing, seriesInstanceUID=dcm.SeriesInstanceUID,
                    frameOfReferenceUID=FrameOfReferenceUID, sliceLocation=sliceLocation,
                    sopInstanceUIDs=sopInstanceUIDs)
       
    image.patient = patient
    # Collect MR information
    if hasattr(dcm, 'BodyPartExamined'):
        image.bodyPartExamined = dcm.BodyPartExamined
    if hasattr(dcm, 'ScanningSequence'):
        image.scanningSequence = dcm.ScanningSequence
    if hasattr(dcm, 'SequenceVariant'):
        image.sequenceVariant = dcm.SequenceVariant
    if hasattr(dcm, 'ScanOptions'):
        image.scanOptions = dcm.ScanOptions
    if hasattr(dcm, 'MRAcquisitionType'):
        image.mrArcquisitionType = dcm.MRAcquisitionType
    if hasattr(dcm, 'RepetitionTime'):
        image.repetitionTime = float(dcm.RepetitionTime)
    if hasattr(dcm, 'EchoTime'):
        if dcm.EchoTime is not None:
            image.echoTime = float(dcm.EchoTime)
    if hasattr(dcm, 'NumberOfAverages'):
        image.nAverages = float(dcm.NumberOfAverages)
    if hasattr(dcm, 'ImagingFrequency'):
        image.imagingFrequency = float(dcm.ImagingFrequency)
    if hasattr(dcm, 'EchoNumbers'):
        image.echoNumbers = int(dcm.EchoNumbers)
    if hasattr(dcm, 'MagneticFieldStrength'):
        image.magneticFieldStrength = float(dcm.MagneticFieldStrength)
    if hasattr(dcm, 'SpacingBetweenSlices'):
        image.spacingBetweenSlices = float(dcm.SpacingBetweenSlices)
    if hasattr(dcm, 'NumberOfPhaseEncodingSteps'):
        image.nPhaseSteps = int(dcm.NumberOfPhaseEncodingSteps)
    if hasattr(dcm, 'EchoTrainLength'):
        if dcm.EchoTrainLength is not None:
            image.echoTrainLength = int(dcm.EchoTrainLength)
    if hasattr(dcm, 'FlipAngle'):
        image.flipAngle = float(dcm.FlipAngle)
    if hasattr(dcm, 'SAR'):
        image.sar = float(dcm.SAR)
    if hasattr(dcm, 'StudyDate'):
        image.studyDate = float(dcm.StudyDate)
    if hasattr(dcm, 'StudyTime'):
        image.studyTime = float(dcm.StudyTime)
    if hasattr(dcm, 'AcquisitionTime'):
        image.acquisitionTime = float(dcm.AcquisitionTime)
    if hasattr(dcm, 'PatientPosition'):
        image.patientPosition = dcm.PatientPosition
    if hasattr(dcm, 'SeriesNumber'):
        image.seriesNumber = dcm.SeriesNumber
    image.studyInstanceUID = dcm.StudyInstanceUID if hasattr(dcm, 'StudyInstanceUID') else pydicom.uid.generate_uid()
    image.bitsAllocated = dcm.BitsAllocated if hasattr(dcm, 'BitsAllocated') else "16"
    image.bitsStored = dcm.BitsStored if hasattr(dcm, 'BitsStored') else ""
    image.samplesPerPixel = dcm.SamplesPerPixel if hasattr(dcm, 'SamplesPerPixel') else "1"
    image.hotometricInterpretation = dcm.PhotometricInterpretation if hasattr(dcm ,'PhotometricInterpretation') else 'MONOCHROME2'
    image.softwareVersions = 'syngo MR E11'
    
    return image

################## Dose Dicom ########################################
def readDicomDose(dcmFile):
    """
    Read a Dicom dose file and generate a dose image object.

    Parameters
    ----------
    dcmFile: str
        Path of the Dicom dose file.

    Returns
    -------
    image: doseImage object
        The function returns the imported dose image
    """

    dcm = pydicom.dcmread(dcmFile)

    # read image pixel data
    if ((hasattr(dcm, 'BitsStored') and dcm.BitsStored == 16) and (hasattr(dcm, 'PixelRepresentation') and dcm.PixelRepresentation == 0)):
        dt = np.dtype('uint16')
    elif ((hasattr(dcm, 'BitsStored') and dcm.BitsStored == 16) and (hasattr(dcm, 'PixelRepresentation') and dcm.PixelRepresentation == 1)):
        dt = np.dtype('int16')
    elif ((hasattr(dcm, 'BitsStored') and dcm.BitsStored == 32) and (hasattr(dcm, 'PixelRepresentation') and dcm.PixelRepresentation == 0)):
        dt = np.dtype('uint32')
    elif ((hasattr(dcm, 'BitsStored') and dcm.BitsStored == 32) and (hasattr(dcm, 'PixelRepresentation') and dcm.PixelRepresentation == 1)):
        dt = np.dtype('int32')
    else:
        logging.error("Error: Unknown data type for " + dcmFile)
        return None

    if (dcm.HighBit == dcm.BitsStored - 1):
        dt = dt.newbyteorder('L')
    else:
        dt = dt.newbyteorder('B')

    imageData = np.frombuffer(dcm.PixelData, dtype=dt)
    imageData = imageData.reshape((dcm.Columns, dcm.Rows, dcm.NumberOfFrames), order='F')
    imageData = imageData * dcm.DoseGridScaling

    # collect other information
    if (hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""):
        imgName = dcm.SeriesDescription
    else:
        imgName = dcm.SeriesInstanceUID

    planSOPInstanceUID = dcm.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID

    if (hasattr(dcm, 'SliceThickness') and dcm.SliceThickness != ""):
        sliceThickness = float(dcm.SliceThickness)
    else:
        if (hasattr(dcm, 'GridFrameOffsetVector') and not dcm.GridFrameOffsetVector is None):
            sliceThickness = abs((dcm.GridFrameOffsetVector[-1] - dcm.GridFrameOffsetVector[0]) / (len(dcm.GridFrameOffsetVector) - 1))
        else:
            sliceThickness = ""

    pixelSpacing = (float(dcm.PixelSpacing[1]), float(dcm.PixelSpacing[0]), sliceThickness)
    imagePositionPatient = tuple(dcm.ImagePositionPatient)

    # check image orientation
    # TODO use image angle instead
    gridFrameOffsetVector = None
    if hasattr(dcm, 'GridFrameOffsetVector') and not dcm.GridFrameOffsetVector is None:
        if (dcm.GridFrameOffsetVector[1] - dcm.GridFrameOffsetVector[0] < 0):
            imageData = np.flip(imageData, 2)

            # Note: Tuples are immutable so we cannot change their values. Our code returns an error.
            # Solution: Convert our “classes” tuple into a list. This will let us change the values in our sequence of class names
            imagePositionPatient_list = list(imagePositionPatient)
            imagePositionPatient_list[2] = imagePositionPatient[2] - imageData.shape[2] * pixelSpacing[2]
            imagePositionPatient=tuple(imagePositionPatient_list)
            
            gridFrameOffsetVector = list(np.arange(0, imageData.shape[2] * pixelSpacing[2], pixelSpacing[2]))
        else:
            gridFrameOffsetVector = dcm.GridFrameOffsetVector
         
    # collect patient information
    if hasattr(dcm, 'PatientID'):
        birth = dcm.PatientBirthDate if hasattr(dcm, 'PatientBirthDate') else ""
        sex = dcm.PatientSex if hasattr(dcm, 'PatientSex') else ""

        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=birth, sex=sex)
    else:
        patient = Patient()

    # generate dose image object
    referencedSOPInstanceUID= dcm.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID if hasattr(dcm.ReferencedRTPlanSequence[0], 'ReferencedSOPInstanceUID') else None
    image = DoseImage(imageArray=imageData, name=imgName, origin=imagePositionPatient,
                      spacing=pixelSpacing, seriesInstanceUID=dcm.SeriesInstanceUID, referencePlan = referencedSOPInstanceUID,
                      sopInstanceUID=dcm.SOPInstanceUID)

    image.patient = patient
    image.studyInstanceUID = dcm.StudyInstanceUID if hasattr(dcm, 'StudyInstanceUID') else pydicom.uid.generate_uid()
    image.seriesInstanceUID = dcm.SeriesInstanceUID if hasattr(dcm, 'SeriesInstanceUID') else pydicom.uid.generate_uid()
    image.sopInstanceUID = dcm.SOPInstanceUID if hasattr(dcm, 'SOPInstanceUID') else ""
    image.implementationClassUID = dcm.file_meta.ImplementationClassUID if hasattr(dcm.file_meta, 'ImplementationClassUID') else "1.2.826.0.1.3680043.1.2.100.6.40.0.76"
    image.fileMetaInformationGroupLength = dcm.file_meta.FileMetaInformationGroupLength if hasattr(dcm.file_meta, 'FileMetaInformationGroupLength') else 0
    image.fileMetaInformationVersion = dcm.file_meta.FileMetaInformationVersion if hasattr(dcm.file_meta, 'FileMetaInformationVersion') else bytes([0,1])
    image.implementationVersionName = dcm.file_meta.ImplementationVersionName if hasattr(dcm.file_meta, 'ImplementationVersionName') else "DicomObjects.NET"
    image.studyID = dcm.StudyID if hasattr(dcm, 'StudyID') else ""
    dt = datetime.datetime.now()
    image.studyDate = dcm.StudyDate if hasattr(dcm, 'StudyDate') else dt.strftime('%Y%m%d')
    image.studyTime = dcm.StudyTime if hasattr(dcm, 'StudyTime') else dt.strftime('%H%M%S.%f')
    image.seriesNumber = dcm.SeriesNumber if hasattr(dcm, 'SeriesNumber') else "1"
    image.instanceNumber = dcm.InstanceNumber if hasattr(dcm, 'InstanceNumber') else "1"
    image.patientOrientation = dcm.PatientOrientation if hasattr(dcm, 'PatientOrientation') else ""
    image.doseUnits = dcm.DoseUnits if hasattr(dcm, 'DoseUnits') else "GY"
    image.frameOfReferenceUID = dcm.FrameOfReferenceUID if hasattr(dcm, 'FrameOfReferenceUID') else pydicom.uid.generate_uid()
    image.photometricInterpretation = dcm.PhotometricInterpretation if hasattr(dcm, 'PhotometricInterpretation') else ""
    image.transferSyntaxUID = dcm.file_meta.TransferSyntaxUID if hasattr(dcm, 'TransferSyntaxUID') else "1.2.840.10008.1.2"
    image.frameIncrementPointer = dcm.FrameIncrementPointer if hasattr(dcm, 'FrameIncrementPointer') else {}
    image.doseType = dcm.DoseType if hasattr(dcm, 'DoseType') else "EFFECTIVE"
    image.doseSummationType = dcm.DoseSummationType if hasattr(dcm, 'DoseSummationType') else "PLAN"
    image.bitsAllocated = dcm.BitsAllocated if hasattr(dcm, 'BitsAllocated') else 16
    image.highBit = dcm.HighBit if hasattr(dcm, 'HighBit') else 15
    image.specificCharacterSet = dcm.SpecificCharacterSet if hasattr(dcm, 'SpecificCharacterSet') else "ISO_IR 100"
    image.accessionNumber = dcm.AccessionNumber if hasattr(dcm, 'AccessionNumber') else ""
    image.softwareVersion = dcm.SoftwareVersion if hasattr(dcm, 'SoftwareVersion') else ""
    image.bitsStored = dcm.BitsStored if hasattr(dcm, 'BitsStored') else 16
    image.modality = dcm.Modality if hasattr(dcm, 'Modality') else "RTDOSE"
    image.sopClassUID = dcm.SOPClassUID if hasattr(dcm, 'SOPClassUID') else "1.2.840.10008.5.1.4.1.1.481.2"
    image.referencedRTPlanSequence = dcm.ReferencedRTPlanSequence if hasattr(dcm, 'ReferencedRTPlanSequence') else []
    image.positionReferenceIndicator = dcm.PositionReferenceIndicator if hasattr(dcm, 'PositionReferenceIndicator') else ""
    image.gridFrameOffsetVector = gridFrameOffsetVector
    image.mediaStorageSOPInstanceUID = dcm.MediaStorageSOPInstanceUID if hasattr(dcm, 'MediaStorageSOPInstanceUID') else ""
    image.softwareVersions = dcm.SoftwareVersions if hasattr(dcm, 'SoftwareVersions') else "10.0.100.1 (Dicom Export)"

    return image

def writeRTDose(dose:DoseImage, outputFolder:str, outputFilename:str = None):
    """
    Export the dose data as a Dicom dose file

    Parameters
    ----------
    dose: DoseImage
        The dose image object.
    outputFolder:
        The output folder path
    """
        
    # meta data
    meta = pydicom.dataset.FileMetaDataset()
    sopUID = pydicom.uid.generate_uid()
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.481.2"
    if (hasattr(dose, 'mediaStorageSOPInstanceUID') and dose.mediaStorageSOPInstanceUID != "" and dose.mediaStorageSOPInstanceUID is not None):
        meta.MediaStorageSOPInstanceUID = dose.mediaStorageSOPInstanceUID
    else:
        meta.MediaStorageSOPInstanceUID = dose.sopInstanceUID if hasattr(dose, 'sopInstanceUID') and dose.sopInstanceUID != "" and not dose.sopInstanceUID is None else pydicom.uid.generate_uid()
    dt = datetime.datetime.now()
    # meta.ImplementationClassUID = '1.2.826.0.1.3680043.1.2.100.5.7.0.47' # from RayStation
    meta.ImplementationClassUID = dose.implementationClassUID if hasattr(dose, 'implementationClassUID') else "1.2.826.0.1.3680043.1.2.100.6.40.0.76"
    meta.FileMetaInformationGroupLength = 0
    meta.FileMetaInformationVersion = dose.fileMetaInformationVersion if hasattr(dose, 'fileMetaInformationVersion') else bytes([0,1])
    meta.ImplementationVersionName = dose.implementationVersionName if hasattr(dose, 'implementationVersionName') else "DicomObjects.NET"
    meta.TransferSyntaxUID = dose.transferSyntaxUID if hasattr(dose, 'transferSyntaxUID') else "1.2.840.10008.1.2"
    
    # dicom dataset
    dcm_file = pydicom.dataset.FileDataset(outputFolder, {}, file_meta=meta, preamble=b"\0" * 128)
    dcm_file.SOPClassUID = dose.sopClassUID if hasattr(dose, 'sopClassUID') else "1.2.840.10008.5.1.4.1.1.481.2"
    dcm_file.SOPInstanceUID = meta.MediaStorageSOPInstanceUID 
    dcm_file.AccessionNumber = dose.accessionNumber if hasattr(dose, 'accessionNumber') else ""
    dcm_file.SoftwareVersion = dose.softwareVersion if hasattr(dose, 'softwareVersion') else ""
    dcm_file.OperatorsName = dose.operatorsName if hasattr(dose, 'operatorsName') else ""
    dcm_file.FrameOfReferenceUID = dose.frameOfReferenceUID if hasattr(dose, 'frameOfReferenceUID') else pydicom.uid.generate_uid()

    # patient information
    if hasattr(dose, 'patient') and dose.patient is not None:
        dcm_file.PatientName = "exported_" + dose.patient.name if hasattr(dose.patient, 'name') else "exported_simple_patient"
        dcm_file.PatientID = dose.patient.id if hasattr(dose.patient, 'id') else dose.patient.name
        dcm_file.PatientBirthDate = dose.patient.birthDate if hasattr(dose.patient, 'birthDate') and not dose.patient.birthDate is None else ""
        dcm_file.PatientSex = dose.patient.sex if hasattr(dose.patient, 'sex') else ""
    else:
        dcm_file.PatientName = "exported_simple_patient" 
        dcm_file.PatientID =  "exported_simple_patient" 
        dcm_file.PatientBirthDate = ""
        dcm_file.PatientSex = ""
        
    # content information
    dcm_file.ContentDate = dt.strftime('%Y%m%d')
    dcm_file.ContentTime = dt.strftime('%H%M%S.%f')
    dcm_file.InstanceCreationDate = dt.strftime('%Y%m%d')
    dcm_file.InstanceCreationTime = dt.strftime('%H%M%S.%f')
    dcm_file.Modality = dose.modality if hasattr(dose, 'modality') else "RTDOSE"
    dcm_file.Manufacturer = 'OpenMCsquare'
    dcm_file.ManufacturerModelName = 'OpenTPS'
    dcm_file.SeriesDescription = dose.name if hasattr(dose, 'name') else ""
    
    dcm_file.StudyInstanceUID = dose.studyInstanceUID if hasattr(dose, 'studyInstanceUID') else pydicom.uid.generate_uid()
    dcm_file.StudyID = dose.studyID if hasattr(dose, 'studyID') else ""
    dcm_file.StudyDate = dose.studyDate if hasattr(dose, 'studyDate') else dt.strftime('%Y%m%d')
    dcm_file.StudyTime = dose.studyTime if hasattr(dose, 'studyTime') else dt.strftime('%H%M%S.%f')   
    
    dcm_file.SeriesInstanceUID = dose.seriesInstanceUID if hasattr(dose, 'seriesInstanceUID') else pydicom.uid.generate_uid()
    dcm_file.SeriesNumber = dose.seriesNumber if hasattr(dose, 'seriesNumber') else "1"
    dcm_file.InstanceNumber = dose.instanceNumber if hasattr(dose, 'instanceNumber') else "1"
    dcm_file.PatientOrientation = dose.patientOrientation if hasattr(dose, 'patientOrientation') else ""
    dcm_file.DoseUnits = dose.doseUnits if hasattr(dose, 'doseUnits') else "GY"
    # or 'EFFECTIVE' for RBE dose (but RayStation exports physical dose even if 1.1 factor is already taken into account)
    dcm_file.DoseType = dose.doseType  if hasattr(dose, 'doseType') else "EFFECTIVE"
    dcm_file.DoseSummationType = dose.doseSummationType if hasattr(dose, 'doseSummationType') else "PLAN"
    dcm_file.SoftwareVersions = dose.softwareVersions if hasattr(dose, 'softwareVersions') else "10.0.100.1 (Dicom Export)"
    
    if (hasattr(dose, 'referenceCT')):
        if (hasattr(dose.referenceCT, 'frameOfReferenceUID')):
            dcm_file.FrameOfReferenceUID = dose.referenceCT.frameOfReferenceUID
        if (hasattr(dose.referenceCT, 'studyInstanceUID')):
            dcm_file.StudyInstanceUID = dose.referenceCT.studyInstanceUID
    else:
        dcm_file.FrameOfReferenceUID = dose.frameOfReferenceUID if hasattr(dose, 'frameOfReferenceUID') else pydicom.uid.generate_uid()
      
    if not hasattr(dose, 'referencedRTPlanSequence'):
        ReferencedPlan = pydicom.dataset.Dataset()
        ReferencedPlan.ReferencedSOPClassUID = "1.2.840.10008.5.1.4.1.1.481.8"  # ion plan
        if dose.referencePlan is None:
            ReferencedPlan.ReferencedSOPInstanceUID = pydicom.uid.generate_uid()
        else:
            ReferencedPlan.ReferencedSOPInstanceUID = dose.referencePlan.SOPInstanceUID
        dcm_file.ReferencedRTPlanSequence = pydicom.sequence.Sequence([ReferencedPlan])
    else:
        dcm_file.ReferencedRTPlanSequence = dose.referencedRTPlanSequence
        for cindex, item in enumerate(dcm_file.ReferencedRTPlanSequence):
            if not dcm_file.ReferencedRTPlanSequence[cindex].ReferencedSOPClassUID:
                dcm_file.ReferencedRTPlanSequence[cindex].ReferencedSOPClassUID = "1.2.840.10008.5.1.4.1.1.481.8"

            if not dcm_file.ReferencedRTPlanSequence[cindex].ReferencedSOPInstanceUID:
                dcm_file.ReferencedRTPlanSequence[cindex].ReferencedSOPInstanceUID = pydicom.uid.generate_uid()
                
    dcm_file.ReferringPhysicianName = dose.referringPhysicianName if hasattr(dose, "referringPhysicianName") else ""
    dcm_file.OperatorName = dose.operatorName if hasattr(dose, 'operatorName') else ""

    # image information
    dcm_file.Width = dose.gridSize[0] if hasattr(dose, 'gridSize') else dose.imageArray.shape[0]
    dcm_file.Columns = dcm_file.Width
    dcm_file.Height = dose.gridSize[1] if hasattr(dose, 'gridSize') else dose.imageArray.shape[1]
    dcm_file.Rows = dcm_file.Height
    if (hasattr(dose, 'gridSize') and len(dose.gridSize) > 2):
        dcm_file.NumberOfFrames = dose.gridSize[2]
    else:
        dcm_file.NumberOfFrames = 1
        
    dcm_file.SliceThickness = dose.spacing[2] if hasattr(dose, 'spacing') else ""
    dcm_file.PixelSpacing = arrayToDS(dose.spacing[0:2]) if hasattr(dose, 'spacing') else ""
    dcm_file.ColorType = 'grayscale'
    dcm_file.ImagePositionPatient = arrayToDS(dose.origin) if hasattr(dose, 'origin') else ""
    dcm_file.ImageOrientationPatient = [1, 0, 0, 0, 1,
                                        0]  # HeadFirstSupine=1,0,0,0,1,0  FeetFirstSupine=-1,0,0,0,1,0  HeadFirstProne=-1,0,0,0,-1,0  FeetFirstProne=1,0,0,0,-1,0
    dcm_file.SamplesPerPixel = 1
    dcm_file.PhotometricInterpretation = 'MONOCHROME2'
    dcm_file.FrameIncrementPointer = dose.frameIncrementPointer if hasattr(dose, 'frameIncrementPointer') else {}
    dcm_file.PositionReferenceIndicator = dose.positionReferenceIndicator if hasattr(dose, 'positionReferenceIndicator') else ""
    
    if (hasattr(dose, 'gridSize') and len(dose.gridSize) > 2):
        dcm_file.GridFrameOffsetVector = list(np.arange(0, dose.gridSize[2] * dose.spacing[2], dose.spacing[2]))
    else:
        dcm_file.GridFrameOffsetVector = dose.gridFrameOffsetVector if hasattr(dose, 'gridFrameOffsetVector') and not(dose.gridFrameOffsetVector is None) else ""
    # transfer syntax
    dcm_file.is_little_endian = True
    # dcm_file.is_implicit_VR = False

    # image data
    dcm_file.BitDepth = 16
    dcm_file.BitsAllocated = dose.bitsAllocated if hasattr(dose, 'bitsAllocated') else dcm_file.BitDepth
    dcm_file.BitsStored = dose.bitsStored if hasattr(dose, 'bitsStored') else dcm_file.BitDepth
    dcm_file.HighBit = dose.highBit if hasattr(dose, 'highBit') else 15
    dcm_file.PixelRepresentation = 0  # 0=unsigned, 1=signed
    dcm_file.DoseGridScaling = floatToDS(dose.imageArray.max() / (2 ** dcm_file.BitDepth - 1) )
    if (len(dose.imageArray.shape) > 2):
        dcm_file.PixelData = (dose.imageArray / dcm_file.DoseGridScaling).astype(np.uint16).transpose(2, 1, 0).tostring()
    else:
        dcm_file.PixelData = (dose.imageArray / dcm_file.DoseGridScaling).astype(np.uint16).transpose(1, 0).tostring()
    
    # save dicom file
    if outputFilename:
        doseFilename = ''.join(letter for letter in outputFilename if letter.isalnum())
        filename = doseFilename + '.dcm'
    elif hasattr(dcm_file, 'SOPInstanceUID'):
        filename = f'RD{dcm_file.SOPInstanceUID}.dcm'
    else : 
        counter = 1
        # Loop until we find a filename that does not exist
        filename = f'RD.dcm'
        
    file_root, file_ext = os.path.splitext(filename)
    newFilename = filename
    counter = 1
    while os.path.exists(os.path.join(outputFolder, newFilename)):
        newFilename = f"{file_root}_{counter}{file_ext}"
        counter += 1
        
    logger.info("Export dicom RTDOSE: " + newFilename + " in " + outputFolder)
    dcm_file.save_as(os.path.join(outputFolder, newFilename))


def readDicomStruct(dcmFile):
    """
    Read a Dicom structure set file and generate a RTStruct object.

    Parameters
    ----------
    dcmFile: str
        Path of the Dicom RTstruct file.

    Returns
    -------
    struct: RTStruct object
        The function returns the imported structure set
    """
    # Read DICOM file
    dcm = pydicom.dcmread(dcmFile)
    dt = datetime.datetime.now()

    if (not hasattr(dcm, 'SeriesInstanceUID')):
        logging.error("Error: Unknown data type for " + dcmFile)
        return None

    if (hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""):
        structName = dcm.SeriesDescription
    else:
        structName = dcm.SeriesInstanceUID

    # collect patient information
    if hasattr(dcm, 'PatientID'):
        brth = dcm.PatientBirthDate if hasattr(dcm, 'PatientBirthDate') else ""
        sex = dcm.PatientSex if hasattr(dcm, 'PatientSex') else None

        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=brth, sex=sex)
    else:
        patient = Patient()

    # Create the object that will be returned. Takes the same patientInfo as the refImage it is linked to
    struct = RTStruct(name=structName, seriesInstanceUID=dcm.SeriesInstanceUID, sopInstanceUID=dcm.SOPInstanceUID)
    struct.patient = patient

    for dcmStruct in dcm.StructureSetROISequence:
        referencedRoiId = next(
            (x for x, val in enumerate(dcm.ROIContourSequence) if val.ReferencedROINumber == dcmStruct.ROINumber), -1)
        dcmContour = dcm.ROIContourSequence[referencedRoiId]

        if not hasattr(dcmContour, 'ContourSequence'):
            logging.warning("This structure [ ", dcmStruct.ROIName ," ]has no attribute ContourSequence. Skipping ...")
            continue

        # Create ROIContour object
        color = tuple([int(c) for c in list(dcmContour.ROIDisplayColor)])
        contour = ROIContour(name=dcmStruct.ROIName, displayColor=color,
                             referencedFrameOfReferenceUID=dcmStruct.ReferencedFrameOfReferenceUID)
        contour.patient = patient

        for dcmSlice in dcmContour.ContourSequence:
            contour.polygonMesh.append(dcmSlice.ContourData)  # list of coordinates (XYZ) for the polygon
            if hasattr(dcmSlice, 'ContourImageSequence'):
                contour.referencedSOPInstanceUIDs.append(dcmSlice.ContourImageSequence[
                                                         0].ReferencedSOPInstanceUID)  # UID of the image of reference (eg. ct slice)
        struct.appendContour(contour)
        
    struct.mediaStorageSOPClassUID = dcm.file_meta.MediaStorageSOPClassUID if hasattr(dcm.file_meta, 'MediaStorageSOPClassUID') else "1.2.840.10008.5.1.4.1.1.481.3"        
    struct.mediaStorageSOPInstanceUID = dcm.file_meta.MediaStorageSOPInstanceUID if hasattr(dcm, 'MediaStorageSOPInstanceUID') else ""
    struct.transferSyntaxUID = dcm.file_meta.TransferSyntaxUID if hasattr(dcm.file_meta, 'TransferSyntaxUID') else "1.2.840.10008.1.2"
    struct.implementationClassUID = dcm.file_meta.ImplementationClassUID if hasattr(dcm.file_meta, 'ImplementationClassUID') else "1.2.826.0.1.3680043.1.2.100.6.40.0.76"
    struct.implementationVersionName = dcm.file_meta.ImplementationVersionName if hasattr(dcm, 'ImplementationVersionName') else "DicomObjects.NET"
    struct.fileMetaInformationVersion = dcm.file_meta.FileMetaInformationVersion if hasattr(dcm, 'FileMetaInformationVersion') else bytes([0,1])
        
    # Data set
    struct.specificCharacterSet = dcm.SpecificCharacterSet if hasattr(dcm, 'SpecificCharacterSet') else "ISO_IR 100"
    struct.sopInstanceUID = dcm.SOPInstanceUID if hasattr(dcm, 'SOPInstanceUID') else ""
    struct.studyDate = dcm.StudyDate if hasattr(dcm, 'StudyDate') else dt.strftime('%Y%m%d')
    struct.seriesDate = dcm.SeriesDate if hasattr(dcm, 'SeriesDate') else dt.strftime('%Y%m%d')
    struct.studyTime = dcm.StudyTime if hasattr(dcm, 'StudyTime') else dt.strftime('%H%M%S.%f')
    struct.modality = dcm.Modality if hasattr(dcm, 'Modality') else "RTSTRUCT"
    struct.manufacturer = dcm.Manufacturer if hasattr(dcm, 'Manufacturer') else ""
    struct.seriesDescription = dcm.SeriesDescription if hasattr(dcm, 'SeriesDescription') else ""
    struct.manufacturerModelName = dcm.ManufacturerModelName if hasattr(dcm, 'ManufacturerModelName') else ""
    struct.patientName = dcm.PatientName if hasattr(dcm, 'PatientName') else ""
    struct.softwareVersions = dcm.SoftwareVersions if hasattr(dcm, 'SoftwareVersions') else "10.0.100.1 (Dicom Export)"
    struct.studyInstanceUID = dcm.StudyInstanceUID if hasattr(dcm, 'StudyInstanceUID') else ""
    struct.seriesInstanceUID = dcm.SeriesInstanceUID if hasattr(dcm, 'SeriesInstanceUID') else ""    
    struct.seriesNumber = dcm.SeriesNumber if hasattr(dcm, 'SeriesNumber') else "1"
    struct.instanceNumber = dcm.InstanceNumber if hasattr(dcm, 'InstanceNumber') else "1"
    struct.frameOfReferenceUID = dcm.FrameOfReferenceUID if hasattr(dcm, 'FrameOfReferenceUID') else pydicom.uid.generate_uid()
    struct.structureSetDate = dcm.StructureSetDate if hasattr(dcm, 'StructureSetDate') else dt.strftime('%Y%m%d')
    struct.structureSetTime = dcm.StructureSetTime if hasattr(dcm, 'StructureSetTime') else dt.strftime('%H%M%S.%f')
    struct.seriesTime = dcm.SeriesTime if hasattr(dcm, 'SeriesTime') else dt.strftime('%H%M%S.%f')
    struct.sopClassUID = dcm.SOPClassUID if hasattr(dcm, 'SOPClassUID') else "1.2.840.10008.5.1.4.1.1.481.3"
    struct.structureSetLabel = dcm.StructureSetLabel if hasattr(dcm, 'StructureSetLabel') else 'OpenTPS Created'
    struct.rtROIObservationsSequence = dcm.RTROIObservationsSequence if hasattr(dcm, 'RTROIObservationsSequence') else []
    if (hasattr(dcm, 'ReferencedFrameOfReferenceSequence')):
        struct.referencedFrameOfReferenceSequence = dcm.ReferencedFrameOfReferenceSequence
    struct.referringPhysicianName = dcm.ReferringPhysicianName if hasattr(dcm, 'ReferringPhysicianName') else ""
    struct.accessionNumber = struct.AccessionNumber if hasattr(struct, 'AccessionNumber') else ""
    struct.studyID = struct.StudyID if hasattr(struct, 'StudyID') else ""
    struct.operatorsName = struct.OperatorsName if hasattr(struct, 'OperatorsName') else ""
            
    return struct

def writeRTStruct(struct: RTStruct, outputFolder: str, outputFilename:str = None):
    """
    Export of TR structure data as a Dicom dose file.

    Parameters
    ----------
    struct: RTStruct
        The RTStruct object

    ctSeriesInstanceUID: str
        The serial instance UID of the CT associated with this RT structure.

    outputFolder: str
        The output folder path

    NOTE: Get the CT serial instance UID by calling the 'writeDicomCT' function.
    """
    
    # meta data
    meta = pydicom.dataset.FileMetaDataset()
    meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'
    if (hasattr(struct, 'mediaStorageSOPInstanceUID') and struct.mediaStorageSOPInstanceUID != "" and struct.mediaStorageSOPInstanceUID is not None):
        meta.MediaStorageSOPInstanceUID = struct.mediaStorageSOPInstanceUID
    else:
        meta.MediaStorageSOPInstanceUID = struct.sopInstanceUID if hasattr(struct, 'sopInstanceUID') and struct.sopInstanceUID != "" and not struct.sopInstanceUID is None else pydicom.uid.generate_uid()
    meta.ImplementationClassUID = struct.implementationClassUID if hasattr(struct, 'implementationClassUID') else "1.2.826.0.1.3680043.1.2.100.6.40.0.76"
    #'1.2.826.0.1.3680043.5.5.100.5.7.0.03'
    meta.TransferSyntaxUID = '1.2.840.10008.1.2'
    meta.ImplementationVersionName = struct.implementationVersionName if hasattr(struct, 'implementationVersionName') else "DicomObjects.NET"
    # NOTE: Don't modify this value
    meta.FileMetaInformationGroupLength = 0
    meta.FileMetaInformationVersion = struct.fileMetaInformationVersion if hasattr(struct, 'fileMetaInformationVersion') else bytes([0,1])
            
    # dicom dataset
    dcm_file = pydicom.dataset.FileDataset(outputFolder, {}, file_meta=meta, preamble=b"\0" * 128)
    dcm_file.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'
    dcm_file.SOPInstanceUID = meta.MediaStorageSOPInstanceUID

    # patient information
    if hasattr(struct, 'patient') and struct.patient is not None:
        dcm_file.PatientName = "exported_" + struct.patient.name if hasattr(struct.patient, 'name') else "exported_simple_patient"
        dcm_file.PatientID = struct.patient.id if hasattr(struct.patient, 'id') else ""
        dcm_file.PatientBirthDate = struct.patient.birthDate if hasattr(struct.patient, 'birthDate') else ""
        dcm_file.PatientSex = struct.patient.sex if hasattr(struct.patient, 'sex') else ""
    else:
        dcm_file.PatientName = "exported_simple_patient" 
        dcm_file.PatientID = "exported_simple_patient" 
        dcm_file.PatientBirthDate = ""
        dcm_file.PatientSex = ""
    
    # content information
    dt = datetime.datetime.now()
    dcm_file.ContentDate = dt.strftime('%Y%m%d')
    dcm_file.ContentTime = dt.strftime('%H%M%S.%f')
    dcm_file.InstanceCreationDate = dt.strftime('%Y%m%d')
    dcm_file.InstanceCreationTime = dt.strftime('%H%M%S.%f')
    dcm_file.Modality = struct.modality if hasattr(struct, 'modality') else 'RTDOSE'
    dcm_file.Manufacturer = 'OpenMCsquare'
    dcm_file.ManufacturerModelName = 'OpenTPS'
    dcm_file.SeriesDescription = struct.name if hasattr(struct, 'name') else ""
    dcm_file.ReferringPhysicianName = struct.referringPhysicianName if hasattr(struct, 'referringPhysicianName') else ""
    dcm_file.OperatorsName = struct.OperatorsName if hasattr(struct, 'OperatorsName') else ""

    dcm_file.StudyInstanceUID = struct.studyInstanceUID + "1" if hasattr(struct, 'studyInstanceUID') else pydicom.uid.generate_uid()
    dcm_file.SeriesInstanceUID = struct.seriesInstanceUID if hasattr(struct, 'seriesInstanceUID') else pydicom.uid.generate_uid()
    dcm_file.SeriesNumber = "2"
    dcm_file.InstanceNumber = "1"

    dcm_file.StudyTime = struct.studyTime if hasattr(struct, 'studyTime') else dt.strftime('%H%M%S.%f')
    dcm_file.SeriesTime = struct.seriesTime if hasattr(struct, 'seriesTime') else dt.strftime('%H%M%S.%f')
    # dcm_file.FrameOfReferenceUID = struct.frameOfReferenceUID if hasattr(struct, 'frameOfReferenceUID') else pydicom.uid.generate_uid()
    dcm_file.StructureSetDate = struct.structureSetDate if hasattr(struct, 'structureSetDate') else dt.strftime('%Y%m%d')
    dcm_file.StructureSetTime = struct.structureSetTime if hasattr(struct, 'structureSetTime') else dt.strftime('%H%M%S.%f')
    dcm_file.SOPClassUID = struct.sopClassUID if hasattr(struct, 'sopClassUID') else meta.MediaStorageSOPClassUID
    dcm_file.StudyDate = struct.studyDate if hasattr(struct, 'studyDate') else dt.strftime('%Y%m%d')
    dcm_file.SeriesDate = struct.seriesDate if hasattr(struct, 'seriesDate') else dt.strftime('%Y%m%d')
    dcm_file.StructureSetLabel = struct.structureSetLabel if hasattr(struct, 'structureSetLabel') else ""
    
    if hasattr(struct, 'referencedFrameOfReferenceSequence'):
        dcm_file.ReferencedFrameOfReferenceSequence = []
        for item in struct.referencedFrameOfReferenceSequence:
            refFrameRef = pydicom.Dataset()
            if hasattr(item, 'FrameOfReferenceUID'):
                refFrameRef.FrameOfReferenceUID = item.FrameOfReferenceUID
            rtRefSub1 = []
            if hasattr(item, 'RTReferencedStudySequence'):
                for subItem1 in item.RTReferencedStudySequence:
                    rtRefSubObj1=pydicom.Dataset()
                    rtRefSubObj1.ReferencedSOPClassUID = subItem1.ReferencedSOPClassUID if hasattr(subItem1, 'ReferencedSOPClassUID') else '1.2.840.10008.3.1.2.3.1'
                    rtRefSubObj1.ReferencedSOPInstanceUID = subItem1.ReferencedSOPInstanceUID if hasattr(subItem1, 'ReferencedSOPInstanceUID') else pydicom.uid.generate_uid()
                    rtRefSub2 = []
                    for subItem2 in subItem1.RTReferencedSeriesSequence:
                        rtRefSubObject2 = pydicom.Dataset()
                        rtRefSubObject2.SeriesInstanceUID = subItem2.SeriesInstanceUID
                        contourSeq = []
                        for subItem3 in subItem2.ContourImageSequence:
                            contourSeqObj=pydicom.dataset.Dataset()
                            contourSeqObj.ReferencedSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
                            contourSeqObj.ReferencedSOPInstanceUID = subItem3.ReferencedSOPInstanceUID if hasattr(subItem3, 'ReferencedSOPInstanceUID') else pydicom.uid.generate_uid()
                            contourSeq.append(contourSeqObj)
                        rtRefSubObject2.ContourImageSequence = contourSeq
                    rtRefSub2.append(rtRefSubObject2)
                    rtRefSubObj1.RTReferencedSeriesSequence = rtRefSub2
                rtRefSub1.append(rtRefSubObj1)
            refFrameRef.RTReferencedStudySequence = rtRefSub1
        dcm_file.ReferencedFrameOfReferenceSequence.append(refFrameRef)

    dcm_file.SamplesPerPixel = 1
    dcm_file.PhotometricInterpretation = 'MONOCHROME2'
    dcm_file.AccessionNumber = struct.accessionNumber if hasattr(struct, 'accessionNumber') else ""
    dcm_file.StudyID = struct.studyID if hasattr(struct, 'studyID') else ""
    
    dcm_file.RTROIObservationsSequence = []
    if hasattr(struct, 'rtROIObservationsSequence'):
        for cidx, item in enumerate(struct.rtROIObservationsSequence, start=1):
            roiObs = pydicom.Dataset()
            roiObs.ObservationNumber = item.ObservationNumber if hasattr(item, 'ObservationNumber') else ''
            roiObs.ReferencedROINumber = item.ReferencedROINumber if hasattr(item, 'ReferencedROINumber') else ''
            roiObs.ROIObservationLabel = item.ROIObservationLabel if hasattr(item, 'ROIObservationLabel') else ''
            roiObs.RTROIInterpretedType = item.RTROIInterpretedType if hasattr(item, 'RTROIInterpretedType') else 'NONE'
            roiObs.ROIInterpreter = item.ROIInterpreter if hasattr(item, 'ROIInterpreter') else 'None'
            dcm_file.RTROIObservationsSequence.append(roiObs)

    dcm_file.StructureSetROISequence = []
    dcm_file.ROIContourSequence = []

    for cidx,contour in enumerate(struct.contours, start=1):
        # StructureSetROISequence
        roi = pydicom.Dataset()
        roi.ROINumber = cidx
        roi.ROIName = contour.name
        roi.ReferencedFrameOfReferenceUID = contour.referencedFrameOfReferenceUID
        roi.ROIGenerationAlgorithm = "AUTOMATIC"
        dcm_file.StructureSetROISequence.append(roi)

        # ROIContourSequence
        con = pydicom.Dataset()
        con.ReferencedROINumber = cidx
        con.ROIDisplayColor = str(contour.color[0])+"\\"+str(contour.color[1])+"\\"+str(contour.color[2])
        con.ContourSequence = []
        for midx,mesh in enumerate(contour.polygonMesh):
            slc = pydicom.Dataset()
            slc.ContourData = mesh
            slc.ContourGeometricType = "CLOSED_PLANAR"
            slc.NumberOfContourPoints = len(mesh) // 3
            con.ContourSequence.append(slc)
        dcm_file.ROIContourSequence.append(con)
 
    # save rt struct dicom file
    if outputFilename:
        contourFilename = ''.join(letter for letter in outputFilename if letter.isalnum())
        filename = contourFilename + '.dcm'
    elif hasattr(dcm_file, 'SOPInstanceUID'):
        filename = f'RS{dcm_file.SOPInstanceUID}.dcm'
    else : 
        filename = f'RS.dcm'

    file_root, file_ext = os.path.splitext(filename)
    newFilename = filename
    counter = 1
    while os.path.exists(os.path.join(outputFolder, newFilename)):
        newFilename = f"{file_root}_{counter}{file_ext}"
        counter += 1

    dcm_file.save_as(os.path.join(outputFolder, newFilename))
    logger.info("Export dicom RTSTRUCT: " + newFilename + ' in ' +  outputFolder)

################### Plan Image ############################################
def readDicomPlan(dcmFile) -> RTPlan:
    """
    Read a Dicom plan file and generate a RTPlan object.

    Parameters
    ----------
    dcmFile: str
        Path of the Dicom plan file.

    Returns
    -------
    plan: RTPlan object
        The function returns the imported plan
    """
    dcm = pydicom.dcmread(dcmFile)

    # collect patient information
    if hasattr(dcm, 'PatientID'):
        birth = dcm.PatientBirthDate if hasattr(dcm, 'PatientBirthDate') else ""        
        sex = dcm.PatientSex if hasattr(dcm, 'PatientSex') else ''
        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=birth,
                      sex=sex)
    else:
        patient = Patient()

    if (hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""):
        name = dcm.SeriesDescription
    else:
        name = dcm.SeriesInstanceUID

    plan = RTPlan(name=name, patient = patient)
    plan.patient = patient
    
    # Photon plan
    if dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.5":
        logger.warning("ERROR: Conventional radiotherapy (photon) plans are not supported")
        plan.modality = "RT Plan IOD"
        return

    # Ion plan
    elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.8":

        plan.modality = "RT Ion Plan IOD"

        if dcm.IonBeamSequence[0].RadiationType == "PROTON":
            plan.radiationType = "Proton"
        else:
            logger.warning("ERROR: Radiation type " + dcm.IonBeamSequence[0].RadiationType + " not supported")
            plan.radiationType = dcm.IonBeamSequence[0].RadiationType
            return

        if dcm.IonBeamSequence[0].ScanMode == "MODULATED":
            plan.scanMode = "MODULATED"  # PBS
        elif dcm.IonBeamSequence[0].ScanMode == "LINE":
            plan.scanMode = "LINE"  # Line Scanning
        else:
            logger.warning("ERROR: Scan mode " + dcm.IonBeamSequence[0].ScanMode + " not supported")
            plan.scanMode = dcm.IonBeamSequence[0].ScanMode
            return

            # Other
    else:
        logger.warning("ERROR: Unknown SOPClassUID " + dcm.SOPClassUID + " for file " + plan.DcmFile)
        plan.modality = ""
        return

    # Start parsing PBS plan
    plan.numberOfFractionsPlanned = int(dcm.FractionGroupSequence[0].NumberOfFractionsPlanned)
    plan.numberOfBeams = int(dcm.FractionGroupSequence[0].NumberOfBeams) if hasattr(dcm.FractionGroupSequence[0], 'NumberOfBeams') else len(dcm.IonBeamSequence)
    plan.fractionGroupNumber = int(dcm.FractionGroupSequence[0].FractionGroupNumber) if hasattr(dcm.FractionGroupSequence[0], 'FractionGroupNumber') else 1   
    if (hasattr(dcm.IonBeamSequence[0], 'TreatmentMachineName')):
        plan.treatmentMachineName = dcm.IonBeamSequence[0].TreatmentMachineName if hasattr(dcm.IonBeamSequence[0], 'TreatmentMachineName') else ''
    else:
        plan.treatmentMachineName = ""

    for dcm_beam in dcm.IonBeamSequence:
        if dcm_beam.TreatmentDeliveryType != "TREATMENT":
            continue

        first_layer = dcm_beam.IonControlPointSequence[0]

        beam = PlanIonBeam()
        beam.seriesInstanceUID = plan.seriesInstanceUID
        beam.name = dcm_beam.BeamName
        beam.isocenterPosition = [float(first_layer.IsocenterPosition[0]), float(first_layer.IsocenterPosition[1]),
                                  float(first_layer.IsocenterPosition[2])]
        beam.gantryAngle = float(first_layer.GantryAngle)
        beam.patientSupportAngle = float(first_layer.PatientSupportAngle)
        finalCumulativeMetersetWeight = float(dcm_beam.FinalCumulativeMetersetWeight)

        # find corresponding beam in FractionGroupSequence (beam order may be different from IonBeamSequence)
        ReferencedBeam_id = next((x for x, val in enumerate(dcm.FractionGroupSequence[0].ReferencedBeamSequence) if
                                  val.ReferencedBeamNumber == dcm_beam.BeamNumber), -1)
        if ReferencedBeam_id == -1:
            logger.warning("ERROR: Beam number " + dcm_beam.BeamNumber + " not found in FractionGroupSequence.")
            logger.warning("This beam is therefore discarded.")
            continue
        else:
            beamMeterset = float(dcm.FractionGroupSequence[0].ReferencedBeamSequence[ReferencedBeam_id].BeamMeterset)

        if dcm_beam.NumberOfRangeShifters == 0:
            # beam.rangeShifter.ID = ""
            # beam.rangeShifterType = "none"
            pass
        elif dcm_beam.NumberOfRangeShifters == 1:
            beam.rangeShifter = RangeShifter()
            beam.rangeShifter.ID = dcm_beam.RangeShifterSequence[0].RangeShifterID
            if dcm_beam.RangeShifterSequence[0].RangeShifterType == "BINARY":
                beam.rangeShifter.type = "binary"
            elif dcm_beam.RangeShifterSequence[0].RangeShifterType == "ANALOG":
                beam.rangeShifter.type = "analog"
            else:
                logger.warning("ERROR: Unknown range shifter type for beam " + dcm_beam.BeamName if hasattr(dcm_beam, 'BeamName') else 'No beam name')
                # beam.rangeShifter.type = "none"
        else:
            logger.warning("ERROR: More than one range shifter defined for beam " + dcm_beam.BeamName if hasattr(dcm_beam, 'BeamName') else 'No beam name')
            # beam.rangeShifterID = ""
            # beam.rangeShifterType = "none"

        SnoutPosition = 0
        if hasattr(first_layer, 'SnoutPosition'):
            SnoutPosition = float(first_layer.SnoutPosition)

        IsocenterToRangeShifterDistance = SnoutPosition
        RangeShifterWaterEquivalentThickness = None
        RangeShifterSetting = "OUT"
        ReferencedRangeShifterNumber = 0

        if hasattr(first_layer, 'RangeShifterSettingsSequence'):
            if hasattr(first_layer.RangeShifterSettingsSequence[0], 'IsocenterToRangeShifterDistance'):
                IsocenterToRangeShifterDistance = float(
                    first_layer.RangeShifterSettingsSequence[0].IsocenterToRangeShifterDistance)
            if hasattr(first_layer.RangeShifterSettingsSequence[0], 'RangeShifterWaterEquivalentThickness'):
                RangeShifterWaterEquivalentThickness = float(
                    first_layer.RangeShifterSettingsSequence[0].RangeShifterWaterEquivalentThickness)
            if hasattr(first_layer.RangeShifterSettingsSequence[0], 'RangeShifterSetting'):
                RangeShifterSetting = first_layer.RangeShifterSettingsSequence[0].RangeShifterSetting
            if hasattr(first_layer.RangeShifterSettingsSequence[0], 'ReferencedRangeShifterNumber'):
                ReferencedRangeShifterNumber = int(
                    first_layer.RangeShifterSettingsSequence[0].ReferencedRangeShifterNumber)

        for dcm_layer in dcm_beam.IonControlPointSequence:
            if (plan.scanMode == "MODULATED"):
                if dcm_layer.NumberOfScanSpotPositions == 1:
                    sum_weights = dcm_layer.ScanSpotMetersetWeights
                else:
                    sum_weights = sum(dcm_layer.ScanSpotMetersetWeights)

            elif (plan.scanMode == "LINE"):
                sum_weights = sum(np.frombuffer(dcm_layer[0x300b1096].value, dtype=np.float32).tolist())

            if sum_weights == 0.0:
                continue

            layer = PlanIonLayer()
            layer.seriesInstanceUID = plan.seriesInstanceUID

            if hasattr(dcm_layer, 'SnoutPosition'):
                SnoutPosition = float(dcm_layer.SnoutPosition)

            if hasattr(dcm_layer, 'NumberOfPaintings'):
                layer.numberOfPaintings = int(dcm_layer.NumberOfPaintings)
            else:
                layer.numberOfPaintings = 1

            layer.nominalEnergy = floatToDS(dcm_layer.NominalBeamEnergy)
            layer.scalingFactor = beamMeterset / finalCumulativeMetersetWeight

            if (plan.scanMode == "MODULATED"):
                _x = dcm_layer.ScanSpotPositionMap[0::2]
                _y = dcm_layer.ScanSpotPositionMap[1::2]
                mu = np.array(
                    dcm_layer.ScanSpotMetersetWeights) * layer.scalingFactor  # spot weights are converted to MU
                layer.appendSpot(_x, _y, mu)

            elif (plan.scanMode == "LINE"):
                raise NotImplementedError()
                # print("SpotNumber: ", dcm_layer[0x300b1092].value)
                # print("SpotValue: ", np.frombuffer(dcm_layer[0x300b1094].value, dtype=np.float32).tolist())
                # print("MUValue: ", np.frombuffer(dcm_layer[0x300b1096].value, dtype=np.float32).tolist())
                # print("SizeValue: ", np.frombuffer(dcm_layer[0x300b1098].value, dtype=np.float32).tolist())
                # print("PaintValue: ", dcm_layer[0x300b109a].value)
                LineScanPoints = np.frombuffer(dcm_layer[0x300b1094].value, dtype=np.float32).tolist()
                layer.LineScanControlPoint_x = LineScanPoints[0::2]
                layer.LineScanControlPoint_y = LineScanPoints[1::2]
                layer.LineScanControlPoint_Weights = np.frombuffer(dcm_layer[0x300b1096].value,
                                                                   dtype=np.float32).tolist()
                layer.LineScanControlPoint_MU = np.array(
                    layer.LineScanControlPoint_Weights) * layer.scalingFactor  # weights are converted to MU
                if layer.LineScanControlPoint_MU.size == 1:
                    layer.LineScanControlPoint_MU = [layer.LineScanControlPoint_MU]
                else:
                    layer.LineScanControlPoint_MU = layer.LineScanControlPoint_MU.tolist()

            if beam.rangeShifter is not None:
                if hasattr(dcm_layer, 'RangeShifterSettingsSequence'):
                    RangeShifterSetting = dcm_layer.RangeShifterSettingsSequence[0].RangeShifterSetting
                    ReferencedRangeShifterNumber = dcm_layer.RangeShifterSettingsSequence[
                        0].ReferencedRangeShifterNumber
                    if hasattr(dcm_layer.RangeShifterSettingsSequence[0], 'IsocenterToRangeShifterDistance'):
                        IsocenterToRangeShifterDistance = dcm_layer.RangeShifterSettingsSequence[
                            0].IsocenterToRangeShifterDistance
                    if hasattr(dcm_layer.RangeShifterSettingsSequence[0], 'RangeShifterWaterEquivalentThickness'):
                        RangeShifterWaterEquivalentThickness = float(
                            dcm_layer.RangeShifterSettingsSequence[0].RangeShifterWaterEquivalentThickness)

                layer.rangeShifterSettings.rangeShifterSetting = RangeShifterSetting
                layer.rangeShifterSettings.isocenterToRangeShifterDistance = IsocenterToRangeShifterDistance
                layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness = RangeShifterWaterEquivalentThickness
                layer.rangeShifterSettings.referencedRangeShifterNumber = ReferencedRangeShifterNumber

            beam.appendLayer(layer)
        plan.appendBeam(beam)
        
        dt = datetime.datetime.now()
        plan.fileMetaInformationGroupLength = dcm.file_meta.FileMetaInformationGroupLength if hasattr(dcm.file_meta, 'FileMetaInformationGroupLength') else 0
        plan.mediaStorageSOPClassUID=dcm.file_meta.MediaStorageSOPClassUID if hasattr(dcm.file_meta, 'MediaStorageSOPClassUID') else "1.2.840.10008.5.1.4.1.1.481.8"          
        plan.transferSyntaxUID=dcm.file_meta.TransferSyntaxUID if hasattr(dcm.file_meta, 'TransferSyntaxUID') else "1.2.840.10008.1.2"
        plan.implementationClassUID=dcm.file_meta.ImplementationClassUID if hasattr(dcm.file_meta, 'ImplementationClassUID') else "1.2.826.0.1.3680043.1.2.100.6.40.0.76"
        plan.implementationVersionName=dcm.file_meta.ImplementationVersionName if hasattr(dcm.file_meta, 'ImplementationVersionName') else "DicomObjects.NET"
        plan.fileMetaInformationVersion=dcm.file_meta.FileMetaInformationVersion if hasattr(dcm.file_meta, 'FileMetaInformationVersion') else bytes([0,1])
        if (hasattr(dcm.file_meta, 'MediaStorageSOPInstanceUID')):
            plan.mediaStorageSOPInstanceUID = dcm.file_meta.MediaStorageSOPInstanceUID
        else:
            plan.mediaStorageSOPInstanceUID = dcm.SOPInstanceUID if hasattr(dcm, 'SOPInstanceUID') else pydicom.uid.generate_uid()
    
        plan.specificCharacterSet = dcm.SpecificCharacterSet if hasattr(dcm, 'SpecificCharacterSet') else "ISO_IR 100"
        plan.studyDate = dcm.StudyDate if hasattr(dcm, 'StudyDate') else dt.strftime('%Y%m%d')
        plan.seriesDate = dcm.SeriesDate if hasattr(dcm, 'SeriesDate') else dt.strftime('%Y%m%d')
        plan.studyTime = dcm.StudyTime if hasattr(dcm, 'StudyTime') else  dt.strftime('%H%M%S.%f')
        plan.sopInstanceUID = dcm.SOPInstanceUID if hasattr(dcm, 'SOPInstanceUID') else plan.mediaStorageSOPClassUID
        plan.modality = dcm.Modality if hasattr(dcm, 'Modality') else ""
        plan.seriesDescription = dcm.SeriesDescription if hasattr(dcm, 'SeriesDescription') else ""
        plan.softwareVersions=dcm.SoftwareVersions if hasattr(dcm, 'SoftwareVersions') else "10.0.100.1 (Dicom Export)"
        plan.studyInstanceUID=dcm.StudyInstanceUID if hasattr(dcm, 'StudyInstanceUID') else pydicom.uid.generate_uid()
        plan.studyID = dcm.StudyID if hasattr(dcm, 'StudyID') else ""
        plan.seriesNumber = dcm.SeriesNumber if hasattr(dcm, 'SeriesNumber') else "1"
        plan.frameOfReferenceUID = dcm.FrameOfReferenceUID if hasattr(dcm, 'FrameOfReferenceUID') else pydicom.uid.generate_uid()
        plan.rtPlanLabel = dcm.RTPlanLabel if hasattr(dcm, 'RTPlanLabel') else "Unkonwn"
        plan.rtPlanName = dcm.RTPlanName if hasattr(dcm, 'RTPlanName') else ""
        plan.rtPlanDate = dcm.RTPlanDate if hasattr(dcm, 'RTPlanDate') else dt.strftime('%Y%m%d')
        plan.rtPlanTime = dcm.RTPlanTime if hasattr(dcm, 'RTPlanTime') else dt.strftime('%H%M%S.%f')
        plan.treatmentProtocols = dcm.TreatmentProtocols if hasattr(dcm, 'TreatmentProtocols') else ""
        plan.planIntent = dcm.PlanIntent if hasattr(dcm, 'PlanIntent') else ""
        plan.rtPlanGeometry = dcm.RTPlanGeometry if hasattr(dcm, 'RTPlanGeometry') else "PATIENT"
        plan.prescriptionDescription = dcm.PrescriptionDescription if hasattr(dcm, 'PrescriptionDescription') else ""
        plan.sopClassUID = dcm.SOPClassUID if hasattr(dcm, 'SOPClassUID') else "1.2.840.10008.5.1.4.1.1.481.8"
        
        plan.doseReferenceSequence=dcm.DoseReferenceSequence if hasattr(dcm, 'DoseReferenceSequence') else []
        plan.fractionGroupSequence = dcm.FractionGroupSequence if hasattr(dcm, 'FractionGroupSequence') else []
        plan.referencedStructureSetSequence = dcm.ReferencedStructureSetSequence if hasattr(dcm, 'ReferencedStructureSetSequence') else []
        plan.ionBeamSequence = dcm.IonBeamSequence if hasattr(dcm, 'IonBeamSequence') else []
        plan.patientSetupSequence = dcm.PatientSetupSequence if hasattr(dcm, 'PatientSetupSequence') else []
        
        plan.referringPhysicianName = dcm.ReferringPhysicianName if hasattr(dcm, 'ReferringPhysicianName') else ""
        plan.accessionNumber = dcm.AccessionNumber if hasattr(dcm, 'AccessionNumber') else ""
        plan.operatorsName = dcm.OperatorsName if hasattr(dcm, 'OperatorsName') else ""
        plan.positionReferenceIndicator = dcm.PositionReferenceIndicator if hasattr(dcm, 'PositionReferenceIndicator') else ""
        plan.privateCreator = dcm.PrivateCreator if hasattr(plan, 'PrivateCreator') else "OpenTPS"
        plan.approvalStatus = dcm.ApprovalStatus if hasattr(plan, 'ApprovalStatus') else "UNAPPROVED"
                
    return plan

def writeRTPlan(plan: RTPlan, outputFolder:str, outputFilename:str=None, struct: RTStruct=None):
    """
    Write a RTPlan object to a dicom file

    Parameters
    ----------
    plan : RTPlan
        the RTPlan object to be written.
    outputFolder : str
        path to the dicom folder

    """

    # meta data
    meta = pydicom.dataset.FileMetaDataset()
    meta.FileMetaInformationGroupLength = plan.fileMetaInformationGroupLength if hasattr(plan, 'fileMetaInformationGroupLength') else 0
    meta.MediaStorageSOPClassUID = plan.mediaStorageSOPClassUID if hasattr(plan, 'mediaStorageSOPClassUID') else "1.2.840.10008.5.1.4.1.1.481.8"
    meta.ImplementationClassUID = plan.implementationClassUID if hasattr(plan, 'implementationClassUID') else "1.2.826.0.1.3680043.1.2.100.6.40.0.76"
    meta.TransferSyntaxUID = plan.transferSyntaxUID if hasattr(plan, 'transferSyntaxUID') else "1.2.840.10008.1.2"
    meta.ImplementationVersionName = plan.implementationVersionName if hasattr(plan, 'implementationVersionName') else "DicomObjects.NET"
    meta.FileMetaInformationVersion = plan.fileMetaInformationVersion if hasattr(plan, 'fileMetaInformationVersion') else bytes([0,1])
    if (hasattr(plan, 'mediaStorageSOPInstanceUID') and plan.mediaStorageSOPInstanceUID != "" and not plan.mediaStorageSOPInstanceUID is None):
        meta.MediaStorageSOPInstanceUID = plan.mediaStorageSOPInstanceUID
    else:
        meta.MediaStorageSOPInstanceUID = plan.sopInstanceUID if hasattr(plan, 'sopInstanceUID') and plan.sopInstanceUID != "" and not plan.sopInstanceUID is None else pydicom.uid.generate_uid()
    
    # dicom dataset
    dcm_file = pydicom.dataset.FileDataset(outputFolder, {}, file_meta=meta, preamble=b"\0" * 128)
    dcm_file.SOPClassUID = plan.sopClassUID if hasattr(plan, 'sopClassUID') else "1.2.840.10008.5.1.4.1.1.481.8"
    dcm_file.SOPInstanceUID = plan.sopInstanceUID if hasattr(plan, 'sopInstanceUID') else meta.MediaStorageSOPInstanceUID
    
    # patient information
    if hasattr(plan, 'patient') and plan.patient is not None:
        dcm_file.PatientName = "exported_" + plan.patient.name if hasattr(plan.patient, 'name') else "exported_simple_patient"
        dcm_file.PatientID = plan.patient.id if hasattr(plan.patient, 'id') else plan.patient.name
        dcm_file.PatientBirthDate = plan.patient.birthDate if hasattr(plan.patient, 'birthDate') and not plan.patient.birthDate is None else ""
        dcm_file.PatientSex = plan.patient.sex if hasattr(plan.patient, 'sex') else ""
    else:
        dcm_file.PatientName = "exported_simple_patient" 
        dcm_file.PatientID = "exported_simple_patient" 
        dcm_file.PatientBirthDate = ""
        dcm_file.PatientSex = ""
    
    # content information
    dt = datetime.datetime.now()
    dcm_file.ContentDate = dt.strftime('%Y%m%d')
    dcm_file.ContentTime = dt.strftime('%H%M%S.%f')
    dcm_file.InstanceCreationDate = dt.strftime('%Y%m%d')
    dcm_file.InstanceCreationTime = dt.strftime('%H%M%S.%f')
    if (hasattr(plan, 'modality') and plan.modality != 'Ion therapy' and plan.modality != ""):
        dcm_file.Modality = plan.modality
    else:
        dcm_file.Modality = 'RTPLAN'
        
    dcm_file.Manufacturer = 'OpenMCsquare'
    dcm_file.ManufacturerModelName = 'OpenTPS'
    dcm_file.SeriesDescription = plan.seriesDescription if hasattr(plan, 'seriesDescription') else ""
    dcm_file.StudyInstanceUID = plan.studyInstanceUID if hasattr(plan, 'studyInstanceUID') else pydicom.uid.generate_uid()
        
    dcm_file.StudyID = plan.studyID if hasattr(plan, 'studyID') else ""
    dcm_file.StudyDate = plan.studyDate if hasattr(plan, 'studyDate') else dt.strftime('%Y%m%d')
    dcm_file.StudyTime = plan.studyTime if hasattr(plan, 'studyTime') else dt.strftime('%H%M%S.%f')
    dcm_file.SpecificCharacterSet = plan.specificCharacterSet if hasattr(plan, 'specificCharacterSet') else "ISO_IR 100"
    dcm_file.SeriesDate = plan.seriesDate if hasattr(plan, 'seriesDate') else dt.strftime('%Y%m%d')
    dcm_file.SoftwareVersions = plan.softwareVersions if hasattr(plan, 'softwareVersions') else "10.0.100.1 (Dicom Export)"
    dcm_file.SeriesNumber = plan.seriesNumber if hasattr(plan, 'seriesNumber') else "1"
    dcm_file.FrameOfReferenceUID = plan.frameOfReferenceUID if hasattr(plan, 'frameOfReferenceUID') else pydicom.uid.generate_uid()
    dcm_file.RTPlanLabel = plan.rtPlanLabel if hasattr(plan, 'rtPlanLabel') else ""
    dcm_file.RTPlanGeometry = plan.rtPlanGeometry if hasattr(plan, 'rtPlanGeometry') else "PATIENT"
    dcm_file.RTPlanName = plan.rtPlanName if hasattr(plan, 'rtPlanName') else ""
    dcm_file.RTPlanDate = plan.rtPlanDate if hasattr(plan, 'rtPlanDate') else dt.strftime('%Y%m%d')
    dcm_file.RTPlanTime = plan.rtPlanTime if hasattr(plan, 'rtPlanTime') else dt.strftime('%H%M%S.%f')
    if hasattr(plan, 'treatmentProtocols'):
        dcm_file.TreatmentProtocols = plan.treatmentProtocols
    if hasattr(plan, 'planIntent'):
        dcm_file.PlanIntent = plan.planIntent
    if hasattr(plan, 'prescriptionDescription'):
        dcm_file.PrescriptionDescription = plan.prescriptionDescription
    dcm_file.ReferringPhysicianName = plan.referringPhysicianName if hasattr(plan, 'referringPhysicianName') else ""
    dcm_file.AccessionNumber = plan.accessionNumber if hasattr(plan, 'accessionNumber') else ""
    if hasattr(plan, 'operatorsName'):
        dcm_file.OperatorsName = plan.operatorsName
    dcm_file.PositionReferenceIndicator = plan.positionReferenceIndicator if hasattr(plan, 'positionReferenceIndicator') else ""

    SeriesInstanceUID = plan.seriesInstanceUID
    if SeriesInstanceUID == "" or (SeriesInstanceUID is None):
        SeriesInstanceUID = pydicom.uid.generate_uid()

    dcm_file.SeriesInstanceUID = SeriesInstanceUID
    dcm_file.SeriesNumber = plan.seriesNumber if hasattr(plan, 'seriesNumber') else "1"

    # plan information
    dcm_file.DoseReferenceSequence = []
    if (hasattr(plan, 'doseReferenceSequence') and len(plan.doseReferenceSequence) > 0) :
        for item in plan.doseReferenceSequence:
            doseRef= pydicom.Dataset()
            doseRef.ReferencedROINumber = item.ReferencedROINumber
            doseRef.DoseReferenceNumber = item.DoseReferenceNumber
            doseRef.DoseReferenceUID = item.DoseReferenceUID
            doseRef.DoseReferenceStructureType = item.DoseReferenceStructureType
            doseRef.DoseReferenceDescription = item.DoseReferenceDescription
            doseRef.DoseReferenceType = item.DoseReferenceType
            doseRef.TargetUnderdoseVolumeFraction = item.TargetUnderdoseVolumeFraction
            dcm_file.DoseReferenceSequence.append(doseRef)
    else:
        doseRef= pydicom.Dataset()
        doseRef.ReferencedROINumber = '0'
        doseRef.DoseReferenceNumber = '1'
        doseRef.DoseReferenceUID = pydicom.uid.generate_uid()
        doseRef.DoseReferenceStructureType = 'VOLUME'
        doseRef.DoseReferenceDescription = 'OpenTPS created'
        doseRef.DoseReferenceType = 'TARGET'
        doseRef.TargetUnderdoseVolumeFraction = 0
        dcm_file.DoseReferenceSequence.append(doseRef)
    
    # Dataset => FractionGroupSequence
    dcm_file.FractionGroupSequence = []
    if hasattr(plan, 'fractionGroupSequence'): 
        for item in plan.fractionGroupSequence:
            fractionGroup = pydicom.dataset.Dataset()
            fractionGroup.FractionGroupNumber = item.FractionGroupNumber if hasattr(item, 'FractionGroupNumber') else "0"
            fractionGroup.NumberOfFractionsPlanned = plan.numberOfFractionsPlanned
            fractionGroup.NumberOfBeams = plan.NumberOfBeams if hasattr(plan, 'NumberOfBeams') else len(plan)
            fractionGroup.NumberOfBrachyApplicationSetups = item.NumberOfBrachyApplicationSetups if hasattr(item, 'NumberOfBrachyApplicationSetups') else "0"
            
            fractionGroup.ReferencedBeamSequence = []
            if hasattr(item, 'ReferencedBeamSequence') and len(item.ReferencedBeamSequence)>0:
                for refBeam in item.ReferencedBeamSequence:
                    refBeamSeq = pydicom.dataset.Dataset()
                    refBeamSeq.BeamDose = refBeam.BeamDose if hasattr(refBeamSeq, 'BeamDose') else ""
                    refBeamSeq.BeamMeterset = refBeam.BeamMeterset if hasattr(refBeamSeq, 'BeamMeterset') else ""
                    if (hasattr(refBeamSeq, 'BeamDosePointDepth')):
                        refBeamSeq.BeamDosePointDepth = refBeam.BeamDosePointDepth
                    if hasattr(refBeamSeq, 'BeamDosePointSSD'):
                        refBeamSeq.BeamDosePointSSD = refBeam.BeamDosePointSSD
                    refBeamSeq.BeamDoseType = refBeam.BeamDoseType  if hasattr(refBeamSeq, 'BeamDoseType') else ""
                    refBeamSeq.ReferencedBeamNumber = refBeam.ReferencedBeamNumber if hasattr(refBeamSeq, 'ReferencedBeamNumber') else ""
                    fractionGroup.ReferencedBeamSequence.append(refBeamSeq)
            else:
                defaultSeq = pydicom.dataset.Dataset()
                defaultSeq.BeamDose = ""
                defaultSeq.BeamMeterset = ""
                defaultSeq.BeamDoseType = ""
                defaultSeq.ReferencedBeamNumber = ""
                fractionGroup.ReferencedBeamSequence.append(defaultSeq)

            fractionGroup.ReferencedDoseReferenceSequence = []
            if hasattr(item, 'ReferencedDoseReferenceSequence') and len(item.ReferencedDoseReferenceSequence)>0:
                for refDoseRef in item.ReferencedDoseReferenceSequence:
                    rdf = pydicom.dataset.Dataset()
                    rdf.ReferencedDoseReferenceNumber = refDoseRef.ReferencedDoseReferenceNumber
                    fractionGroup.ReferencedDoseReferenceSequence.append(rdf)
            else:
                rdf = pydicom.dataset.Dataset()
                rdf.ReferencedDoseReferenceNumber = 0
                fractionGroup.ReferencedDoseReferenceSequence.append(rdf)
            
            dcm_file.FractionGroupSequence.append(fractionGroup)
        
    # Dataset => PatientSetupSequence
    dcm_file.PatientSetupSequence = []
    if hasattr(plan, 'patientSetupSequence') and len(plan.patientSetupSequence)>0:
        for ps in plan.patientSetupSequence:
            patientSetup = pydicom.dataset.Dataset()
            patientSetup.PatientPosition = ps.PatientPosition
            patientSetup.PatientSetupNumber = ps.PatientSetupNumber
            if hasattr(ps, 'TableTopVerticalSetupDisplacement'):
                patientSetup.TableTopVerticalSetupDisplacement = ps.TableTopVerticalSetupDisplacement
            if hasattr(ps, 'TableTopLongitudinalSetupDisplacement'):
                patientSetup.TableTopLongitudinalSetupDisplacement = ps.TableTopLongitudinalSetupDisplacement
            if hasattr(ps, 'TableTopLateralSetupDisplacement'):
                patientSetup.TableTopLateralSetupDisplacement = ps.TableTopLateralSetupDisplacement
            dcm_file.PatientSetupSequence.append(patientSetup)
    else:
        patientSetup = pydicom.dataset.Dataset()
        patientSetup.PatientPosition = ""
        patientSetup.PatientSetupNumber = 0
        dcm_file.PatientSetupSequence.append(patientSetup)
    
    # Dataset => IonBeamSequence
    dcm_file.IonBeamSequence = []
    if len(plan.beams)>0:
        dcm_file.FractionGroupSequence = []
        fg = pydicom.dataset.Dataset()
        fg.FractionGroupNumber = "0"
        fg.NumberOfFractionsPlanned = plan.numberOfFractionsPlanned
        fg.NumberOfBeams = len(plan)
        fg.NumberOfBrachyApplicationSetups = "0"
        fg.ReferencedBeamSequence = []
        dcm_file.FractionGroupSequence.append(fg)
        
        for (beamNumber,beam) in enumerate(plan):
            rbm = pydicom.dataset.Dataset()
            rbm.ReferencedBeamNumber = beamNumber
            rbm.BeamMeterset = beam[0].scalingFactor * floatToDS(plan.beamCumulativeMetersetWeight[beamNumber])
            fg.ReferencedBeamSequence.append(rbm)
            
            bm = pydicom.dataset.Dataset()
            bm.TreatmentMachineName = plan.treatmentMachineName
            bm.PrimaryDosimeterUnit = 'MU'
            bm.BeamNumber = beamNumber
            bm.BeamName = beam.name
            bm.BeamDescription = ''
            bm.BeamType = 'STATIC'
            bm.RadiationType = plan.radiationType.upper()
            bm.TreatmentDeliveryType = 'TREATMENT'
            bm.NumberOfWedges = '0'
            bm.NumberOfCompensators = '0'
            bm.NumberOfBoli = '0'
            bm.NumberOfBlocks = '0'
            bm.NumberOfControlPoints = len(beam)
            bm.ScanMode = "MODULATED"
            bm.VirtualSourceAxisDistances = arrayToDS([0,0])
            bm.FinalCumulativeMetersetWeight = floatToDS(plan.beamCumulativeMetersetWeight[beamNumber])
            
            bm.NumberOfRangeShifters = len(beam.rangeShifter) if not (beam.rangeShifter is None) else 0
            if bm.NumberOfRangeShifters>0:
                bm.RangeShifterSequence = []
                for (rsNumber, rangeShifter) in enumerate(beam.rangeShifter):
                    rs = pydicom.dataset.Dataset()
                    rs.RangeShifterNumber = rsNumber
                    rs.RangeShifterID = rangeShifter.ID
                    rs.RangeShifterType = rangeShifter.type.upper()
                    bm.RangeShifterSequence.append(rs)
            bm.NumberOfLateralSpreadingDevices = "0"         
            bm.NumberOfRangeModulators = "0"
            bm.PatientSupportType = "TABLE"
            
            bm.IonControlPointSequence = []
            for (layerNumber, layer) in enumerate(beam):
                ctrlpt = pydicom.dataset.Dataset()
                ctrlpt.ControlPointIndex = layerNumber
                ctrlpt.NominalBeamEnergy = layer.nominalEnergy
                ctrlpt.NumberOfPaintings = layer.numberOfPaintings
                ctrlpt.CumulativeMetersetWeight = ""
                ctrlpt.ScanSpotTuneID = "0"
                ctrlpt.ScanSpotPositionMap = arrayToDS(np.array(list(layer.spotXY)).flatten().tolist())
                ctrlpt.ScanSpotMetersetWeights = arrayToDS(layer.spotMUs.tolist())
                ctrlpt.NumberOfScanSpotPositions = layer.numberOfSpots
                if layerNumber==0:
                    ctrlpt.GantryAngle = beam.gantryAngle
                    ctrlpt.GantryRotationDirection = "NONE"
                    ctrlpt.BeamLimitingDeviceAngle = "0"
                    ctrlpt.BeamLimitingDeviceRotationDirection = "NONE"
                    ctrlpt.PatientSupportAngle = beam.couchAngle
                    ctrlpt.TableTopVerticalPosition = "0"
                    ctrlpt.TableTopLongitudinalPosition = "0"
                    ctrlpt.TableTopLateralPosition = "0"
                    ctrlpt.IsocenterPosition = arrayToDS(beam.isocenterPosition)
                    ctrlpt.SnoutPosition = 0
                    ctrlpt.RangeShifterSettingsSequence = []
                    rss = pydicom.dataset.Dataset()
                    rss.RangeShifterSetting = layer.rangeShifterSettings.rangeShifterSetting
                    rss.IsocenterToRangeShifterDistance = layer.rangeShifterSettings.isocenterToRangeShifterDistance
                    if not (layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness is None):
                        rss.RangeShifterWaterEquivalentThickness = layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness
                    rss.ReferencedRangeShifterNumber = '0'
                    ctrlpt.RangeShifterSettingsSequence.append(rss)
                bm.IonControlPointSequence.append(ctrlpt)
                    
            dcm_file.IonBeamSequence.append(bm)  
            
    if hasattr(plan, 'ionBeamSequence') and len(plan.ionBeamSequence)>0:
        for beamNumber, beam in enumerate(plan.ionBeamSequence):
            referencedBeam = pydicom.dataset.Dataset()
            # referencedBeam.BeamMeterset = floatToDS(beam.meterset)
            referencedBeam.Manufacturer = beam.Manufacturer if hasattr(beam, "Manufacturer") else ""
            referencedBeam.TreatmentMachineName = beam.TreatmentMachineName if hasattr(beam, "TreatmentMachineName") else ""
            referencedBeam.PrimaryDosimeterUnit = beam.PrimaryDosimeterUnit if hasattr(beam, "PrimaryDosimeterUnit") else "MU"
            referencedBeam.BeamNumber = beam.BeamNumber if hasattr(beam, "BeamNumber") else str(beamNumber)
            referencedBeam.BeamName = beam.BeamName if hasattr(beam, "BeamName") else ""
            referencedBeam.BeamDescription = beam.BeamDescription if hasattr(beam, "BeamDescription") else ""
            referencedBeam.BeamType = beam.BeamType if hasattr(beam, "BeamType") else "STATIC"
            referencedBeam.RadiationType = plan.radiationType.upper() if hasattr(plan, "radiationType") else ""
            referencedBeam.TreatmentDeliveryType = beam.TreatmentDeliveryType if hasattr(beam, "TreatmentDeliveryType") else "TREATMENT"
            referencedBeam.NumberOfWedges = beam.NumberOfWedges if hasattr(beam, "NumberOfWedges") else "0"
            referencedBeam.NumberOfCompensators = beam.NumberOfCompensators if hasattr(beam, "NumberOfCompensators") else "0"
            referencedBeam.NumberOfBoli = beam.NumberOfBoli if hasattr(beam, "NumberOfBoli") else "0"
            referencedBeam.NumberOfBlocks = beam.NumberOfBlocks if hasattr(beam, "NumberOfBlocks") else "0"
            referencedBeam.FinalCumulativeMetersetWeight = beam.FinalCumulativeMetersetWeight if hasattr(beam, "FinalCumulativeMetersetWeight") else floatToDS(plan.beamCumulativeMetersetWeight[beamNumber])
            referencedBeam.NumberOfControlPoints = beam.NumberOfControlPoints if hasattr(beam, "NumberOfControlPoints") else len(beam)
            referencedBeam.ScanMode = beam.ScanMode if hasattr(beam, "ScanMode") else "MODULATED"
            referencedBeam.VirtualSourceAxisDistances = beam.VirtualSourceAxisDistances if hasattr(beam,"VirtualSourceAxisDistances") else arrayToDS([0,0])
            # Snout Sequence
            referencedBeam.SnoutSequence = []
            if hasattr(beam, 'SnoutSequence') and len(beam.SnoutSequence) > 0:
                for item in beam.SnoutSequence:
                    snouts = pydicom.dataset.Dataset()
                    snouts.SnoutID = item.SnoutID
                    referencedBeam.SnoutSequence.append(snouts)
            else:
                snouts = pydicom.dataset.Dataset()
                snouts.SnoutID = ""
                referencedBeam.SnoutSequence.append(snouts)
                
            referencedBeam.NumberOfRangeShifters = beam.NumberOfRangeShifters if hasattr(beam, 'NumberOfRangeShifters') else ""
            referencedBeam.RangeShifterSequence = []
            if hasattr(beam, 'RangeShifterSequence') and len(beam.RangeShifterSequence) > 0:     
                for item in beam.RangeShifterSequence:
                    rsSeq = pydicom.dataset.Dataset()
                    rsSeq.RangeShifterNumber = item.RangeShifterNumber if hasattr(beam, 'RangeShifterNumber') else "0"
                    rsSeq.RangeShifterID = item.RangeShifterID if hasattr(beam, 'RangeShifterID') else ""
                    rsSeq.RangeShifterType = item.RangeShifterType if hasattr(beam, 'RangeShifterType') else "BINARY"
                    referencedBeam.RangeShifterSequence.append(rsSeq)
            else:
                rsSeq = pydicom.dataset.Dataset()
                rsSeq.RangeShifterNumber = "0"
                rsSeq.RangeShifterID = ""
                rsSeq.RangeShifterType = "BINARY"
                referencedBeam.RangeShifterSequence.append(rsSeq)
            
            referencedBeam.NumberOfLateralSpreadingDevices = beam.NumberOfLateralSpreadingDevices if hasattr(beam, 'NumberOfLateralSpreadingDevices') else "0"             
            referencedBeam.NumberOfRangeModulators = beam.NumberOfRangeModulators if hasattr(beam, 'NumberOfRangeModulators') else "0"
            referencedBeam.PatientSupportType = beam.PatientSupportType if hasattr(beam, 'PatientSupportType') else "TABLE"
            referencedBeam.PatientSupportID = beam.PatientSupportID if hasattr(beam, 'PatientSupportID') else "TABLE"
            
            referencedBeam.IonControlPointSequence = []
            if hasattr(beam, 'IonControlPointSequence') and len(beam.IonControlPointSequence)>0:
                for ioncContorItem in beam.IonControlPointSequence:
                    ionCps = pydicom.dataset.Dataset()
                    ionCps.NominalBeamEnergyUnit = ioncContorItem.NominalBeamEnergyUnit if hasattr(ioncContorItem, 'NominalBeamEnergyUnit') else ""
                    ionCps.ControlPointIndex = ioncContorItem.ControlPointIndex if hasattr(ioncContorItem, 'ControlPointIndex') else ""
                    ionCps.NominalBeamEnergy = floatToDS(ioncContorItem.NominalBeamEnergy) if hasattr(ioncContorItem, 'NominalBeamEnergy') else ""
                    if hasattr(ioncContorItem, 'GantryAngle'): 
                        ionCps.GantryAngle = ioncContorItem.GantryAngle
                    if hasattr(ioncContorItem, 'GantryRotationDirection'):
                        ionCps.GantryRotationDirection = ioncContorItem.GantryRotationDirection
                    if hasattr(ioncContorItem, 'BeamLimitingDeviceAngle'):
                        ionCps.BeamLimitingDeviceAngle = ioncContorItem.BeamLimitingDeviceAngle
                    if hasattr(ioncContorItem, 'BeamLimitingDeviceRotationDirection'):
                        ionCps.BeamLimitingDeviceRotationDirection = ioncContorItem.BeamLimitingDeviceRotationDirection
                    if hasattr(ioncContorItem, 'PatientSupportAngle'):
                        ionCps.PatientSupportAngle = ioncContorItem.PatientSupportAngle
                    if hasattr(ioncContorItem, 'PatientSupportRotationDirection'):
                        ionCps.PatientSupportRotationDirection = ioncContorItem.PatientSupportRotationDirection
                    if hasattr(ioncContorItem, 'TableTopVerticalPosition'):
                        ionCps.TableTopVerticalPosition = ioncContorItem.TableTopVerticalPosition
                    if hasattr(ioncContorItem, 'TableTopLongitudinalPosition'):
                        ionCps.TableTopLongitudinalPosition = ioncContorItem.TableTopLongitudinalPosition
                    if hasattr(ioncContorItem, 'TableTopLateralPosition'):
                        ionCps.TableTopLateralPosition = ioncContorItem.TableTopLateralPosition
                    if hasattr(ioncContorItem, 'IsocenterPosition'):
                        ionCps.IsocenterPosition = ioncContorItem.IsocenterPosition
                    if hasattr(ioncContorItem, 'CumulativeMetersetWeight'):
                        ionCps.CumulativeMetersetWeight = ioncContorItem.CumulativeMetersetWeight
                    if hasattr(ioncContorItem, 'TableTopPitchAngle'):
                        ionCps.TableTopPitchAngle = ioncContorItem.TableTopPitchAngle
                    if hasattr(ioncContorItem, 'TableTopPitchRotationDirection'):
                        ionCps.TableTopPitchRotationDirection = ioncContorItem.TableTopPitchRotationDirection
                    if hasattr(ioncContorItem, 'TableTopRollAngle'):
                        ionCps.TableTopRollAngle = ioncContorItem.TableTopRollAngle
                    if hasattr(ioncContorItem, 'TableTopRollRotationDirection'):
                        ionCps.TableTopRollRotationDirection = ioncContorItem.TableTopRollRotationDirection
                    if hasattr(ioncContorItem, 'GantryPitchAngle'):    
                        ionCps.GantryPitchAngle = ioncContorItem.GantryPitchAngle
                    if hasattr(ioncContorItem, 'GantryPitchRotationDirection'):
                        ionCps.GantryPitchRotationDirection = ioncContorItem.GantryPitchRotationDirection
                    if hasattr(ioncContorItem, 'SnoutPosition'):   
                        ionCps.SnoutPosition = floatToDS(ioncContorItem.SnoutPosition)
                    ionCps.RangeShifterSettingsSequence = []
                    if hasattr(ioncContorItem, 'RangeShifterSettingsSequence') and len(ioncContorItem.RangeShifterSettingsSequence) > 0:
                        for rItem in ioncContorItem.RangeShifterSettingsSequence:
                            ionCpsRange = pydicom.dataset.Dataset()
                            ionCpsRange.RangeShifterSetting = rItem.RangeShifterSetting
                            ionCpsRange.IsocenterToRangeShifterDistance = rItem.IsocenterToRangeShifterDistance
                            ionCpsRange.ReferencedRangeShifterNumber = rItem.ReferencedRangeShifterNumber
                            ionCps.RangeShifterSettingsSequence.append(ionCpsRange)
                    else:
                        defaultIonCpsRange = pydicom.dataset.Dataset()
                        defaultIonCpsRange.RangeShifterSetting = "IN"
                        defaultIonCpsRange.IsocenterToRangeShifterDistance = 0.0
                        defaultIonCpsRange.ReferencedRangeShifterNumber = "0"
                        ionCps.RangeShifterSettingsSequence.append(defaultIonCpsRange)
                    
                    ionCps.ScanSpotTuneID = ioncContorItem.ScanSpotTuneID if hasattr(ioncContorItem, "ScanSpotTuneID") else ""
                    ionCps.NumberOfScanSpotPositions = ioncContorItem.NumberOfScanSpotPositions if hasattr(ioncContorItem, "NumberOfScanSpotPositions") else ""
                    ionCps.ScanSpotPositionMap = ioncContorItem.ScanSpotPositionMap if hasattr(ioncContorItem, "ScanSpotPositionMap") else ""
                    ionCps.ScanSpotMetersetWeights = ioncContorItem.ScanSpotMetersetWeights if hasattr(ioncContorItem, "ScanSpotMetersetWeights") else ""
                    ionCps.ScanningSpotSize = ioncContorItem.ScanningSpotSize if hasattr(ioncContorItem, "ScanningSpotSize") else ""
                    ionCps.NumberOfPaintings = ioncContorItem.NumberOfPaintings if hasattr(ioncContorItem, "NumberOfPaintings") else 1
                    ionCps.ReferencedDoseReferenceSequence = []
                    if hasattr(ioncContorItem, 'ReferencedDoseReferenceSequence') and len(ioncContorItem.ReferencedDoseReferenceSequence)>0:
                        for refItem in ioncContorItem.ReferencedDoseReferenceSequence:
                            refDoseR = pydicom.dataset.Dataset()
                            refDoseR.CumulativeDoseReferenceCoefficient = refItem.CumulativeDoseReferenceCoefficient
                            refDoseR.ReferencedDoseReferenceNumber = refItem.ReferencedDoseReferenceNumber
                            ionCps.ReferencedDoseReferenceSequence.append(refDoseR)
                    else:
                        defaultRefDoseR =  pydicom.dataset.Dataset()
                        defaultRefDoseR.CumulativeDoseReferenceCoefficient = ""
                        defaultRefDoseR.ReferencedDoseReferenceNumber = "0"
                        defaultRefDoseR.PrivateCreator = ""
                        ionCps.ReferencedDoseReferenceSequence.append(defaultRefDoseR)
                    referencedBeam.IonControlPointSequence.append(ionCps)
            else:
                ionCps = pydicom.dataset.Dataset()
                ionCps.NominalBeamEnergyUnit = ""
                ionCps.ControlPointIndex = ""
                ionCps.NominalBeamEnergy = ""
                ionCps.BeamLimitingDeviceRotationDirection = "None"
                ionCps.PatientSupportAngle = "0"
                ionCps.PatientSupportRotationDirection = "None"
                ionCps.TableTopVerticalPosition = ""
                ionCps.TableTopLongitudinalPosition = ""
                ionCps.TableTopLateralPosition = ""
                ionCps.CumulativeMetersetWeight = ""
                ionCps.TableTopPitchAngle = 0.0
                ionCps.TableTopPitchRotationDirection = "None"
                ionCps.TableTopRollAngle = 0.0
                ionCps.TableTopRollRotationDirection = "None"
                ionCps.GantryPitchAngle = 0.0
                ionCps.GantryPitchRotationDirection = "None"
                ionCps.SnoutPosition = ""
                ionCps.RangeShifterSettingsSequence = []        
                defaultIonCpsRange = pydicom.dataset.Dataset()
                defaultIonCpsRange.RangeShifterSetting = "OUT"
                defaultIonCpsRange.IsocenterToRangeShifterDistance = 0.0
                defaultIonCpsRange.ReferencedRangeShifterNumber = '0'
                ionCps.RangeShifterSettingsSequence.append(defaultIonCpsRange)
                ionCps.ScanSpotTuneID = ""
                ionCps.NumberOfScanSpotPositions = ""
                ionCps.ScanSpotPositionMap = ""
                ionCps.ScanSpotMetersetWeights = ""
                ionCps.ScanningSpotSize = ""
                ionCps.NumberOfPaintings = 1
                ionCps.ReferencedDoseReferenceSequence = []
                defaultRefDoseR =  pydicom.dataset.Dataset()
                defaultRefDoseR.CumulativeDoseReferenceCoefficient = ""
                defaultRefDoseR.ReferencedDoseReferenceNumber = "0"
                defaultRefDoseR.PrivateCreator = ""
                ionCps.ReferencedDoseReferenceSequence.append(defaultRefDoseR)
                
                referencedBeam.IonControlPointSequence.append(ionCps)
                   
            referencedBeam.PrivateCreator = beam.PrivateCreator if hasattr(beam, 'PrivateCreator') else ""
            referencedBeam.ReferencedPatientSetupNumber = beam.ReferencedPatientSetupNumber if hasattr(beam, 'ReferencedPatientSetupNumber') else ""
            dcm_file.IonBeamSequence.append(referencedBeam)
    # else:
    #     referencedBeam = pydicom.dataset.Dataset()
    #     # referencedBeam.BeamMeterset = floatToDS(beam.meterset)
    #     referencedBeam.Manufacturer = ""
    #     referencedBeam.TreatmentMachineName = ""
    #     referencedBeam.PrimaryDosimeterUnit = ""
    #     referencedBeam.BeamNumber = ""
    #     referencedBeam.BeamDescription = ""
    #     referencedBeam.BeamType = "STATIC"
    #     referencedBeam.RadiationType = ""
    #     referencedBeam.TreatmentDeliveryType = ""
    #     referencedBeam.NumberOfWedges = ""
    #     referencedBeam.NumberOfCompensators = ""
    #     referencedBeam.NumberOfBoli = ""
    #     referencedBeam.NumberOfBlocks = ""
    #     referencedBeam.FinalCumulativeMetersetWeight = ""
    #     referencedBeam.NumberOfControlPoints = ""
    #     referencedBeam.ScanMode = ""
    #     referencedBeam.VirtualSourceAxisDistances = ""
    #     # Snout Sequence
    #     referencedBeam.SnoutSequence = []
    #     snouts = pydicom.dataset.Dataset()
    #     snouts.SnoutID = ""
    #     referencedBeam.SnoutSequence.append(snouts) 
    #     referencedBeam.NumberOfRangeShifters = "0"
        
    #     referencedBeam.RangeShifterSequence = []
    #     rsSeq = pydicom.dataset.Dataset()
    #     rsSeq.RangeShifterNumber = "0"
    #     rsSeq.RangeShifterID = ""
    #     rsSeq.RangeShifterType = "BINARY"
    #     referencedBeam.RangeShifterSequence.append(rsSeq)
    #     referencedBeam.NumberOfLateralSpreadingDevices = "0"             
    #     referencedBeam.NumberOfRangeModulators = "0"
    #     referencedBeam.PatientSupportType = "TABLE"
    #     referencedBeam.PatientSupportID = "TABLE"
            
    #     referencedBeam.IonControlPointSequence = []
    #     ionCps = pydicom.dataset.Dataset()
    #     ionCps.NominalBeamEnergyUnit = ""
    #     ionCps.ControlPointIndex = "0"
    #     ionCps.NominalBeamEnergy = ""
    #     ionCps.GantryAngle = ""
    #     ionCps.BeamLimitingDeviceRotationDirection = "None"
    #     ionCps.PatientSupportAngle = ""
    #     ionCps.PatientSupportRotationDirection = ""
    #     ionCps.TableTopVerticalPosition = ""
    #     ionCps.TableTopLongitudinalPosition = ""
    #     ionCps.TableTopLateralPosition = ""
    #     ionCps.IsocenterPosition = ""
    #     ionCps.CumulativeMetersetWeight = ""
    #     ionCps.TableTopPitchAngle = 0.0
    #     ionCps.TableTopPitchRotationDirection = "None"
    #     ionCps.TableTopRollAngle = 0.0
    #     ionCps.TableTopRollRotationDirection = "None"
    #     ionCps.GantryPitchAngle = 0.0
    #     ionCps.GantryPitchRotationDirection = "None"
    #     ionCps.SnoutPosition = ""
    #     ionCps.RangeShifterSettingsSequence = []
    #     ionCpsRange = pydicom.dataset.Dataset()
    #     ionCpsRange.RangeShifterSetting = "IN"
    #     ionCpsRange.IsocenterToRangeShifterDistance = 0.0
    #     ionCpsRange.ReferencedRangeShifterNumber = "0"
    #     ionCps.RangeShifterSettingsSequence.append(ionCpsRange)
        
    #     ionCps.ScanSpotTuneID = ""
    #     ionCps.NumberOfScanSpotPositions = ""
    #     ionCps.ScanSpotPositionMap = ""
    #     ionCps.ScanSpotMetersetWeights = ""
    #     ionCps.ScanningSpotSize = ""
    #     ionCps.NumberOfPaintings = ""
    #     ionCps.ReferencedDoseReferenceSequence = []
    #     defaultRefDoseR =  pydicom.dataset.Dataset()
    #     defaultRefDoseR.CumulativeDoseReferenceCoefficient = ""
    #     defaultRefDoseR.ReferencedDoseReferenceNumber = "0"
    #     ionCps.ReferencedDoseReferenceSequence.append(defaultRefDoseR)
    #     referencedBeam.IonControlPointSequence.append(ionCps)
        
    #     referencedBeam.PrivateCreator = ""
    #     referencedBeam.ReferencedPatientSetupNumber = ""
    #     dcm_file.IonBeamSequence.append(referencedBeam)
        
            
    dcm_file.ReferencedStructureSetSequence = []
    if (hasattr(plan, 'referencedStructureSetSequence') and len(plan.referencedStructureSetSequence)>0):
        for item in plan.referencedStructureSetSequence:
            refStructSeq = pydicom.Dataset()
            refStructSeq.ReferencedSOPClassUID = item.ReferencedSOPClassUID
            refStructSeq.ReferencedSOPInstanceUID = item.ReferencedSOPInstanceUID
            dcm_file.ReferencedStructureSetSequence.append(refStructSeq)
    elif dcm_file.RTPlanGeometry=='PATIENT' and not struct is None:
        refStructSeq = pydicom.Dataset()
        refStructSeq.ReferencedSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'
        refStructSeq.ReferencedSOPInstanceUID = struct.sopInstanceUID
        dcm_file.ReferencedStructureSetSequence.append(refStructSeq)        
    elif dcm_file.RTPlanGeometry=='PATIENT':
        refStructSeq = pydicom.Dataset()
        refStructSeq.ReferencedSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'
        refStructSeq.ReferencedSOPInstanceUID = pydicom.uid.generate_uid()
        dcm_file.ReferencedStructureSetSequence.append(refStructSeq)
    
    dcm_file.ApprovalStatus = plan.approvalStatus if hasattr(plan, 'approvalStatus') else ""
    dcm_file.PrivateCreator = plan.privateCreator if hasattr(plan, 'privateCreator') else "OpenTPS"
    
    # save dicom file
    if outputFilename:
        planFilename = ''.join(letter for letter in outputFilename if letter.isalnum())
        filename = planFilename + '.dcm'
    elif hasattr(dcm_file, 'SOPInstanceUID'):
        filename = f'RP{dcm_file.SOPInstanceUID}.dcm'
    else : 
        filename = f'RP.dcm'

    file_root, file_ext = os.path.splitext(filename)
    newFilename = filename
    counter = 1
    while os.path.exists(os.path.join(outputFolder, newFilename)):
        newFilename = f"{file_root}_{counter}{file_ext}"
        counter += 1

    dcm_file.save_as(os.path.join(outputFolder, newFilename))
    logger.info("Export dicom TREATMENT PLAN: " + newFilename + ' in ' + outputFolder)
    
    

def readDicomVectorField(dcmFile):
    """
    Read a Dicom vector field file and generate a vector field object.

    Parameters
    ----------
    dcmFile: str
        Path of the Dicom vector field file.

    Returns
    -------
    field: vectorField3D object
        The function returns the imported vector field
    """

    dcm = pydicom.dcmread(dcmFile)

    # import vector field
    dcmSeq = dcm.DeformableRegistrationSequence[0]
    dcmField = dcmSeq.DeformableRegistrationGridSequence[0]

    imagePositionPatient = dcmField.ImagePositionPatient
    pixelSpacing = dcmField.GridResolution

    rawField = np.frombuffer(dcmField.VectorGridData, dtype=np.float32)
    rawField = rawField.reshape(
        (3, dcmField.GridDimensions[0], dcmField.GridDimensions[1], dcmField.GridDimensions[2]),
        order='F').transpose(1, 2, 3, 0)
    fieldData = rawField.copy()

    # collect patient information
    if hasattr(dcm, 'PatientID'):
        birth = dcm.PatientBirthDate if hasattr(dcm, 'PatientBirthDate') else ""
        sex = dcm.PatientSex if hasattr(dcm, 'PatientSex') else None
        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=birth,
                      sex=sex)
    else:
        patient = Patient()

    # collect other information
    if (hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""):
        fieldName = dcm.SeriesDescription
    else:
        fieldName = dcm.SeriesInstanceUID

    # generate dose image object
    field = VectorField3D(imageArray=fieldData, name=fieldName, origin=imagePositionPatient,
                          spacing=pixelSpacing)
    field.patient = patient

    return field




def readDicomRigidTransform(dcmFile):
    """
    Read a Dicom registration file and generate a 3D transform object.

    Parameters
    ----------
    dcmFile: str
        Path of the Dicom registration file.

    Returns
    -------
    transform: Transform3D object
        The function returns the imported transform
    """

    dcm = pydicom.dcmread(dcmFile)

    for i in range(len(dcm.RegistrationSequence)):
        if hasattr(dcm.RegistrationSequence[i], 'MatrixRegistrationSequence'):
            reg_matrix = dcm.RegistrationSequence[i].MatrixRegistrationSequence[0].MatrixSequence[0].FrameOfReferenceTransformationMatrix

    tformMatrix = np.array(reg_matrix).reshape(4, 4)
    tformMatrix_1 = np.linalg.inv(tformMatrix) # get inverse
    transform3D = Transform3D()
    transform3D.setCenter('dicomOrigin')
    transform3D.setMatrix4x4(tformMatrix_1)

    return transform3D
