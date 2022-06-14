import os
import platform
import shutil
import struct
import time
import unittest
from typing import Optional, Sequence

import numpy as np
import pydicom
import scipy.sparse as sp
from scipy.sparse import csc_matrix

from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareCTCalibration import MCsquareCTCalibration
from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareMaterial import MCsquareMaterial
from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareMolecule import MCsquareMolecule
from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.MCsquare.bdl import BDL
from Core.Data.MCsquare.mcsquareConfig import MCsquareConfig
from Core.Data.Plan.objectivesList import ObjectivesList
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rangeShifter import RangeShifter
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.sparseBeamlets import SparseBeamlets
from Core.IO import mhdIO
from Core.IO.mhdIO import exportImageMHD, importImageMHD
from Core.Processing.ImageProcessing import crop3D


def readBeamlets(file_path, roi: Optional[ROIMask] = None):
    if (not file_path.endswith('.txt')):
        raise NameError('File ', file_path, ' is not a valid sparse matrix header')

    # Read sparse beamlets header file
    print('Read sparse beamlets: ', file_path)
    header = _read_sparse_header(file_path)

    if (header["SimulationMode"] != 'Beamlet'):
        raise ValueError('Not a beamlet file')

    # Read sparse beamlets binary file
    print('Read binary file: ', file_path)
    sparseBeamlets = _read_sparse_data(header["Binary_file"], header["NbrVoxels"], header["NbrSpots"], roi)

    beamletDose = SparseBeamlets()
    beamletDose.setUnitaryBeamlets(sparseBeamlets)
    beamletDose.beamletWeights = np.ones(header["NbrSpots"])
    beamletDose.doseOrigin = header["Offset"]
    beamletDose.doseSpacing = header["VoxelSpacing"]
    beamletDose.doseGridSize = header["ImageSize"]

    return beamletDose


def _read_sparse_header(file_path):
    header = {}

    # Parse file path
    Folder, File = os.path.split(file_path)
    FileName, FileExtension = os.path.splitext(File)
    Header_file = file_path
    header["ImgName"] = FileName

    with open(Header_file, 'r') as fid:
        for line in fid:
            if not line.startswith("#"):
                key, val = line.split('=')
                key = key.strip()
                if key == 'NbrSpots':
                    header["NbrSpots"] = int(val)
                elif key == 'ImageSize':
                    ImageSize = [int(i) for i in val.split()]
                    header["ImageSize"] = (ImageSize[0], ImageSize[1], ImageSize[2])
                    header["NbrVoxels"] = ImageSize[0] * ImageSize[1] * ImageSize[2]
                elif key == 'VoxelSpacing':
                    header["VoxelSpacing"] = [float(i) for i in val.split()]
                elif key == 'Offset':
                    header["Offset"] = [float(i) for i in val.split()]
                elif key == 'SimulationMode':
                    header["SimulationMode"] = val.strip()
                elif key == 'BinaryFile':
                    header["Binary_file"] = os.path.join(Folder, val.strip())

    return header


