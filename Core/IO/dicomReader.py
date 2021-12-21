import os, sys
import pydicom
import numpy as np
from PIL import Image, ImageDraw
import logging

from Core.Data.patientInfo import PatientInfo
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.roiStruct import ROIStruct
from Core.Data.Images.roiContour import ROIContour
from Core.Data.Images.vectorField3D import VectorField3D

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
    imageData = np.dstack(images).astype("float32").transpose(1,0,2)

    # verify reconstructed volume
    if imageData.shape[0:2] != (dcm.Columns, dcm.Rows):
        logging.warning("WARNING: GridSize " + str(imageData.shape[0:2]) + " different from Dicom Columns (" + str(dcm.Columns) + ") and Rows (" + str(dcm.Rows) + ")")

    # collect image information
    meanSliceDistance = (sliceLocation[-1] - sliceLocation[0]) / (len(images)-1)
    if(hasattr(dcm, 'SliceThickness') and (type(dcm.SliceThickness) == int or type(dcm.SliceThickness) == float) and abs(meanSliceDistance - dcm.SliceThickness) > 0.001):
        logging.warning("WARNING: Mean Slice Distance (" + str(meanSliceDistance) + ") is different from Slice Thickness (" + str(dcm.SliceThickness) + ")")

    if(hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""): imgName = dcm.SeriesDescription
    else: imgName = dcm.SeriesInstanceUID

    pixelSpacing = (float(dcm.PixelSpacing[1]), float(dcm.PixelSpacing[0]), meanSliceDistance)
    imagePositionPatient = (float(dcm.ImagePositionPatient[0]), float(dcm.ImagePositionPatient[1]), sliceLocation[0])

    # collect patient information
    patientInfo = PatientInfo(patientID=dcm.PatientID, name=str(dcm.PatientName), birthDate=dcm.PatientBirthDate, sex=dcm.PatientSex)

    # generate CT image object
    image = CTImage(data=imageData, name=imgName, patientInfo=patientInfo, origin=imagePositionPatient, spacing=pixelSpacing, seriesInstanceUID=dcm.SeriesInstanceUID, frameOfReferenceUID=dcm.FrameOfReferenceUID, sliceLocation=sliceLocation, sopInstanceUIDs=sopInstanceUIDs)

    return image



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
    if(dcm.BitsStored == 16 and dcm.PixelRepresentation == 0):
      dt = np.dtype('uint16')
    elif(dcm.BitsStored == 16 and dcm.PixelRepresentation == 1):
      dt = np.dtype('int16')
    elif(dcm.BitsStored == 32 and dcm.PixelRepresentation == 0):
      dt = np.dtype('uint32')
    elif(dcm.BitsStored == 32 and dcm.PixelRepresentation == 1):
      dt = np.dtype('int32')
    else:
      logging.error("Error: Unknown data type for " + self.DcmFile)
      return None
      
    if(dcm.HighBit == dcm.BitsStored-1):
      dt = dt.newbyteorder('L')
    else:
      dt = dt.newbyteorder('B')
      
    imageData = np.frombuffer(dcm.PixelData, dtype=dt) 
    imageData = imageData.reshape((dcm.Columns, dcm.Rows, dcm.NumberOfFrames), order='F')
    imageData = imageData * dcm.DoseGridScaling

    # collect other information
    if(hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""): imgName = dcm.SeriesDescription
    else: imgName = dcm.SeriesInstanceUID

    planSOPInstanceUID = dcm.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID

    if(type(dcm.SliceThickness) == float): sliceThickness = dcm.SliceThickness
    else: sliceThickness = (dcm.GridFrameOffsetVector[-1] - dcm.GridFrameOffsetVector[0]) / (len(dcm.GridFrameOffsetVector)-1)

    pixelSpacing = (float(dcm.PixelSpacing[1]), float(dcm.PixelSpacing[0]), sliceThickness)
    imagePositionPatient = tuple(dcm.ImagePositionPatient)

    # check image orientation
    # TODO use image angle instead
    if hasattr(dcm, 'GridFrameOffsetVector'):
        if(dcm.GridFrameOffsetVector[1] - dcm.GridFrameOffsetVector[0] < 0):
            imageData = np.flip(imageData, 2)
            imagePositionPatient[2] = imagePositionPatient[2] - imageData.shape[2] * pixelSpacing[2]

    # collect patient information
    patientInfo = PatientInfo(patientID=dcm.PatientID, name=str(dcm.PatientName), birthDate=dcm.PatientBirthDate, sex=dcm.PatientSex)

    # generate dose image object
    image = DoseImage(data=imageData, name=imgName, patientInfo=patientInfo, origin=imagePositionPatient, spacing=pixelSpacing, seriesInstanceUID=dcm.SeriesInstanceUID, frameOfReferenceUID=dcm.FrameOfReferenceUID, sopInstanceUID=dcm.SOPInstanceUID, planSOPInstanceUID=planSOPInstanceUID)

    return image

