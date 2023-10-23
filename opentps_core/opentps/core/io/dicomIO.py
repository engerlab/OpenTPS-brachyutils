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

def floatToDS(v):
    return pydicom.valuerep.DSfloat(v,auto_format=True)

def arrayToDS(ls):
    return list(map(floatToDS, ls))


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
        brth = dcm.PatientBirthDate if hasattr(dcm, 'PatientBirthDate') else None
        sex = dcm.PatientSex if hasattr(dcm, 'PatientSex') else None

        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=brth, sex=sex)
    else:
        patient = Patient()

    # generate CT image object
    FrameOfReferenceUID = dcm.FrameOfReferenceUID if hasattr(dcm, 'FrameOfReferenceUID') else None
    image = CTImage(imageArray=imageData, name=imgName, origin=imagePositionPatient,
                    spacing=pixelSpacing, seriesInstanceUID=dcm.SeriesInstanceUID,
                    frameOfReferenceUID=FrameOfReferenceUID, sliceLocation=sliceLocation,
                    sopInstanceUIDs=sopInstanceUIDs)
    image.patient = patient
    image.patientPosition = dcm.PatientPosition if hasattr(dcm, 'PatientPosition') else None
    image.seriesNumber = dcm.SeriesNumber if hasattr(dcm, 'SeriesNumber') else None
    image.photometricInterpretation = dcm.PhotometricInterpretation if hasattr(dcm, 'PhotometricInterpretation') else None
    image.sopInstanceUIDs = sopInstanceUIDs
    image.sopClassUID = dcm.SOPClassUID if hasattr(dcm, 'SOPClassUID') else ''
    image.softwareVersions = dcm.SoftwareVersions if hasattr(dcm, 'SoftwareVersions') else "None"
    image.studyDate = dcm.StudyDate if hasattr(dcm, 'StudyDate') else dt.strftime('%Y%m%d')    
    image.seriesNumber = dcm.SeriesNumber if(hasattr(dcm, 'SeriesNumber')) else ''
    image.fileMetaInformationGroupLength = dcm.file_meta.FileMetaInformationGroupLength if hasattr(dcm.file_meta, 'FileMetaInformationGroupLength') else 0
    image.mediaStorageSOPClassUID = dcm.file_meta.MediaStorageSOPClassUID if hasattr(dcm.file_meta, 'MediaStorageSOPClassUID') else "None"
    image.implementationClassUID = dcm.file_meta.ImplementationClassUID if hasattr(dcm.file_meta, 'ImplementationClassUID') else ""
    image.studyID = dcm.StudyID if hasattr(dcm, 'StudyID') else ""
    image.studyTime = dcm.StudyTime if hasattr(dcm, 'StudyTime') else dt.strftime('%H%M%S.%f')
    image.implementationVersionName = dcm.file_meta.ImplementationVersionName if hasattr(dcm.file_meta, 'ImplementationVersionName') else "None"
    image.contentDate = dcm.ContentDate if hasattr(dcm, 'ContentDate') else dt.strftime('%Y%m%d')
    image.frameOfReferenceUID = dcm.FrameOfReferenceUID if hasattr(dcm, 'FrameOfReferenceUID') else None
    image.imageOrientationPatient = dcm.ImageOrientationPatient if hasattr(dcm, 'imageOrientationPatient') else ""
    image.seriesDate = dcm.SeriesDate if hasattr(dcm, 'SeriesDate') else dt.strftime('%Y%m%d')
    image.studyInstanceUID = dcm.StudyInstanceUID
    image.bitsAllocated = dcm.BitsAllocated if hasattr(dcm, 'BitsAllocated') else 0
    image.modality = dcm.Modality if hasattr(dcm, 'Modality') else ""
    image.bitsStored = dcm.BitsStored if hasattr(dcm, 'BitsStored') else 0
    image.highBit = dcm.HighBit if hasattr(dcm, 'HighBit') else 0
    image.approvalStatus = dcm.ApprovalStatus if hasattr(dcm, 'ApprovalStatus') else 'UNAPPROVED'

    return image


