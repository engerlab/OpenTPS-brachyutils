import datetime
import pydicom
import numpy as np
import logging

from opentps.core.data import Patient
from opentps.core.data.plan._rangeShifter import RangeShifter

from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data.plan._planIonBeam import PlanIonBeam
from opentps.core.data.plan._planIonLayer import PlanIonLayer
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._doseImage import DoseImage
from opentps.core.data._rtStruct import RTStruct
from opentps.core.data._roiContour import ROIContour
from opentps.core.data.images._vectorField3D import VectorField3D


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
        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=dcm.PatientBirthDate,
                              sex=dcm.PatientSex)
    else:
        patient = Patient()

    # generate CT image object
    image = CTImage(imageArray=imageData, name=imgName, origin=imagePositionPatient,
                    spacing=pixelSpacing, seriesInstanceUID=dcm.SeriesInstanceUID,
                    frameOfReferenceUID=dcm.FrameOfReferenceUID, sliceLocation=sliceLocation,
                    sopInstanceUIDs=sopInstanceUIDs)
    image.patient = patient

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
    if (dcm.BitsStored == 16 and dcm.PixelRepresentation == 0):
        dt = np.dtype('uint16')
    elif (dcm.BitsStored == 16 and dcm.PixelRepresentation == 1):
        dt = np.dtype('int16')
    elif (dcm.BitsStored == 32 and dcm.PixelRepresentation == 0):
        dt = np.dtype('uint32')
    elif (dcm.BitsStored == 32 and dcm.PixelRepresentation == 1):
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
        sliceThickness = (dcm.GridFrameOffsetVector[-1] - dcm.GridFrameOffsetVector[0]) / (
                    len(dcm.GridFrameOffsetVector) - 1)

    pixelSpacing = (float(dcm.PixelSpacing[1]), float(dcm.PixelSpacing[0]), sliceThickness)
    imagePositionPatient = tuple(dcm.ImagePositionPatient)

    # check image orientation
    # TODO use image angle instead
    if hasattr(dcm, 'GridFrameOffsetVector'):
        if (dcm.GridFrameOffsetVector[1] - dcm.GridFrameOffsetVector[0] < 0):
            imageData = np.flip(imageData, 2)
            imagePositionPatient[2] = imagePositionPatient[2] - imageData.shape[2] * pixelSpacing[2]

    # collect patient information
    if hasattr(dcm, 'PatientID'):
        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=dcm.PatientBirthDate,
                      sex=dcm.PatientSex)
    else:
        patient = Patient()

    # generate dose image object
    image = DoseImage(imageArray=imageData, name=imgName, origin=imagePositionPatient,
                      spacing=pixelSpacing, seriesInstanceUID=dcm.SeriesInstanceUID,
                      sopInstanceUID=dcm.SOPInstanceUID)
    image.patient = patient

    return image


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

    if (hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""):
        structName = dcm.SeriesDescription
    else:
        structName = dcm.SeriesInstanceUID

    # collect patient information
    if hasattr(dcm, 'PatientID'):
        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=dcm.PatientBirthDate,
                      sex=dcm.PatientSex)
    else:
        patient = Patient()

    # Create the object that will be returned. Takes the same patientInfo as the refImage it is linked to
    struct = RTStruct(name=structName, seriesInstanceUID=dcm.SeriesInstanceUID,
                      sopInstanceUID=dcm.SOPInstanceUID)
    struct.patient = patient

    for dcmStruct in dcm.StructureSetROISequence:
        referencedRoiId = next(
            (x for x, val in enumerate(dcm.ROIContourSequence) if val.ReferencedROINumber == dcmStruct.ROINumber), -1)
        dcmContour = dcm.ROIContourSequence[referencedRoiId]

        if not hasattr(dcmContour, 'ContourSequence'):
            logging.warning("This structure has no attribute ContourSequence. Skipping...")
            continue

        # Create ROIContour object
        color = tuple([int(c) for c in list(dcmContour.ROIDisplayColor)])
        contour = ROIContour(name=dcmStruct.ROIName, displayColor=color,
                             referencedFrameOfReferenceUID=dcmStruct.ReferencedFrameOfReferenceUID)
        contour.patient = patient

        for dcmSlice in dcmContour.ContourSequence:
            contour.polygonMesh.append(dcmSlice.ContourData)  # list of coordinates (XYZ) for the polygon
            contour.referencedSOPInstanceUIDs.append(dcmSlice.ContourImageSequence[
                                                         0].ReferencedSOPInstanceUID)  # UID of the image of reference (eg. ct slice)

        struct.appendContour(contour)

    return struct


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
        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=dcm.PatientBirthDate,
                      sex=dcm.PatientSex)
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