def _read_sparse_data(Binary_file, NbrVoxels, NbrSpots, roi: Optional[ROIMask] = None) -> csc_matrix:
    BeamletMatrix = []

    fid = open(Binary_file, 'rb')

    buffer_size = 5 * NbrVoxels
    col_index = np.zeros((buffer_size), dtype=np.uint32)
    row_index = np.zeros((buffer_size), dtype=np.uint32)
    beamlet_data = np.zeros((buffer_size), dtype=np.float32)
    data_id = 0
    last_stacked_col = 0
    num_unstacked_col = 1

    print("roi shape = ", roi.imageArray.shape)
    print('nspots =', NbrSpots)
    print('nvox =', NbrVoxels)

    if not (roi is None):
        roiData = roi.imageArray
        roiData = np.flip(roiData, 0)
        roiData = np.flip(roiData, 1)
        roiData = roiData.flatten(order='F')
        roiData = roiData.astype(bool)
        roiData = roiData.flatten()
    else:
        roiData = np.zeros((NbrVoxels, 1)).astype(bool)

    time_start = time.time()

    for spot in range(NbrSpots):
        [NonZeroVoxels] = struct.unpack('I', fid.read(4))
        [BeamID] = struct.unpack('I', fid.read(4))
        [LayerID] = struct.unpack('I', fid.read(4))
        [xcoord] = struct.unpack('<f', fid.read(4))
        [ycoord] = struct.unpack('<f', fid.read(4))

        if (NonZeroVoxels == 0): continue

        ReadVoxels = 0
        while (1):
            [NbrContinuousValues] = struct.unpack('I', fid.read(4))
            ReadVoxels += NbrContinuousValues

            [FirstIndex] = struct.unpack('I', fid.read(4))

            for j in range(NbrContinuousValues):
                [temp] = struct.unpack('<f', fid.read(4))

                rowIndexVal = FirstIndex + j
                if roiData[rowIndexVal]:
                    beamlet_data[data_id] = temp
                    row_index[data_id] = rowIndexVal
                    col_index[data_id] = spot - last_stacked_col
                    data_id += 1

            if (ReadVoxels >= NonZeroVoxels):
                if spot == 0:
                    BeamletMatrix = sp.csc_matrix(
                        (beamlet_data[:data_id], (row_index[:data_id], col_index[:data_id])), shape=(NbrVoxels, 1),
                        dtype=np.float32)
                    data_id = 0
                    last_stacked_col = spot + 1
                    num_unstacked_col = 1
                elif (data_id > buffer_size - NbrVoxels):
                    A = sp.csc_matrix((beamlet_data[:data_id], (row_index[:data_id], col_index[:data_id])),
                                      shape=(NbrVoxels, num_unstacked_col), dtype=np.float32)
                    data_id = 0
                    BeamletMatrix = sp.hstack([BeamletMatrix, A])
                    last_stacked_col = spot + 1
                    num_unstacked_col = 1
                else:
                    num_unstacked_col += 1

                break

    # stack last cols
    A = sp.csc_matrix((beamlet_data[:data_id], (row_index[:data_id], col_index[:data_id])),
                      shape=(NbrVoxels, num_unstacked_col - 1), dtype=np.float32)
    print("A shape = ", A.shape)
    print("BL shape = ", beamlet_data.shape)
    print("num_unstacked_col =", num_unstacked_col)
    BeamletMatrix = sp.hstack([BeamletMatrix, A])

    print('Beamlets imported in ' + str(time.time() - time_start) + ' sec')

    _print_memory_usage(BeamletMatrix)

    fid.close()
    return BeamletMatrix


def _print_memory_usage(BeamletMatrix):
    if (BeamletMatrix == []):
        print(" ")
        print("Beamlets not loaded")
        print(" ")

    else:
        mat_size = BeamletMatrix.data.nbytes + BeamletMatrix.indptr.nbytes + BeamletMatrix.indices.nbytes
        print(" ")
        print("Beamlets loaded")
        print("Matrix size: " + str(BeamletMatrix.shape))
        print("Non-zero values: " + str(BeamletMatrix.nnz))
        print("Data format: " + str(BeamletMatrix.dtype))
        print("Memory usage: " + str(mat_size / 1024 ** 3) + " GB")
        print(" ")


def readDose(filePath):
    doseMHD = importImageMHD(filePath)

    # Convert data for compatibility with MCsquare
    # These transformations may be modified in a future version
    doseMHD.imageArray = np.flip(doseMHD.imageArray, 0)
    doseMHD.imageArray = np.flip(doseMHD.imageArray, 1)

    doseImage = DoseImage.fromImage(doseMHD)

    return doseImage