def writeDicomCT(ct: CTImage, outputFolderPath:str):
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
    folder_name = os.path.split(outputFolderPath)[-1]
    outdata = ct.imageArray.copy()
    dt = datetime.datetime.now()
    
    # meta data
    meta = pydicom.dataset.FileMetaDataset()
    meta.MediaStorageSOPClassUID = ct.mediaStorageSOPClassUID # CT Image Storage
    meta.ImplementationClassUID = ct.implementationClassUID
    meta.FileMetaInformationGroupLength = ct.fileMetaInformationGroupLength
    meta.ImplementationVersionName = ct.implementationVersionName

    # dicom dataset
    dcm_file = pydicom.dataset.FileDataset(outputFolderPath, {}, file_meta=meta, preamble=b"\0" * 128)
    dcm_file.SOPClassUID = ct.sopClassUID
    dcm_file.ImageType = ['DERIVED', 'SECONDARY', 'AXIAL']
    # dcm_file.SpecificCharacterSet =
    # dcm_file.AccessionNumber =
    dcm_file.SoftwareVersions = ct.softwareVersions

    # patient information
    patient = ct.patient
    if not (patient is None):
        dcm_file.PatientName = "exported_" + patient.name
        dcm_file.PatientID = patient.id
        dcm_file.PatientBirthDate = patient.birthDate
        dcm_file.PatientSex = patient.sex
    else:
        dcm_file.PatientName = 'ANONYMOUS'
        dcm_file.PatientID = 'ANONYMOUS'
        dcm_file.PatientBirthDate = '01022010'
        dcm_file.PatientSex = 'Helicopter'
    dcm_file.OtherPatientNames = 'None'
    dcm_file.PatientAge = '099Y'
    dcm_file.IssuerOfPatientID = ''

    # Study information
    dcm_file.StudyDate = ct.studyDate
    dcm_file.StudyTime = ct.studyTime
    dcm_file.SeriesTime = dt.strftime('%H%M%S.%f')
    # dcm_file.AcquisitionTime = '084338'
    # dcm_file.ContentTime = '160108.480'
    # dcm_file.AccessionNumber = 'D140640901'
    dcm_file.StudyID = ct.studyID
    dcm_file.StudyInstanceUID = ct.studyInstanceUID+'1'


    # content information
    dcm_file.ContentDate = dt.strftime('%Y%m%d')
    dcm_file.ContentTime = dt.strftime('%H%M%S.%f')
    dcm_file.InstanceCreationDate = dt.strftime('%Y%m%d')
    dcm_file.InstanceCreationTime = dt.strftime('%H%M%S.%f')
    dcm_file.Modality = ct.modality
    dcm_file.Manufacturer = 'OpenTPS'
    # dcm_file.InstitutionName = ''
    # dcm_file.ReferringPhysicianName = ''
    # dcm_file.StationName = ''
    dcm_file.StudyDescription = 'OpenTPS simulation'
    dcm_file.SeriesDescription = 'OpenTPS created image'
    dcm_file.ManufacturerModelName = 'OpenTPS'
    # dcm_file.InstitutionalDepartmentName = 'RADIOTHERAPY'
    # dcm_file.OperatorsName = ''
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
    dcm_file.PatientPosition = ct.patientPosition
    # dcm_file.CTDIvol = 

    dcm_file.SeriesInstanceUID = ct.seriesInstanceUID
    dcm_file.SeriesNumber = ct.seriesNumber
    # dcm_file.AcquisitionNumber = '4'
    dcm_file.ImagePositionPatient = arrayToDS(ct.origin)
    dcm_file.ImageOrientationPatient = [1, 0, 0, 0, 1,
                                        0]  # HeadFirstSupine=1,0,0,0,1,0  FeetFirstSupine=-1,0,0,0,1,0  HeadFirstProne=-1,0,0,0,-1,0  FeetFirstProne=1,0,0,0,-1,0
    dcm_file.FrameOfReferenceUID = ct.frameOfReferenceUID
    # dcm_file.PositionReferenceIndicator = ''
    # dcm_file.NumberOfStudyRelatedInstances = ''
    # dcm_file.RespiratoryIntervalTime = 
    dcm_file.SamplesPerPixel = 1
    dcm_file.PhotometricInterpretation = ct.photometricInterpretation
    dcm_file.Rows = ct.gridSize[1]
    dcm_file.Columns = ct.gridSize[0]
    dcm_file.PixelSpacing = arrayToDS(ct.spacing[0:2])
    dcm_file.BitsAllocated = ct.bitsAllocated
    dcm_file.BitsStored = ct.bitsStored
    dcm_file.HighBit = ct.highBit
    dcm_file.PixelRepresentation = 1
    dcm_file.ApprovalStatus = ct.approvalStatus
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
    # dcm_file.StructureSetLabel = ''
    # dcm_file.StructureSetDate = ''
    # dcm_file.StructureSetTime = ''
    
    # transfer syntax
    dcm_file.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    dcm_file.is_little_endian = True
    dcm_file.is_implicit_VR = False

    
    # pydicom.dataset.validate_file_meta(dcm_file.file_meta, enforce_standard=True)
    for slice in range(ct.gridSize[2]):
        
        # meta data
        meta = pydicom.dataset.FileMetaDataset()
        meta.MediaStorageSOPInstanceUID = ct.sopInstanceUIDs[slice]
         
        dcm_slice = copy.deepcopy(dcm_file)
        dcm_file.SOPClassUID = ct.mediaStorageSOPClassUID
        dcm_slice.SOPInstanceUID = ct.sopInstanceUIDs[slice]
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

        # write output dicom file
        output_filename = f'{folder_name}_{slice+1:04d}.dcm'
        dcm_slice.save_as(os.path.join(outputFolderPath,output_filename))
    return dcm_file.SeriesInstanceUID
        
        
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
        brth = dcm.PatientBirthDate if hasattr(dcm, 'PatientBirthDate') else strftime('%Y%m%d')
        sex = dcm.PatientSex if hasattr(dcm, 'PatientSex') else None

        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=brth, sex=sex)
    else:
        patient = Patient()

    # generate MR image object
    FrameOfReferenceUID = dcm.FrameOfReferenceUID if hasattr(dcm, 'FrameOfReferenceUID') else ""
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
    image.studyInstanceUID = dcm.StudyInstanceUID if hasattr(dcm, 'StudyInstanceUID') else ""

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
    dt = datetime.datetime.now()
    # dcm_file.ContentDate = dt.strftime('%Y%m%d')
    # dcm_file.ContentTime = dt.strftime('%H%M%S.%f')

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

    if (type(dcm.SliceThickness) == float):
        sliceThickness = dcm.SliceThickness
    else:
        if (hasattr(dcm, 'GridFrameOffsetVector') and hasattr(dcm, 'GridFrameOffsetVector') and hasattr(dcm, 'GridFrameOffsetVector')):
            sliceThickness = (dcm.GridFrameOffsetVector[-1] - dcm.GridFrameOffsetVector[0]) / (len(dcm.GridFrameOffsetVector) - 1)
        else:
            sliceThickness = ""

    pixelSpacing = (float(dcm.PixelSpacing[1]), float(dcm.PixelSpacing[0]), sliceThickness)
    imagePositionPatient = tuple(dcm.ImagePositionPatient)

    # check image orientation
    # TODO use image angle instead
    if hasattr(dcm, 'GridFrameOffsetVector'):
        if (dcm.GridFrameOffsetVector[1] - dcm.GridFrameOffsetVector[0] < 0):
            imageData = np.flip(imageData, 2)
            
            # Note: Tuples are immutable so we cannot change their values. Our code returns an error.
            # Solution: Convert our “classes” tuple into a list. This will let us change the values in our sequence of class names
            imagePositionPatient_list = list(imagePositionPatient)
            imagePositionPatient_list[2] = imagePositionPatient[2] - imageData.shape[2] * pixelSpacing[2]
            imagePositionPatient=tuple(imagePositionPatient_list)

    # collect patient information
    if hasattr(dcm, 'PatientID'):
        brth = dcm.PatientBirthDate if hasattr(dcm, 'PatientBirthDate') else dt.strftime('%Y%m%d')
        sex = dcm.PatientSex if hasattr(dcm, 'PatientSex') else ""

        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=brth, sex=sex)
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
    image.sopInstanceUID = dcm.SOPInstanceUID
    image.implementationClassUID = dcm.file_meta.ImplementationClassUID if hasattr(dcm.file_meta, 'ImplementationClassUID') else ""
    image.fileMetaInformationGroupLength = dcm.file_meta.FileMetaInformationGroupLength if hasattr(dcm.file_meta, 'FileMetaInformationGroupLength') else 0
    image.fileMetaInformationVersion = dcm.file_meta.FileMetaInformationVersion if hasattr(dcm.file_meta, 'FileMetaInformationVersion') else ""
    image.implementationVersionName = dcm.file_meta.ImplementationVersionName if hasattr(dcm.file_meta, 'ImplementationVersionName') else ""
    image.studyID = dcm.StudyID if hasattr(dcm, 'StudyID') else ""
    image.studyDate = dcm.StudyDate if hasattr(dcm, 'StudyDate') else dt.strftime('%Y%m%d')
    image.studyTime = dcm.StudyTime if hasattr(dcm, 'StudyTime') else dt.strftime('%H%M%S.%f')
    image.seriesNumber = dcm.SeriesNumber if hasattr(dcm, 'SeriesNumber') else ""
    image.instanceNumber = dcm.InstanceNumber if hasattr(dcm, 'InstanceNumber') else "1"
    image.patientOrientation = dcm.PatientOrientation if hasattr(dcm, 'PatientOrientation') else ""
    image.doseUnits = dcm.DoseUnits if hasattr(dcm, 'DoseUnits') else ""
    image.frameOfReferenceUID = dcm.FrameOfReferenceUID if hasattr(dcm, 'FrameOfReferenceUID') else ""
    image.photometricInterpretation = dcm.PhotometricInterpretation if hasattr(dcm, 'PhotometricInterpretation') else ""
    image.transferSyntaxUID = dcm.file_meta.TransferSyntaxUID if hasattr(dcm, 'TransferSyntaxUID') else ""
    image.frameIncrementPointer = dcm.FrameIncrementPointer if hasattr(dcm, 'FrameIncrementPointer') else {}
    image.doseType = dcm.DoseType if hasattr(dcm, 'DoseType') else ""
    image.doseSummationType = dcm.DoseSummationType if hasattr(dcm, 'DoseSummationType') else ""
    image.bitsAllocated = dcm.BitsAllocated if hasattr(dcm, 'BitsAllocated') else 0
    image.highBit = dcm.HighBit if hasattr(dcm, 'HighBit') else 0
    image.specificCharacterSet = dcm.SpecificCharacterSet if hasattr(dcm, 'SpecificCharacterSet') else ""
    image.accessionNumber = dcm.AccessionNumber if hasattr(dcm, 'AccessionNumber') else ""
    image.softwareVersion = dcm.SoftwareVersion if hasattr(dcm, 'SoftwareVersion') else ""
    image.bitsStored = dcm.BitsStored if hasattr(dcm, 'BitsStored') else 0
    image.modality = dcm.Modality if hasattr(dcm, 'Modality') else ""
    image.sopClassUID = dcm.SOPClassUID if hasattr(dcm, 'SOPClassUID') else ""
    image.referencedRTPlanSequence = dcm.ReferencedRTPlanSequence if hasattr(dcm, 'ReferencedRTPlanSequence') else [] 

    return image