def readDicomPlan(dcmFile) -> RTPlan:
    dcm = pydicom.dcmread(dcmFile)

    # collect patient information
    if hasattr(dcm, 'PatientID'):
        patient = Patient(id=dcm.PatientID, name=str(dcm.PatientName), birthDate=dcm.PatientBirthDate,
                      sex=dcm.PatientSex)
    else:
        patient = Patient()

    if (hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""):
        name = dcm.SeriesDescription
    else:
        name = dcm.SeriesInstanceUID

    plan = RTPlan(name=name)
    plan.patient = patient

    # plan.OriginalDicomDataset = dcm

    # Photon plan
    if dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.5":
        print("ERROR: Conventional radiotherapy (photon) plans are not supported")
        plan.modality = "Radiotherapy"
        return

    # Ion plan
    elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.8":
        plan.modality = "Ion therapy"

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
        plan.treatmentMachineName = dcm.IonBeamSequence[0].TreatmentMachineName
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
                print("ERROR: Unknown range shifter type for beam " + dcm_beam.BeamName)
                # beam.rangeShifter.type = "none"
        else:
            print("ERROR: More than one range shifter defined for beam " + dcm_beam.BeamName)
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

    return plan


def writeRTPlan(plan: RTPlan, filePath):
    SOPInstanceUID = pydicom.uid.generate_uid()

    # meta data
    meta = pydicom.dataset.FileMetaDataset()
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.481.8"
    meta.MediaStorageSOPInstanceUID = SOPInstanceUID
    meta.ImplementationClassUID = '1.2.826.0.1.3680043.5.5.100.5.7.0.03'

    # dicom dataset
    dcm_file = pydicom.dataset.FileDataset(filePath, {}, file_meta=meta, preamble=b"\0" * 128)
    dcm_file.SOPClassUID = meta.MediaStorageSOPClassUID
    dcm_file.SOPInstanceUID = SOPInstanceUID

    # patient information
    dcm_file.PatientName = plan.patient.name
    dcm_file.PatientID = plan.patient.id
    dcm_file.PatientBirthDate = plan.patient.birthDate
    dcm_file.PatientSex = plan.patient.sex

    # content information
    dt = datetime.datetime.now()
    dcm_file.ContentDate = dt.strftime('%Y%m%d')
    dcm_file.ContentTime = dt.strftime('%H%M%S.%f')
    dcm_file.InstanceCreationDate = dt.strftime('%Y%m%d')
    dcm_file.InstanceCreationTime = dt.strftime('%H%M%S.%f')
    dcm_file.Modality = 'RTPLAN'
    dcm_file.Manufacturer = 'OpenMCsquare'
    dcm_file.ManufacturerModelName = 'OpenTPS'
    # dcm_file.SeriesDescription = self.ImgName
    # dcm_file.StudyInstanceUID = self.StudyInfo.StudyInstanceUID
    # dcm_file.StudyID = self.StudyInfo.StudyID
    # dcm_file.StudyDate = self.StudyInfo.StudyDate
    # dcm_file.StudyTime = self.StudyInfo.StudyTime

    SeriesInstanceUID = plan.seriesInstanceUID
    if SeriesInstanceUID == "" or (SeriesInstanceUID is None):
        SeriesInstanceUID = pydicom.uid.generate_uid()

    dcm_file.SeriesInstanceUID = SeriesInstanceUID
    # dcm_file.SeriesNumber = 1
    # dcm_file.InstanceNumber = 1

    # plan information
    dcm_file.FractionGroupSequence = []
    fractionGroup = pydicom.dataset.Dataset()
    # Only 1 fraction spported right now!
    fractionGroup.NumberOfFractionsPlanned = 1  # plan.numberOfFractionsPlanned
    dcm_file.FractionGroupSequence.append(fractionGroup)
    fractionGroup.ReferencedBeamSequence = []

    dcm_file.IonBeamSequence = []

    for beamNumber, beam in enumerate(plan):
        referencedBeam = pydicom.dataset.Dataset()
        referencedBeam.BeamMeterset = beam.meterset
        referencedBeam.ReferencedBeamNumber = beamNumber
        fractionGroup.ReferencedBeamSequence.append(referencedBeam)

        dcm_beam = pydicom.dataset.Dataset()
        dcm_beam.BeamName = beam.name
        dcm_beam.SeriesInstanceUID = SeriesInstanceUID
        dcm_beam.TreatmentMachineName = plan.treatmentMachineName
        dcm_beam.RadiationType = "PROTON"
        dcm_beam.ScanMode = "MODULATED"
        dcm_beam.TreatmentDeliveryType = "TREATMENT"
        dcm_beam.FinalCumulativeMetersetWeight = plan.beamCumulativeMetersetWeight[beamNumber]
        dcm_beam.BeamNumber = beamNumber

        rangeShifter = beam.rangeShifter
        if rangeShifter is None:
            dcm_beam.NumberOfRangeShifters = 0
        else:
            dcm_beam.NumberOfRangeShifters = 1

        dcm_beam.RangeShifterSequence = []
        dcm_rs = pydicom.dataset.Dataset()
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
        for layer in beam:
            dcm_layer = pydicom.dataset.Dataset()
            dcm_layer.SeriesInstanceUID = SeriesInstanceUID
            dcm_layer.NumberOfPaintings = layer.numberOfPaintings
            dcm_layer.NominalBeamEnergy = layer.nominalEnergy
            dcm_layer.ScanSpotPositionMap = np.array(list(layer.spotXY)).flatten().tolist()
            dcm_layer.ScanSpotMetersetWeights = layer.spotMUs.tolist()
            dcm_layer.NumberOfScanSpotPositions = len(dcm_layer.ScanSpotMetersetWeights)
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

    dcm_file.save_as(filePath)