def readMCsquarePlan(ct: CTImage, file_path):
    destFolder, destFile = os.path.split(file_path)
    fileName, fileExtension = os.path.splitext(destFile)

    plan = RTPlan()
    plan.seriesInstanceUID = pydicom.uid.generate_uid()
    plan.planName = fileName
    plan.modality = "Ion therapy"
    plan.radiationType = "Proton"
    plan.scanMode = "MODULATED"
    plan.treatmentMachineName = "Unknown"

    numSpots = 0

    with open(file_path, 'r') as f:
        line = f.readline()
        while line:
            # clean the string
            line = line.replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')

            if line == "#PlanName":
                plan.planName = f.readline().replace('\r', '').replace('\n', '').replace('\t', ' ')

            elif line == "#NumberOfFractions":
                plan.numberOfFractionsPlanned = int(f.readline())

            elif line == "#TotalMetersetWeightOfAllFields":
                plan.meterset = float(f.readline())

            elif line == "#FIELD-DESCRIPTION":
                plan._beams.append(PlanIonBeam())
                plan.beams[-1].seriesInstanceUID = plan.seriesInstanceUID

            elif line == "###FieldID" and len(plan.beams) > 0:
                plan.beams[-1].name = f.readline()

            elif line == "###FinalCumulativeMeterSetWeight":
                plan.beams[-1].meterset = float(f.readline())

            elif line == "###GantryAngle":
                plan.beams[-1].gantryAngle = float(f.readline())

            elif line == "###PatientSupportAngle":
                plan.beams[-1].patientSupportAngle = float(f.readline())

            elif line == "###IsocenterPosition":
                # read isocenter in MCsquare coordinates
                iso = f.readline().replace('\r', '').replace('\n', '').replace('\t', ' ').split()
                iso = [float(i) for i in iso]

                #plan.beams[-1].MCsquareIsocenter = iso

                # convert isocenter in dicom coordinates
                iso[1] = ct.gridSize[1] * ct.spacing[1] - iso[1]
                iso[0] = iso[0] + ct.angles[0] - ct.spacing[0] / 2
                iso[1] = iso[1] + ct.angles[1] - ct.spacing[1] / 2
                iso[2] = iso[2] + ct.angles[2] - ct.spacing[2] / 2
                plan.beams[-1].isocenterPosition = iso

            elif line == "###RangeShifterID":
                plan.beams[-1].rangeShifter.ID = f.readline().replace('\r', '').replace('\n', '').replace('\t', '')

            elif line == "###RangeShifterType":
                plan.beams[-1].rangeShifter.ID = f.readline().replace('\r', '').replace('\n', '').replace('\t', '')

            elif line == "####ControlPointIndex":
                plan.beams[-1]._layers.append(PlanIonLayer())
                plan.beams[-1].layers[-1].seriesInstanceUID = plan.seriesInstanceUID
                line = f.readline()

            elif line == "####CumulativeMetersetWeight":
                plan.beams[-1].layers[-1].meterset = float(f.readline())

            elif line == "####Energy(MeV)":
                plan.beams[-1].layers[-1].nominalEnergy = float(f.readline())

            elif line == "####RangeShifterSetting":
                plan.beams[-1].layers[-1].rangeShifterSettings = f.readline().replace('\r', '').replace('\n',
                                                                                                       '').replace('\t',
                                                                                                                   '')

            elif line == "####IsocenterToRangeShifterDistance":
                plan.beams[-1].layers[-1].rangeShifterSettings.isocenterToRangeShifterDistance = float(f.readline())

            elif line == "####RangeShifterWaterEquivalentThickness":
                plan.beams[-1].layers[-1].rangeShifterSettings.rangeShifterWaterEquivalentThickness = float(f.readline())

            elif line == "####NbOfScannedSpots":
                numSpots = int(f.readline())
                plan.numberOfSpots += numSpots

            elif line == "####XYWeight":
                for s in range(numSpots):
                    data = f.readline().replace('\r', '').replace('\n', '').replace('\t', '').split()
                    plan.beams[-1].layers[-1]._x.append(float(data[0]))
                    plan.beams[-1].layers[-1]._y.append(float(data[1]))
                    #plan.beams[-1].layers[-1].meterset.append(float(data[2]))
                    plan.beams[-1].layers[-1]._weights.append(float(data[2]))

            elif line == "####XYWeightTime":
                for s in range(numSpots):
                    data = f.readline().replace('\r', '').replace('\n', '').replace('\t', '').split()
                    plan.beams[-1].layers[-1]._x.append(float(data[0]))
                    plan.beams[-1].layers[-1]._y.append(float(data[1]))
                    #plan.beams[-1].layers[-1].meterset.append(float(data[2]))
                    plan.beams[-1].layers[-1]._weights.append(float(data[2]))
                    plan.beams[-1].layers[-1]._timings.append(float(data[3]))

            line = f.readline()

    # plan.Beams[-1].Layers[-1].RangeShifterSetting = 'OUT'
    # plan.Beams[-1].Layers[-1].IsocenterToRangeShifterDistance = 0.0
    # plan.Beams[-1].Layers[-1].RangeShifterWaterEquivalentThickness = 0.0
    # plan.Beams[-1].Layers[-1].ReferencedRangeShifterNumber = 0

    # plan.Beams[-1].RangeShifter = "none"
    # plan.NumberOfSpots = ""
    plan.isLoaded = 1

    return plan