def writeRTDose(dose:DoseImage, outputFile):
    """
    Export the dose data as a Dicom dose file

    Parameters
    ----------
    dose: DoseImage
        The dose image object.
    outputFile:
        The output file path
    """
    
    # meta data
    meta = pydicom.dataset.FileMetaDataset()
    meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'
    meta.MediaStorageSOPInstanceUID = dose.sopInstanceUID
    
    # meta.ImplementationClassUID = '1.2.826.0.1.3680043.1.2.100.5.7.0.47' # from RayStation
    meta.ImplementationClassUID =  dose.implementationClassUID # modified
    meta.FileMetaInformationGroupLength = 0
    meta.FileMetaInformationVersion = dose.fileMetaInformationVersion
    meta.ImplementationVersionName = dose.implementationVersionName
    meta.TransferSyntaxUID = dose.transferSyntaxUID
    
    # dicom dataset
    dcm_file = pydicom.dataset.FileDataset(outputFile, {}, file_meta=meta, preamble=b"\0" * 128)
    dcm_file.SOPClassUID = dose.sopClassUID
    dcm_file.SOPInstanceUID = dose.sopInstanceUID
    dcm_file.SpecificCharacterSet = dose.specificCharacterSet
    dcm_file.AccessionNumber = dose.accessionNumber
    dcm_file.SoftwareVersion = dose.softwareVersion

    # patient information
    patient = dose.patient
    if not (patient is None):
        dcm_file.PatientName = "exported_" + patient.name
        dcm_file.PatientID = patient.id
        dcm_file.PatientBirthDate = patient.birthDate
        dcm_file.PatientSex = patient.sex

    # content information
    dt = datetime.datetime.now()
    dcm_file.ContentDate = dt.strftime('%Y%m%d')
    dcm_file.ContentTime = dt.strftime('%H%M%S.%f')
    dcm_file.InstanceCreationDate = dt.strftime('%Y%m%d')
    dcm_file.InstanceCreationTime = dt.strftime('%H%M%S.%f')
    dcm_file.Modality = dose.modality
    dcm_file.Manufacturer = 'OpenMCsquare'
    dcm_file.ManufacturerModelName = 'OpenTPS'
    dcm_file.SeriesDescription = dose.name
    
    # wei test
    dcm_file.StudyInstanceUID = dose.studyInstanceUID+'1'
    
    dcm_file.StudyID = dose.studyID
    dcm_file.StudyDate = dose.studyDate
    dcm_file.StudyTime = dose.studyTime
    dcm_file.SeriesInstanceUID = dose.seriesInstanceUID
    dcm_file.SeriesNumber = dose.seriesNumber
    dcm_file.InstanceNumber = dose.instanceNumber
    dcm_file.PatientOrientation = dose.patientOrientation
    dcm_file.DoseUnits = dose.doseUnits
    dcm_file.DoseType = dose.doseType  # or 'EFFECTIVE' for RBE dose (but RayStation exports physical dose even if 1.1 factor is already taken into account)
    dcm_file.DoseSummationType = dose.doseSummationType
    
    if dose.referenceCT is None:
        dcm_file.FrameOfReferenceUID = dose.frameOfReferenceUID
    else:
        dcm_file.FrameOfReferenceUID = dose.referenceCT.frameOfReferenceUID

    if dose.referencedRTPlanSequence is None:
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
                
    # dcm_file.ReferringPhysicianName
    # dcm_file.OperatorName

    # image information
    dcm_file.Width = dose.gridSize[0]
    dcm_file.Columns = dcm_file.Width
    dcm_file.Height = dose.gridSize[1]
    dcm_file.Rows = dcm_file.Height
    dcm_file.NumberOfFrames = dose.gridSize[2]
    dcm_file.SliceThickness = dose.spacing[2]
    dcm_file.PixelSpacing = arrayToDS(dose.spacing[0:2])    
    dcm_file.ColorType = 'grayscale'
    dcm_file.ImagePositionPatient = arrayToDS(dose.origin)
    dcm_file.ImageOrientationPatient = [1, 0, 0, 0, 1,
                                        0]  # HeadFirstSupine=1,0,0,0,1,0  FeetFirstSupine=-1,0,0,0,1,0  HeadFirstProne=-1,0,0,0,-1,0  FeetFirstProne=1,0,0,0,-1,0
    dcm_file.SamplesPerPixel = 1
    dcm_file.PhotometricInterpretation = dose.photometricInterpretation
    dcm_file.FrameIncrementPointer = dose.frameIncrementPointer
    dcm_file.GridFrameOffsetVector = list(
        np.arange(0, dose.gridSize[2] * dose.spacing[2], dose.spacing[2]))

    # transfer syntax
    dcm_file.is_little_endian = True
    dcm_file.is_implicit_VR = False

    # image data
    dcm_file.BitDepth = 16
    dcm_file.BitsAllocated = dose.bitsAllocated
    dcm_file.BitsStored = dose.bitsStored
    dcm_file.HighBit = dose.highBit
    dcm_file.PixelRepresentation = 0  # 0=unsigned, 1=signed
    dcm_file.DoseGridScaling = dose.imageArray.max() / (2 ** dcm_file.BitDepth - 1)
    dcm_file.PixelData = (dose.imageArray / dcm_file.DoseGridScaling).astype(np.uint16).transpose(2, 1, 0).tostring()
    
    # save dicom file
    print("Export dicom RTDOSE: " + outputFile)
    dcm_file.save_as(outputFile)
    