def readDicomStruct(dcmFile, refImage):
    """
    Read a Dicom structure file and generate a ROIStruct image object.

    Parameters
    ----------
    dcmFile: str
        Path of the Dicom struct file.

    Returns
    -------
    data: ROIStruct object
        The function returns the imported roi structure object
    """
    # Read DICOM file
    dcm = pydicom.dcmread(dcmFile)
    # Create the object that will be returned. Takes the same patientInfo as the refImage it is linked to
    roiStruct = ROIStruct(refImage.patientInfo)
    roiStruct.seriesInstanceUID = dcm.SeriesInstanceUID
    roiStruct.refImageSeriesInstanceUID = refImage.seriesInstanceUID

    contours = []
    for dcmStruct in dcm.StructureSetROISequence:
        referencedRoiId = next((x for x, val in enumerate(dcm.ROIContourSequence) if val.ReferencedROINumber == dcmStruct.ROINumber), -1)
        dcmContour = dcm.ROIContourSequence[referencedRoiId]

        # Create ROIContour object
        contour = ROIContour()
        contour.seriesInstanceUID = roiStruct.seriesInstanceUID
        contour.name = dcmStruct.ROIName
        contour.displayColor = dcmContour.ROIDisplayColor

        contour.data = np.zeros(refImage.getGridSize())
        contour.spacing = refImage.spacing
        contour.origin = refImage.origin

        sopInstanceUIDMatch = 1

        if not hasattr(dcmContour, 'ContourSequence'):
            logging.warning("This structure has no attribute ContourSequence. Skipping...")
            continue

        for dcmSlice in dcmContour.ContourSequence:
            slice = {}
            # list of DICOM coordinates
            slice["XY_dcm"] = list(zip( np.array(dcmSlice.ContourData[0::3]), np.array(dcmSlice.ContourData[1::3]) ))
            slice["Z_dcm"] = float(dcmSlice.ContourData[2])
            # list of coordinates in the image frame
            slice["XY_img"] = list(zip( ((np.array(dcmSlice.ContourData[0::3]) - refImage.origin[0]) / refImage.spacing[0]), ((np.array(dcmSlice.ContourData[1::3]) - refImage.origin[1]) / refImage.spacing[1]) ))
            slice["Z_img"] = (slice["Z_dcm"] - refImage.origin[2]) / refImage.spacing[2]
            slice["Slice_id"] = int(round(slice["Z_img"]))
            
            # convert polygon to mask (based on PIL - fast)
            img = Image.new('L', (refImage.getGridSize()[0], refImage.getGridSize()[1]), 0)
            if(len(slice["XY_img"]) > 1): ImageDraw.Draw(img).polygon(slice["XY_img"], outline=1, fill=1)
            mask = np.array(img)
            contour.data[:,:,slice["Slice_id"]] = np.logical_or(contour.data[:,:,slice["Slice_id"]], mask)
            contour.contourSequence.append(slice)
            
            # check if the contour sequence is imported on the correct CT slice:
            if(hasattr(dcmSlice, 'ContourImageSequence') and refImage.sopInstanceUIDs[slice["Slice_id"]] != dcmSlice.ContourImageSequence[0].ReferencedSOPInstanceUID):
                sopInstanceUIDMatch = 0
        
        if sopInstanceUIDMatch != 1:
            logging.warning("WARNING: some SOPInstanceUIDs don't match during importation of " + contour.name + " contour on CT image")
    
        contours.append(contour)

    roiStruct.contours = contours
    roiStruct.numContours = len(contours)
    return roiStruct

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

    # convert from mm to pixels
    for i in range(3):
        fieldData[:, :, :, i] = fieldData[:, :, :, i] / pixelSpacing[i]

    # collect patient information
    patientInfo = PatientInfo(patientID=dcm.PatientID, name=str(dcm.PatientName), birthDate=dcm.PatientBirthDate,
                              sex=dcm.PatientSex)

    # collect other information
    if (hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""):
        fieldName = dcm.SeriesDescription
    else:
        fieldName = dcm.SeriesInstanceUID

    # generate dose image object
    field = VectorField3D(data=fieldData, name=fieldName, patientInfo=patientInfo, origin=imagePositionPatient,
                      spacing=pixelSpacing)

    return field