def updateWeightsFromPlanPencil(ct: CTImage, initialPlan: RTPlan, file_path, bdl):
    # read PlanPencil generated by MCsquare
    PlanPencil = readMCsquarePlan(ct, file_path)

    # update weight of initial plan with those from PlanPencil
    initialPlan.deliveredProtons = 0
    initialPlan.meterset = PlanPencil.meterset
    for b in range(len(PlanPencil.beams)):
        initialPlan.beams[b].meterset = PlanPencil.beams[b].meterset
        for l in range(len(PlanPencil.beams[b].layers)):
            initialPlan.beams[b].layers[l].meterset = PlanPencil.beams[b].layers[l].meterset
            initialPlan.beams[b].layers[l].spotWeights = PlanPencil.beams[b].layers[l].spotWeights
            if bdl.isLoaded:
                initialPlan.deliveredProtons += sum(initialPlan.beams[b].layers[l].spotWeights) * np.interp(
                    initialPlan.beams[b].layers[l].nominalEnergy, bdl.NominalEnergy, bdl.ProtonsMU)
            else:
                initialPlan.deliveredProtons += bdl.computeMU2Protons(initialPlan.beams[b].layers[l].nominalEnergy)


def writeCT(ct: CTImage, filtePath, overwriteOutsideROI=None):
    # Convert data for compatibility with MCsquare
    # These transformations may be modified in a future version
    image = ct.copy()

    # Crop CT image with contour
    if overwriteOutsideROI is not None:
        print(f'Cropping CT around {overwriteOutsideROI.name}')
        contour_mask = overwriteOutsideROI.getBinaryMask(image.origin, image.gridSize, image.spacing)
        image.imageArray[contour_mask.imageArray.astype(bool) == False] = -1024

    # TODO: cropCTContour:
    # ctCropped = CTImage.fromImage3D(ct)
    # box = crop3D.getBoxAroundROI(cropCTContour)
    # crop3D.crop3DDataAroundBox(ctCropped, box)

    image.imageArray = np.flip(image.imageArray, 0)
    image.imageArray = np.flip(image.imageArray, 1)

    exportImageMHD(filtePath, image)


def writeCTCalibrationAndBDL(calibration: AbstractCTCalibration, scannerPath, materialPath, bdl: BDL, bdlFileName):
    _writeCTCalibration(calibration, scannerPath, materialPath)

    materials = MCsquareMaterial.getMaterialList(materialPath)
    matNames = [mat["name"] for mat in materials]

    with open(os.path.join(materialPath, 'list.dat'), "a") as listFile:
        for rangeShifter in bdl.RangeShifters:
            rangeShifter.material.write(materialPath, matNames)
            listFile.write(str(len(materials) + 1) + ' ' + rangeShifter.material.name)

    materials = MCsquareMaterial.getMaterialList(materialPath)

    _writeBDL(bdl, bdlFileName, materials)


def _writeCTCalibration(calibration: AbstractCTCalibration, scannerPath, materialPath):
    if not isinstance(calibration, MCsquareCTCalibration):
        calibration = MCsquareCTCalibration.fromCTCalibration(calibration)

    calibration.write(scannerPath, materialPath)


def writeConfig(config: MCsquareConfig, file_path):
    fid = open(file_path, 'w')
    fid.write(config.mcsquareFormatted())
    fid.close()