################### Dose Image #######################################################
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
        brth = dcm.PatientBirthDate if hasattr(dcm, 'PatientBirthDate') else dt.strftime('%Y%m%d')
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
        
    struct.mediaStorageSOPClassUID = dcm.file_meta.MediaStorageSOPClassUID if hasattr(dcm.file_meta, 'MediaStorageSOPClassUID') else ""        
    struct.mediaStorageSOPInstanceUID = dcm.file_meta.MediaStorageSOPInstanceUID if hasattr(dcm, 'MediaStorageSOPInstanceUID') else ""    
    struct.transferSyntaxUID = dcm.file_meta.TransferSyntaxUID if hasattr(dcm.file_meta, 'TransferSyntaxUID') else ""
    struct.implementationClassUID = dcm.file_meta.ImplementationClassUID if hasattr(dcm.file_meta, 'ImplementationClassUID') else ""
    struct.implementationVersionName = dcm.file_meta.ImplementationVersionName if hasattr(dcm, 'ImplementationVersionName') else ""
    
    # Data set
    struct.specificCharacterSet = dcm.SpecificCharacterSet if hasattr(dcm, 'SpecificCharacterSet') else ""
    struct.sopInstanceUID = dcm.SOPInstanceUID if hasattr(dcm, 'SOPInstanceUID') else ""
    struct.studyDate = dcm.StudyDate if hasattr(dcm, 'StudyDate') else dt.strftime('%Y%m%d')
    struct.seriesDate = dcm.SeriesDate if hasattr(dcm, 'SeriesDate') else dt.strftime('%Y%m%d')
    struct.studyTime = dcm.StudyTime if hasattr(dcm, 'StudyTime') else dt.strftime('%H%M%S.%f')
    struct.modality = dcm.Modality if hasattr(dcm, 'Modality') else ""
    struct.manufacturer = dcm.Manufacturer if hasattr(dcm, 'Manufacturer') else ""
    struct.seriesDescription = dcm.SeriesDescription if hasattr(dcm, 'SeriesDescription') else ""
    struct.manufacturerModelName = dcm.ManufacturerModelName if hasattr(dcm, 'ManufacturerModelName') else ""
    struct.patientName = dcm.PatientName if hasattr(dcm, 'PatientName') else ""
    struct.softwareVersions = dcm.SoftwareVersions if hasattr(dcm, 'SoftwareVersions') else ""
    struct.studyInstanceUID = dcm.StudyInstanceUID if hasattr(dcm, 'StudyInstanceUID') else ""
    struct.seriesInstanceUID = dcm.SeriesInstanceUID if hasattr(dcm, 'SeriesInstanceUID') else ""    
    struct.seriesNumber = dcm.SeriesNumber if hasattr(dcm, 'SeriesNumber') else ""
    struct.instanceNumber = dcm.InstanceNumber if hasattr(dcm, 'InstanceNumber') else "1"
    struct.frameOfReferenceUID = dcm.FrameOfReferenceUID if hasattr(dcm, 'FrameOfReferenceUID') else ""
    struct.structureSetDate = dcm.StructureSetDate if hasattr(dcm, 'StructureSetDate') else dt.strftime('%Y%m%d')
    struct.structureSetTime = dcm.StructureSetTime if hasattr(dcm, 'StructureSetTime') else dt.strftime('%H%M%S.%f')
    struct.seriesTime = dcm.SeriesTime if hasattr(dcm, 'SeriesTime') else dt.strftime('%H%M%S.%f')
    struct.sopClassUID = dcm.SOPClassUID if hasattr(dcm, 'SOPClassUID') else ""
    struct.structureSetLabel = dcm.StructureSetLabel if hasattr(dcm, 'StructureSetLabel') else 'OpenTPS Created'
    struct.rtROIObservationsSequence = dcm.RTROIObservationsSequence if hasattr(dcm, 'RTROIObservationsSequence') else []
    struct.referencedFrameOfReferenceSequence = dcm.ReferencedFrameOfReferenceSequence if hasattr(dcm, 'ReferencedFrameOfReferenceSequence') else []
    
    return struct