def writeRTDose(dose:DoseImage, outputFile):
    SOPInstanceUID = pydicom.uid.generate_uid()

    # meta data
    meta = pydicom.dataset.FileMetaDataset()
    meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'
    meta.MediaStorageSOPInstanceUID = SOPInstanceUID
    # meta.ImplementationClassUID = '1.2.826.0.1.3680043.1.2.100.5.7.0.47' # from RayStation
    meta.ImplementationClassUID = '1.2.826.0.1.3680043.5.5.100.5.7.0.03'  # modified
    # meta.FileMetaInformationGroupLength =
    # meta.FileMetaInformationVersion =

    # dicom dataset
    dcm_file = pydicom.dataset.FileDataset(outputFile, {}, file_meta=meta, preamble=b"\0" * 128)
    dcm_file.SOPClassUID = meta.MediaStorageSOPClassUID
    dcm_file.SOPInstanceUID = SOPInstanceUID
    # dcm_file.ImplementationVersionName =
    # dcm_file.SpecificCharacterSet =
    # dcm_file.AccessionNumber =
    # dcm_file.SoftwareVersion =

    # patient information
    patient = dose.patient
    if not (patient is None):
        dcm_file.PatientName = patient.name
        dcm_file.PatientID = patient.id
        dcm_file.PatientBirthDate = patient.birthDate
        dcm_file.PatientSex = patient.sex

    # content information
    dt = datetime.datetime.now()
    dcm_file.ContentDate = dt.strftime('%Y%m%d')
    dcm_file.ContentTime = dt.strftime('%H%M%S.%f')
    dcm_file.InstanceCreationDate = dt.strftime('%Y%m%d')
    dcm_file.InstanceCreationTime = dt.strftime('%H%M%S.%f')
    dcm_file.Modality = 'RTDOSE'
    dcm_file.Manufacturer = 'OpenMCsquare'
    dcm_file.ManufacturerModelName = 'OpenTPS'
    dcm_file.SeriesDescription = dose.name
    dcm_file.StudyInstanceUID = pydicom.uid.generate_uid()
    #dcm_file.StudyID = self.StudyInfo.StudyID
    #dcm_file.StudyDate = self.StudyInfo.StudyDate
    #dcm_file.StudyTime = self.StudyInfo.StudyTime
    dcm_file.SeriesInstanceUID = dose.seriesInstanceUID
    dcm_file.SeriesNumber = 1
    dcm_file.InstanceNumber = 1
    dcm_file.PatientOrientation = ''
    if dose.referenceCT is None:
        dcm_file.FrameOfReferenceUID = pydicom.uid.generate_uid()
    else:
        dcm_file.FrameOfReferenceUID = dose.referenceCT.frameOfReferenceUID
    dcm_file.DoseUnits = 'GY'
    dcm_file.DoseType = 'PHYSICAL'  # or 'EFFECTIVE' for RBE dose (but RayStation exports physical dose even if 1.1 factor is already taken into account)
    dcm_file.DoseSummationType = 'PLAN'
    ReferencedPlan = pydicom.dataset.Dataset()
    ReferencedPlan.ReferencedSOPClassUID = "1.2.840.10008.5.1.4.1.1.481.8"  # ion plan
    if dose.referencePlan is None:
        ReferencedPlan.ReferencedSOPInstanceUID = pydicom.uid.generate_uid()
    else:
        ReferencedPlan.ReferencedSOPInstanceUID = dose.referencePlan.SOPInstanceUID
    dcm_file.ReferencedRTPlanSequence = pydicom.sequence.Sequence([ReferencedPlan])
    # dcm_file.ReferringPhysicianName
    # dcm_file.OperatorName

    # image information
    dcm_file.Width = dose.gridSize[0]
    dcm_file.Columns = dcm_file.Width
    dcm_file.Height = dose.gridSize[1]
    dcm_file.Rows = dcm_file.Height
    dcm_file.NumberOfFrames = dose.gridSize[2]
    dcm_file.SliceThickness = dose.spacing[2]
    dcm_file.PixelSpacing = list(dose.spacing[0:2])
    dcm_file.ColorType = 'grayscale'
    dcm_file.ImagePositionPatient = list(dose.origin)
    dcm_file.ImageOrientationPatient = [1, 0, 0, 0, 1,
                                        0]  # HeadFirstSupine=1,0,0,0,1,0  FeetFirstSupine=-1,0,0,0,1,0  HeadFirstProne=-1,0,0,0,-1,0  FeetFirstProne=1,0,0,0,-1,0
    dcm_file.SamplesPerPixel = 1
    dcm_file.PhotometricInterpretation = 'MONOCHROME2'
    dcm_file.FrameIncrementPointer = pydicom.tag.Tag((0x3004, 0x000c))
    dcm_file.GridFrameOffsetVector = list(
        np.arange(0, dose.gridSize[2] * dose.spacing[2], dose.spacing[2]))

    # transfer syntax
    dcm_file.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    dcm_file.is_little_endian = True
    dcm_file.is_implicit_VR = False

    # image data
    dcm_file.BitDepth = 16
    dcm_file.BitsAllocated = 16
    dcm_file.BitsStored = 16
    dcm_file.HighBit = 15
    dcm_file.PixelRepresentation = 0  # 0=unsigned, 1=signed
    dcm_file.DoseGridScaling = dose.imageArray.max() / (2 ** dcm_file.BitDepth - 1)
    dcm_file.PixelData = (dose.imageArray / dcm_file.DoseGridScaling).astype(np.uint16).transpose(2, 1, 0).tostring()

    # print(dcm_file)

    # save dicom file
    print("Export dicom RTDOSE: " + outputFile)
    dcm_file.save_as(outputFile)