def readBDL(path, materialsPath='default') -> BDL:
    bdl = BDL()

    materialList = MCsquareMaterial.getMaterialList()

    with open(path, 'r') as fid:
        # verify BDL format
        line = fid.readline()
        fid.seek(0)
        if not "--UPenn beam model (double gaussian)--" in line and not "--Lookup table BDL format--" in line:
            fid.close()
            raise IOError("BDL format not supported")

        line_num = -1
        readNIDist = False
        smx = False
        smy = False
        for line in fid:
            line_num += 1

            # remove comments
            if line[0] == '#': continue
            line = line.split('#')[0]

            if "Nozzle exit to Isocenter distance" in line:
                readNIDist = True
                continue
            if readNIDist:
                line = line.split()
                bdl.nozzle_isocenter = float(line[0])
                readNIDist = False
                continue

            if "SMX" in line:
                smx = True
                continue
            if smx:
                line = line.split()
                bdl.smx = float(line[0])
                smx = False
                continue

            if "SMY" in line:
                smy = True
                continue
            if smy:
                line = line.split()
                bdl.smy = float(line[0])
                smy = False
                continue

            # find begining of the BDL table in the file
            if ("NominalEnergy" in line): table_line = line_num + 1

            # parse range shifter data
            if ("Range Shifter parameters" in line):
                RS = RangeShifter()
                bdl.RangeShifters.append(RS)

            if ("RS_ID" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                bdl.RangeShifters[-1].ID = value

            if ("RS_type" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                bdl.RangeShifters[-1].type = value.lower()

            if ("RS_material" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')

                material = MCsquareMolecule()
                material.load(int(value), materialsPath)

                bdl.RangeShifters[-1].material = material

            if ("RS_density" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                bdl.RangeShifters[-1].density = float(value)

            if ("RS_WET" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                bdl.RangeShifters[-1].WET = float(value)

    # parse BDL table
    BDL_table = np.loadtxt(path, skiprows=table_line)

    bdl.NominalEnergy = BDL_table[:, 0]
    bdl.MeanEnergy = BDL_table[:, 1]
    bdl.EnergySpread = BDL_table[:, 2]
    bdl.ProtonsMU = BDL_table[:, 3]
    bdl.Weight1 = BDL_table[:, 4]
    bdl.SpotSize1x = BDL_table[:, 5]
    bdl.Divergence1x = BDL_table[:, 6]
    bdl.Correlation1x = BDL_table[:, 7]
    bdl.SpotSize1y = BDL_table[:, 8]
    bdl.Divergence1y = BDL_table[:, 9]
    bdl.Correlation1y = BDL_table[:, 10]
    bdl.Weight2 = BDL_table[:, 11]
    bdl.SpotSize2x = BDL_table[:, 12]
    bdl.Divergence2x = BDL_table[:, 13]
    bdl.Correlation2x = BDL_table[:, 14]
    bdl.SpotSize2y = BDL_table[:, 15]
    bdl.Divergence2y = BDL_table[:, 16]
    bdl.Correlation2y = BDL_table[:, 17]

    return bdl


def _writeBDL(bdl: BDL, fileName, materials):
    with open(fileName, 'w') as f:
        f.write(bdl.mcsquareFormatted(materials))


def writePlan(plan: RTPlan, file_path, CT: CTImage, bdl: BDL):
    DestFolder, DestFile = os.path.split(file_path)
    FileName, FileExtension = os.path.splitext(DestFile)

    # export plan
    fid = open(file_path, 'w')
    fid.write("#TREATMENT-PLAN-DESCRIPTION\n")
    fid.write("#PlanName\n")
    fid.write("%s\n" % FileName)
    fid.write("#NumberOfFractions\n")
    fid.write("%d\n" % plan.numberOfFractionsPlanned)
    fid.write("##FractionID\n")
    fid.write("1\n")
    fid.write("##NumberOfFields\n")
    fid.write("%d\n" % len(plan))
    for i in range(len(plan)):
        fid.write("###FieldsID\n")
        fid.write("%d\n" % (i + 1))
    fid.write("#TotalMetersetWeightOfAllFields\n")
    fid.write("%f\n" % plan.meterset)

    FinalCumulativeMeterSetWeight = 0.
    for i, beam in enumerate(plan):
        CumulativeMetersetWeight = 0.

        fid.write("\n")
        fid.write("#FIELD-DESCRIPTION\n")
        fid.write("###FieldID\n")
        fid.write("%d\n" % (i + 1))
        fid.write("###FinalCumulativeMeterSetWeight\n")
        FinalCumulativeMeterSetWeight += beam.meterset
        fid.write("%f\n" % FinalCumulativeMeterSetWeight)
        fid.write("###GantryAngle\n")
        fid.write("%f\n" % beam.gantryAngle)
        fid.write("###PatientSupportAngle\n")
        fid.write("%f\n" % beam.patientSupportAngle)
        fid.write("###IsocenterPosition\n")
        fid.write(
            "%f\t %f\t %f\n" % _dicomIsocenterToMCsquare(beam.isocenterPosition, CT.origin, CT.spacing, CT.gridSize))

        if not (beam.rangeShifter is None):
            if beam.rangeShifter.ID not in [rs.ID for rs in bdl.RangeShifters]:
                raise Exception('Range shifter in plan not in BDL')
            else:
                fid.write("###RangeShifterID\n")
                fid.write("%s\n" % beam.rangeShifter.ID)
                fid.write("###RangeShifterType\n")
                fid.write("binary\n")

        fid.write("###NumberOfControlPoints\n")
        fid.write("%d\n" % len(beam))
        fid.write("\n")
        fid.write("#SPOTS-DESCRIPTION\n")

        for j, layer in enumerate(beam):
            fid.write("####ControlPointIndex\n")
            fid.write("%d\n" % (j + 1))
            fid.write("####SpotTunnedID\n")
            fid.write("1\n")
            fid.write("####CumulativeMetersetWeight\n")
            CumulativeMetersetWeight += layer.meterset
            fid.write("%f\n" % CumulativeMetersetWeight)
            fid.write("####Energy (MeV)\n")
            fid.write("%f\n" % layer.nominalEnergy)

            if not (beam.rangeShifter is None) and (beam.rangeShifter.type == "binary"):
                fid.write("####RangeShifterSetting\n")
                fid.write("%s\n" % layer.rangeShifterSettings.rangeShifterSetting)
                fid.write("####IsocenterToRangeShifterDistance\n")
                fid.write("%f\n" % layer.rangeShifterSettings.isocenterToRangeShifterDistance)
                fid.write("####RangeShifterWaterEquivalentThickness\n")
                if (layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness is None):
                    # fid.write("%f\n" % beam.rangeShifter.WET)
                    RS_index = [rs.ID for rs in bdl.RangeShifters]
                    ID = RS_index.index(beam.rangeShifter.ID)
                    fid.write("%f\n" % bdl.RangeShifters[ID].WET)
                else:
                    print('layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness',
                          layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness)
                    print('type(layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness)',
                          type(layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness))
                    fid.write("%f\n" % layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness)

            fid.write("####NbOfScannedSpots\n")
            fid.write("%d\n" % len(layer))

            fid.write("####X Y Weight\n")
            for i, xy in enumerate(layer.spotXY):
                fid.write("%f %f %f\n" % (xy[0], xy[1], layer.spotWeights[i]))

    fid.close()


def writeContours(contour: ROIMask, folder_path):
    # Convert data for compatibility with MCsquare
    # These transformations may be modified in a future version
    #contour.imageArray = np.flip(contour.imageArray, (0,1))
    contour.imageArray = np.flip(contour.imageArray, 0)
    contour.imageArray = np.flip(contour.imageArray, 1)

    if not os.path.isdir(folder_path):
        os.mkdir(folder_path)
    contourName = contour.name.replace(' ', '_').replace('-', '_').replace('.', '_').replace('/', '_')
    file_path = os.path.join(folder_path, contourName + ".mhd")
    mhdIO.exportImageMHD(file_path, contour)

def writeObjectives(objectives: ObjectivesList, file_path):
    targetName = objectives.targetName.replace(' ', '_').replace('-', '_').replace('.', '_').replace('/', '_')

    print("Write plan objectives: " + file_path)
    fid = open(file_path, 'w');
    fid.write("# List of objectives for treatment plan optimization\n\n")
    fid.write("Target_ROIName:\n" + targetName + "\n\n")
    fid.write("Dose_prescription:\n" + str(objectives.targetPrescription) + "\n\n")
    fid.write("Number_of_objectives:\n" + str(len(objectives.fidObjList)) + "\n\n")

    for objective in objectives.fidObjList:
        contourName = objective.roiName.replace(' ', '_').replace('-', '_').replace('.', '_').replace('/', '_')

        fid.write("Objective_parameters:\n")
        fid.write("ROIName = " + contourName + "\n")
        fid.write("Weight = " + str(objective.weight) + "\n")
        fid.write(objective.metric + " " + objective.condition + " " + str(objective.limitValue) + "\n")
        fid.write("\n")

    fid.close()


def _dicomIsocenterToMCsquare(isocenter, ctImagePositionPatient, ctPixelSpacing, ctGridSize):
    MCsquareIsocenter0 = isocenter[0] - ctImagePositionPatient[0] + ctPixelSpacing[
        0] / 2  # change coordinates (origin is now in the corner of the image)
    MCsquareIsocenter1 = isocenter[1] - ctImagePositionPatient[1] + ctPixelSpacing[1] / 2
    MCsquareIsocenter2 = isocenter[2] - ctImagePositionPatient[2] + ctPixelSpacing[2] / 2

    MCsquareIsocenter1 = ctGridSize[1] * ctPixelSpacing[1] - MCsquareIsocenter1  # flip coordinates in Y direction

    return (MCsquareIsocenter0, MCsquareIsocenter1, MCsquareIsocenter2)


def writeBin(destFolder):
    import Core.Processing.DoseCalculation.MCsquare as MCsquareModule
    mcsquarePath = str(MCsquareModule.__path__[0])

    if (platform.system() == "Linux"):
        source_path = os.path.join(mcsquarePath, "MCsquare")
        destination_path = os.path.join(destFolder, "MCsquare")
        shutil.copyfile(source_path, destination_path)  # copy file
        shutil.copymode(source_path, destination_path)  # copy permissions

        source_path = os.path.join(mcsquarePath, "MCsquare_linux")
        destination_path = os.path.join(destFolder, "MCsquare_linux")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

        source_path = os.path.join(mcsquarePath, "MCsquare_linux_avx")
        destination_path = os.path.join(destFolder, "MCsquare_linux_avx")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

        source_path = os.path.join(mcsquarePath, "MCsquare_linux_avx2")
        destination_path = os.path.join(destFolder, "MCsquare_linux_avx2")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

        source_path = os.path.join(mcsquarePath, "MCsquare_linux_avx512")
        destination_path = os.path.join(destFolder, "MCsquare_linux_avx512")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

        source_path = os.path.join(mcsquarePath, "MCsquare_linux_sse4")
        destination_path = os.path.join(destFolder, "MCsquare_linux_sse4")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

        source_path = os.path.join(mcsquarePath, "MCsquare_opti")
        destination_path = os.path.join(destFolder, "MCsquare_opti")
        shutil.copyfile(source_path, destination_path)  # copy file
        shutil.copymode(source_path, destination_path)  # copy permissions

        source_path = os.path.join(mcsquarePath, "MCsquare_opti_linux")
        destination_path = os.path.join(destFolder, "MCsquare_opti_linux")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

        source_path = os.path.join(mcsquarePath, "MCsquare_opti_linux_avx")
        destination_path = os.path.join(destFolder, "MCsquare_opti_linux_avx")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

        source_path = os.path.join(mcsquarePath, "MCsquare_opti_linux_avx2")
        destination_path = os.path.join(destFolder, "MCsquare_opti_linux_avx2")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

        source_path = os.path.join(mcsquarePath, "MCsquare_opti_linux_avx512")
        destination_path = os.path.join(destFolder, "MCsquare_opti_linux_avx512")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

        source_path = os.path.join(mcsquarePath, "MCsquare_opti_linux_sse4")
        destination_path = os.path.join(destFolder, "MCsquare_opti_linux_sse4")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

    elif (platform.system() == "Windows"):
        source_path = os.path.join(mcsquarePath, "MCsquare_win.bat")
        destination_path = os.path.join(destFolder, "MCsquare_win.bat")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

        source_path = os.path.join(mcsquarePath, "MCsquare_win.exe")
        destination_path = os.path.join(destFolder, "MCsquare_win.exe")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

        source_path = os.path.join(mcsquarePath, "libiomp5md.dll")
        destination_path = os.path.join(destFolder, "libiomp5md.dll")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

    else:
        raise Exception("Error: Operating system " + platform.system() + " is not supported by MCsquare.")


class MCsquareIOTestCase(unittest.TestCase):
    def testWrite(self):
        from Core.Data.Plan.planIonBeam import PlanIonBeam
        from Core.Data.Plan.planIonLayer import PlanIonLayer

        import Core.Processing.DoseCalculation.MCsquare.BDL as BDLModule

        bdl = readBDL(os.path.join(str(BDLModule.__path__[0]), 'BDL_default_DN_RangeShifter.txt'))

        plan = RTPlan()
        beam = PlanIonBeam()
        layer = PlanIonLayer(nominalEnergy=100.)
        layer.appendSpot(0, 0, 1)
        layer.appendSpot(0, 1, 2)

        beam.appendLayer(layer)

        plan.appendBeam(beam)

        writePlan(plan, 'plan_test.txt', CTImage(), bdl)