def writeRTStruct(struct: RTStruct, outputFile):
    """
    Export of TR structure data as a Dicom dose file.
    
    Parameters
    ----------
    struct: RTStruct
        The RTStruct object
        
    ctSeriesInstanceUID: str
        The serial instance UID of the CT associated with this RT structure.
    
    outputFile: str
        The output folde path
        
    NOTE: Get the CT serial instance UID by calling the 'writeDicomCT' function.
    """
    
    SOPInstanceUID = struct.sopInstanceUID
    # meta data
    meta = pydicom.dataset.FileMetaDataset()
    meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'
    meta.MediaStorageSOPInstanceUID = SOPInstanceUID
    meta.ImplementationClassUID = struct.implementationClassUID
    #'1.2.826.0.1.3680043.5.5.100.5.7.0.03'
    meta.TransferSyntaxUID = '1.2.840.10008.1.2'
    meta.ImplementationVersionName = struct.implementationVersionName
    # NOTE: Don't modify this value
    meta.FileMetaInformationGroupLength = 0 
            
    # dicom dataset
    dcm_file = pydicom.dataset.FileDataset(outputFile, {}, file_meta=meta, preamble=b"\0" * 128)
    dcm_file.SOPClassUID = meta.MediaStorageSOPClassUID
    dcm_file.SOPInstanceUID = SOPInstanceUID

    # patient information
    if not (struct.patient is None):
        dcm_file.PatientName = "exported_" + struct.patient.name
        dcm_file.PatientID = struct.patient.id
        dcm_file.PatientBirthDate = struct.patient.birthDate
        dcm_file.PatientSex = struct.patient.sex
    
    # content information
    dt = datetime.datetime.now()
    dcm_file.ContentDate = dt.strftime('%Y%m%d')
    dcm_file.ContentTime = dt.strftime('%H%M%S.%f')
    dcm_file.InstanceCreationDate = dt.strftime('%Y%m%d')
    dcm_file.InstanceCreationTime = dt.strftime('%H%M%S.%f')
    dcm_file.Modality = struct.modality
    dcm_file.Manufacturer = 'OpenMCsquare'
    dcm_file.ManufacturerModelName = 'OpenTPS'
    dcm_file.SeriesDescription = struct.name
    
    # wei test
    dcm_file.StudyInstanceUID = struct.studyInstanceUID +'1'
    SeriesInstanceUID = struct.seriesInstanceUID
    if SeriesInstanceUID == "" or (SeriesInstanceUID is None):
        SeriesInstanceUID = pydicom.uid.generate_uid()
    dcm_file.SeriesInstanceUID = SeriesInstanceUID
    dcm_file.SeriesNumber = 2
    dcm_file.InstanceNumber = 1

    dcm_file.StudyTime = struct.studyTime
    dcm_file.SeriesTime = struct.seriesTime
    dcm_file.FrameOfReferenceUID = struct.frameOfReferenceUID
    dcm_file.StructureSetDate = struct.structureSetDate
    dcm_file.StructureSetTime = struct.structureSetTime
    dcm_file.SOPClassUID = struct.sopClassUID
    dcm_file.StudyDate = struct.studyDate
    dcm_file.SeriesDate = struct.seriesDate
    dcm_file.StructureSetLabel = struct.structureSetLabel
    
    dcm_file.ReferencedFrameOfReferenceSequence = []
    for cidx, item in enumerate(struct.referencedFrameOfReferenceSequence, start=1):
        refFrameRef = pydicom.Dataset()
        refFrameRef.FrameOfReferenceUID = item.FrameOfReferenceUID
        rtRefSub1 = []
        for cSubIdx2, subItem1 in enumerate(item.RTReferencedStudySequence, start=1):
            rtRefSubObj1=pydicom.Dataset()
            rtRefSubObj1.ReferencedSOPClassUID = subItem1.ReferencedSOPClassUID if hasattr(subItem1, 'ReferencedSOPClassUID') else '1.2.840.10008.3.1.2.3.1'
            rtRefSubObj1.ReferencedSOPInstanceUID = subItem1.ReferencedSOPInstanceUID if hasattr(subItem1, 'ReferencedSOPInstanceUID') else pydicom.uid.generate_uid()
            rtRefSub2 = []
            for cSubIdx2, subItem2 in enumerate(subItem1.RTReferencedSeriesSequence, start=1):
                rtRefSubObject2 = pydicom.Dataset()
                rtRefSubObject2.SeriesInstanceUID = subItem2.SeriesInstanceUID
                contourSeq = []
                for cSubIdx3, subItem3 in enumerate(subItem2.ContourImageSequence, start=1):
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

      
    dcm_file.RTROIObservationsSequence = []
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
    print("Export dicom RTSTRCT: " + outputFile)
    dcm_file.save_as(outputFile)

################### Plan Image ############################################    
def readDicomPlan(dcmFile) -> RTPlan:
    dcm = pydicom.dcmread(dcmFile)

    # collect patient information
    if hasattr(dcm, 'PatientID'):
        brth = dcm.PatientBirthDate if hasattr(dcm, 'PatientBirthDate') else dt.strftime('%Y%m%d')
        sex = dcm.PatientSex if hasattr(dcm, 'PatientSex') else ''

        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=brth,
                      sex=sex)
    else:
        patient = Patient()

    if (hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""):
        name = dcm.SeriesDescription
    else:
        name = dcm.SeriesInstanceUID

    plan = RTPlan(name=name, patient = patient)
    # plan.patient = patient
    
    # Photon plan
    if dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.5":
        print("ERROR: Conventional radiotherapy (photon) plans are not supported")
        plan.modality = "RT Plan IOD"
        return

    # Ion plan
    elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.8":
        
        plan.modality = "RT Ion Plan IOD"

        if dcm.IonBeamSequence[0].RadiationType == "PROTON":
            plan.radiationType = "Proton"
        else:
            print("ERROR: Radiation type " + dcm.IonBeamSequence[0].RadiationType + " not supported")
            plan.radiationType = dcm.IonBeamSequence[0].RadiationType
            return

        if dcm.IonBeamSequence[0].ScanMode == "MODULATED":
            plan.scanMode = "MODULATED"  # PBS
        elif dcm.IonBeamSequence[0].ScanMode == "LINE":
            plan.scanMode = "LINE"  # Line Scanning
        else:
            print("ERROR: Scan mode " + dcm.IonBeamSequence[0].ScanMode + " not supported")
            plan.scanMode = dcm.IonBeamSequence[0].ScanMode
            return

            # Other
    else:
        print("ERROR: Unknown SOPClassUID " + dcm.SOPClassUID + " for file " + plan.DcmFile)
        plan.modality = "Unknown"
        return

    # Start parsing PBS plan
    plan.SOPInstanceUID = dcm.SOPInstanceUID
    plan.numberOfFractionsPlanned = int(dcm.FractionGroupSequence[0].NumberOfFractionsPlanned)

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
            print("ERROR: Beam number " + dcm_beam.BeamNumber + " not found in FractionGroupSequence.")
            print("This beam is therefore discarded.")
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
                print("ERROR: Unknown range shifter type for beam " + dcm_beam.BeamName if hasattr(dcm_beam, 'BeamName') else 'No beam name')
                # beam.rangeShifter.type = "none"
        else:
            print("ERROR: More than one range shifter defined for beam " + dcm_beam.BeamName if hasattr(dcm_beam, 'BeamName') else 'No beam name')
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
                layer.NumberOfPaintings = int(dcm_layer.NumberOfPaintings)
            else:
                layer.numberOfPaintings = 1

            layer.nominalEnergy = float(dcm_layer.NominalBeamEnergy)
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
        plan.mediaStorageSOPClassUID=dcm.file_meta.MediaStorageSOPClassUID if hasattr(dcm.file_meta, 'MediaStorageSOPClassUID') else ""
        plan.mediaStorageSOPInstanceUID=dcm.file_meta.MediaStorageSOPInstanceUID if hasattr(dcm.file_meta, 'MediaStorageSOPInstanceUID') else ""
        plan.transferSyntaxUID=dcm.file_meta.TransferSyntaxUID if hasattr(dcm.file_meta, 'TransferSyntaxUID') else ""
        plan.implementationClassUID=dcm.file_meta.ImplementationClassUID if hasattr(dcm.file_meta, 'ImplementationClassUID') else ""
        plan.implementationVersionName=dcm.file_meta.ImplementationVersionName if hasattr(dcm.file_meta, 'ImplementationVersionName') else ""
        
        plan.specificCharacterSet = dcm.SpecificCharacterSet if hasattr(dcm, 'SpecificCharacterSet') else ""
        plan.studyDate = dcm.StudyDate if hasattr(dcm, 'StudyDate') else dt.strftime('%Y%m%d')
        plan.seriesDate = dcm.SeriesDate if hasattr(dcm, 'SeriesDate') else dt.strftime('%H%M%S.%f')
        plan.studyTime = dcm.StudyTime if hasattr(dcm, 'StudyTime') else  dt.strftime('%H%M%S.%f')
        plan.modality = dcm.Modality if hasattr(dcm, 'Modality') else ""
        plan.seriesDescription = dcm.SeriesDescription if hasattr(dcm, 'SeriesDescription') else ""
        plan.softwareVersions=dcm.SoftwareVersions if hasattr(dcm, 'SoftwareVersions') else ""
        plan.studyInstanceUID=dcm.StudyInstanceUID if hasattr(dcm, 'StudyInstanceUID') else None
        plan.studyID = dcm.StudyID if hasattr(dcm, 'StudyID') else ""
        plan.seriesNumber = dcm.SeriesNumber if hasattr(dcm, 'SeriesNumber') else ""
        plan.frameOfReferenceUID = dcm.FrameOfReferenceUID if hasattr(dcm, 'FrameOfReferenceUID') else ""
        plan.rtPlanLabel = dcm.RTPlanLabel if hasattr(dcm, 'RTPlanLabel') else ""
        plan.rtPlanName = dcm.RTPlanName if hasattr(dcm, 'RTPlanName') else ""
        plan.rtPlanDate = dcm.RTPlanDate if hasattr(dcm, 'RTPlanDate') else dt.strftime('%Y%m%d')
        plan.rtPlanTime = dcm.RTPlanTime if hasattr(dcm, 'RTPlanTime') else dt.strftime('%H%M%S.%f')
        plan.treatmentProtocols = dcm.TreatmentProtocols if hasattr(dcm, 'TreatmentProtocols') else ""
        plan.planIntent = dcm.PlanIntent if hasattr(dcm, 'PlanIntent') else ""
        plan.rtPlanGeometry = dcm.RTPlanGeometry if hasattr(dcm, 'RTPlanGeometry') else ""
        plan.prescriptionDescription = dcm.PrescriptionDescription if hasattr(dcm, 'PrescriptionDescription') else ""
        plan.sopClassUID=dcm.SOPClassUID if hasattr(dcm, 'SOPClassUID') else ""
        plan.doseReferenceSequence=dcm.DoseReferenceSequence if hasattr(dcm, 'DoseReferenceSequence') else []
        plan.fractionGroupSequence = dcm.FractionGroupSequence if hasattr(dcm, 'FractionGroupSequence') else []
        plan.referencedStructureSetSequence = dcm.ReferencedStructureSetSequence if hasattr(dcm, 'ReferencedStructureSetSequence') else []
        plan.ionBeamSequence = dcm.IonBeamSequence if hasattr(dcm, 'IonBeamSequence') else []
        
    return plan

def writeRTPlan(plan: RTPlan, filePath):
    """
    Export the RT plan data as a Dicom dose file.

    Parameters
    ----------
    plan: RTPlan
        The RT plan data object
    filePath: str
        the output folder path
    """
    
    # meta data
    meta = pydicom.dataset.FileMetaDataset()
    meta.MediaStorageSOPClassUID = plan.mediaStorageSOPClassUID
    meta.MediaStorageSOPInstanceUID = plan.SOPInstanceUID
    meta.ImplementationClassUID = plan.implementationClassUID
    meta.TransferSyntaxUID = plan.transferSyntaxUID
    meta.ImplementationVersionName = plan.implementationVersionName
    
    # dicom dataset
    dcm_file = pydicom.dataset.FileDataset(filePath, {}, file_meta=meta, preamble=b"\0" * 128)
    dcm_file.SOPClassUID = plan.sopClassUID
    dcm_file.SOPInstanceUID = plan.SOPInstanceUID

    # patient information
    dcm_file.PatientName = "exported_" + plan.patient.name
    dcm_file.PatientID = plan.patient.id
    dcm_file.PatientBirthDate = plan.patient.birthDate
    dcm_file.PatientSex = plan.patient.sex

    # content information
    dt = datetime.datetime.now()
    dcm_file.ContentDate = dt.strftime('%Y%m%d')
    dcm_file.ContentTime = dt.strftime('%H%M%S.%f')
    dcm_file.InstanceCreationDate = dt.strftime('%Y%m%d')
    dcm_file.InstanceCreationTime = dt.strftime('%H%M%S.%f')
    dcm_file.Modality = plan.modality
    dcm_file.Manufacturer = 'OpenMCsquare'
    dcm_file.ManufacturerModelName = 'OpenTPS'
    dcm_file.SeriesDescription = plan.seriesDescription
    # wei test
    dcm_file.StudyInstanceUID = plan.studyInstanceUID+'1'
    
    dcm_file.StudyID = plan.studyID
    dcm_file.StudyDate = plan.studyDate
    dcm_file.StudyTime = plan.studyTime
    dcm_file.SpecificCharacterSet = plan.specificCharacterSet
    dcm_file.SeriesDate = plan.seriesDate
    dcm_file.SoftwareVersions = plan.softwareVersions
    dcm_file.SeriesNumber = plan.seriesNumber
    dcm_file.FrameOfReferenceUID = plan.frameOfReferenceUID
    dcm_file.RTPlanLabel = plan.rtPlanLabel
    dcm_file.RTPlanName = plan.rtPlanName
    dcm_file.RTPlanDate = plan.rtPlanDate
    dcm_file.RTPlanTime = plan.rtPlanTime
    dcm_file.TreatmentProtocols = plan.treatmentProtocols
    dcm_file.PlanIntent = plan.planIntent
    dcm_file.RTPlanGeometry = plan.rtPlanGeometry
    dcm_file.PrescriptionDescription = plan.prescriptionDescription

    SeriesInstanceUID = plan.seriesInstanceUID
    if SeriesInstanceUID == "" or (SeriesInstanceUID is None):
        SeriesInstanceUID = pydicom.uid.generate_uid()

    dcm_file.SeriesInstanceUID = SeriesInstanceUID
    dcm_file.SeriesNumber = plan.seriesNumber

    # plan information
    dcm_file.DoseReferenceSequence = []
    for cidx, item in enumerate(plan.doseReferenceSequence, start=1):
        doseRef= pydicom.Dataset()
        doseRef.ReferencedROINumber = item.ReferencedROINumber
        doseRef.DoseReferenceNumber = item.DoseReferenceNumber
        doseRef.DoseReferenceUID = item.DoseReferenceUID
        doseRef.DoseReferenceStructureType = item.DoseReferenceStructureType
        doseRef.DoseReferenceDescription = item.DoseReferenceDescription
        doseRef.DoseReferenceType = item.DoseReferenceType
        doseRef.TargetPrescriptionDose = item.TargetPrescriptionDose
        doseRef.TargetUnderdoseVolumeFraction = item.TargetUnderdoseVolumeFraction
        doseRef.PrivateCreator = 'OpenTPS'
        dcm_file.DoseReferenceSequence.append(doseRef)
    
    dcm_file.FractionGroupSequence = []
    fractionGroup = pydicom.dataset.Dataset()
    # Only 1 fraction spported right now!
    fractionGroup.NumberOfFractionsPlanned = 1  # plan.numberOfFractionsPlanned
    fractionGroup.NumberOfBrachyApplicationSetups = 0
    dcm_file.FractionGroupSequence.append(fractionGroup)
    fractionGroup.ReferencedBeamSequence = []
    
    dcm_file.IonBeamSequence = []
    for beamNumber, beam in enumerate(plan):
        referencedBeam = pydicom.dataset.Dataset()
        referencedBeam.BeamMeterset = floatToDS(beam.meterset)
        referencedBeam.ReferencedBeamNumber = beamNumber
        fractionGroup.ReferencedBeamSequence.append(referencedBeam)

        dcm_beam = pydicom.dataset.Dataset()
        dcm_beam.BeamName = beam.name
        dcm_beam.SeriesInstanceUID = SeriesInstanceUID
        dcm_beam.TreatmentMachineName = plan.treatmentMachineName
        dcm_beam.RadiationType = "PROTON"
        dcm_beam.ScanMode = "MODULATED"
        dcm_beam.TreatmentDeliveryType = "TREATMENT"
        dcm_beam.FinalCumulativeMetersetWeight = floatToDS(plan.beamCumulativeMetersetWeight[beamNumber])
        dcm_beam.BeamNumber = beamNumber
        dcm_beam.BeamType = 'STATIC'
        rangeShifter = beam.rangeShifter
        if rangeShifter is None:
            dcm_beam.NumberOfRangeShifters = 0
        else:
            dcm_beam.NumberOfRangeShifters = 1

        dcm_beam.RangeShifterSequence = []
        dcm_rs = pydicom.dataset.Dataset()
        if not (rangeShifter is None):
            dcm_rs.RangeShifterID = rangeShifter.ID
            if rangeShifter.type == "binary":
                dcm_rs.RangeShifterType = "BINARY"
            elif rangeShifter.type == "analog":
                dcm_rs.RangeShifterType = "ANALOG"
            else:
                print("ERROR: Unknown range shifter type: " + rangeShifter.type)

        dcm_beam.RangeShifterSequence.append(dcm_rs)
        dcm_file.IonBeamSequence.append(dcm_beam)

        dcm_beam.IonControlPointSequence = []

        for layerIndex,layer in enumerate(beam):
            dcm_layer = pydicom.dataset.Dataset()            
            dcm_layer.SeriesInstanceUID = SeriesInstanceUID
            dcm_layer.ControlPointIndex = layerIndex
            dcm_layer.NumberOfPaintings = layer.numberOfPaintings
            dcm_layer.NominalBeamEnergy = layer.nominalEnergy
            dcm_layer.ScanSpotPositionMap = np.array(list(layer.spotXY)).flatten().tolist()
            dcm_layer.ScanSpotMetersetWeights = layer.spotMUs.tolist()
            if type(dcm_layer.ScanSpotMetersetWeights) == float:
                dcm_layer.NumberOfScanSpotPositions = 1
            else: dcm_layer.NumberOfScanSpotPositions = len(dcm_layer.ScanSpotMetersetWeights)
            dcm_layer.IsocenterPosition = [beam.isocenterPosition[0], beam.isocenterPosition[1],
                                           beam.isocenterPosition[2]]
            dcm_layer.GantryAngle = beam.gantryAngle
            dcm_layer.PatientSupportAngle = beam.couchAngle

            dcm_layer.RangeShifterSettingsSequence = []
            dcm_rsSettings = pydicom.dataset.Dataset()
            dcm_rsSettings.IsocenterToRangeShifterDistance = layer.rangeShifterSettings.isocenterToRangeShifterDistance
            if not (layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness is None):
                dcm_rsSettings.RangeShifterWaterEquivalentThickness = layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness
            dcm_rsSettings.RangeShifterSetting = layer.rangeShifterSettings.rangeShifterSetting
            dcm_rsSettings.ReferencedRangeShifterNumber = 0
            dcm_layer.RangeShifterSettingsSequence.append(dcm_rsSettings)

            dcm_beam.IonControlPointSequence.append(dcm_layer)

    dcm_file.ReferencedStructureSetSequence = []
    for cidx, item in enumerate(plan.referencedStructureSetSequence, start=1):
        refStructSeq = pydicom.Dataset()
        refStructSeq.ReferencedSOPClassUID = item.ReferencedSOPClassUID
        refStructSeq.ReferencedSOPInstanceUID = item.ReferencedSOPInstanceUID
    dcm_file.ReferencedStructureSetSequence.append(refStructSeq)
    
    # save dicom file
    print("Export dicom TRAINMENT PLAN: " + filePath)
    dcm_file.save_as(filePath)
    
    
# ##########################################################
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
        brth = dcm.PatientBirthDate if hasattr(dcm, 'PatientBirthDate') else None
        sex = dcm.PatientSex if hasattr(dcm, 'PatientSex') else None
        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=brth,
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
