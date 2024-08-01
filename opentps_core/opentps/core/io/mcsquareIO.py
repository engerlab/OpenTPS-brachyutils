import os
import platform
import shutil
import struct
import time
import logging
import unittest
from typing import Optional, Sequence, Iterable

import numpy as np
import pydicom
import scipy.sparse as sp
from scipy.sparse import csc_matrix

from opentps.core.data.CTCalibrations.MCsquareCalibration import MCsquareCTCalibration
from opentps.core.data.CTCalibrations.MCsquareCalibration import MCsquareMaterial
from opentps.core.data.CTCalibrations.MCsquareCalibration import MCsquareMolecule
from opentps.core.data.CTCalibrations import AbstractCTCalibration
from opentps.core.data.images import CTImage
from opentps.core.data.images import DoseImage
from opentps.core.data.images import ROIMask
from opentps.core.data.MCsquare import BDL
from opentps.core.data.MCsquare import MCsquareConfig
from opentps.core.data.plan import ObjectivesList
from opentps.core.data.plan import PlanIonBeam
from opentps.core.data.plan import PlanIonLayer
from opentps.core.data.plan import RangeShifter
from opentps.core.data.plan import RTPlan
from opentps.core.data import SparseBeamlets
from opentps.core.io import mhdIO
from opentps.core.io.mhdIO import exportImageMHD, importImageMHD

from opentps.core.data.images import Image3D


logger = logging.getLogger(__name__)

def readBeamlets(file_path, beamletRescaling:Sequence[float], origin, roi: Optional[ROIMask] = None):
    """
    Read sparse beamlets from a file and return a beamlet dose image

    Parameters
    ----------
    file_path : str
        The path to the sparse beamlets file
    beamletRescaling : Sequence[float]
        The beamlet dose image grid rescaling factors [r,s,t]
    origin : Sequence[float]
        The origin of the dose grid [x,y,z]
    roi : Optional[ROIMask], optional
        The ROI mask, by default None

    Returns
    -------
    BeamletDose
        The beamlets dose image

    """
    if (not file_path.endswith('.txt')):
        raise NameError('File ', file_path, ' is not a valid sparse matrix header')

    # Read sparse beamlets header file
    logger.info('Read sparse beamlets: {}'.format(file_path))
    header = _read_sparse_header(file_path)
    if 'Beamlet' not in header["SimulationMode"]:
        raise ValueError('Not a beamlet file')

    # Read sparse beamlets binary file
    logger.info('Read binary file: {}'.format(file_path))
    sparseBeamlets = _read_sparse_data(header["Binary_file"], header["NbrVoxels"], header["NbrSpots"], roi)

    beamletDose = SparseBeamlets()
    beamletDose.setUnitaryBeamlets(csc_matrix.dot(sparseBeamlets, csc_matrix(np.diag(beamletRescaling), dtype=np.float32)))
    beamletDose.doseOrigin = origin
    beamletDose.doseSpacing = header["VoxelSpacing"]
    beamletDose.doseGridSize = header["ImageSize"]

    return beamletDose


def _read_sparse_header(file_path):
    """
    Read sparse beamlets header file

    Parameters
    ----------
    file_path : str
        The path to the sparse beamlets header file

    Returns
    -------
    header:dict
        The sparse beamlets header
    """
    header = {}

    # Parse file path
    Folder, File = os.path.split(file_path)
    FileName, FileExtension = os.path.splitext(File)
    Header_file = file_path
    header["ImgName"] = FileName
    header["SimulationMode"] = []

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
                    header["SimulationMode"].append(val.strip())
                elif key == 'BinaryFile':
                    header["Binary_file"] = os.path.join(Folder, val.strip())

    return header


def _read_sparse_data(Binary_file, NbrVoxels, NbrSpots, roi:Optional[ROIMask]=None) -> csc_matrix:
    """
    Read sparse beamlets matrix from a sparse beamlets binary file

    Parameters
    ----------
    Binary_file : str
        The path to the sparse beamlets binary file
    NbrVoxels : int
        The number of voxels
    NbrSpots : int
        The number of spots
    roi : Optional[ROIMask], optional
        The ROI mask, by default None

    Returns
    -------
    BeamletMatrix : csc_matrix
        The sparse beamlets matrix

    """
    BeamletMatrix = None

    fid = open(Binary_file, 'rb')

    buffer_size = 5 * NbrVoxels
    col_index = np.zeros((buffer_size), dtype=np.uint32)
    row_index = np.zeros((buffer_size), dtype=np.uint32)
    beamlet_data = np.zeros((buffer_size), dtype=np.float32)
    data_id = 0
    last_stacked_col = -1
    num_unstacked_col = 0

    if not(roi is None) or (roi is list and not(len(roi)==0)):
        if isinstance(roi, ROIMask):
            roi = [roi]
        logger.info("Beamlets are computed on {}".format([contour.name for contour in roi]))
        roiUnion = None
        for contour in roi:
            roiData = np.flip(contour.imageArray,(0,1))
            roiData = np.ndarray.flatten(roiData,'F').astype('bool')
            if roiUnion is None:
                roiUnion = roiData
            else:
                roiUnion = np.logical_or(roiUnion, roiData)
    else:
        roiUnion = np.ones((NbrVoxels, 1)).astype(bool)

    time_start = time.time()

    for spot in range(NbrSpots):
        [NonZeroVoxels] = struct.unpack('I', fid.read(4))
        [BeamID] = struct.unpack('I', fid.read(4))
        [LayerID] = struct.unpack('I', fid.read(4))
        [xcoord] = struct.unpack('<f', fid.read(4))
        [ycoord] = struct.unpack('<f', fid.read(4))

        logger.info("Spot {} : BeamID={} LayerID={} Position=({};{}) NonZeroVoxels={}".format(spot, BeamID, LayerID, xcoord, ycoord, NonZeroVoxels))

        if (NonZeroVoxels == 0):
            num_unstacked_col += 1
            continue

        ReadVoxels = 0
        while (1):
            [NbrContinuousValues] = struct.unpack('I', fid.read(4))
            ReadVoxels += NbrContinuousValues

            [FirstIndex] = struct.unpack('I', fid.read(4))

            for j in range(NbrContinuousValues):
                [temp] = struct.unpack('<f', fid.read(4))

                rowIndexVal = FirstIndex + j
                if roiUnion[rowIndexVal]:
                    beamlet_data[data_id] = temp
                    row_index[data_id] = rowIndexVal
                    col_index[data_id] = spot - last_stacked_col - 1
                    data_id += 1

            if (ReadVoxels >= NonZeroVoxels):
                if spot == 0:
                    BeamletMatrix = sp.csc_matrix(
                        (beamlet_data[:data_id], (row_index[:data_id], col_index[:data_id])), shape=(NbrVoxels, 1),
                        dtype=np.float32)
                    data_id = 0
                    last_stacked_col = spot
                    num_unstacked_col = 0

                    beamlet_data = 0 * beamlet_data
                    row_index = 0 * row_index
                    col_index = 0 * col_index
                elif (data_id > buffer_size - NbrVoxels):
                    A = sp.csc_matrix((beamlet_data[:data_id], (row_index[:data_id], col_index[:data_id])),
                                      shape=(NbrVoxels, num_unstacked_col + 1), dtype=np.float32)
                    data_id = 0
                    BeamletMatrix = sp.hstack([BeamletMatrix, A])
                    last_stacked_col = spot
                    num_unstacked_col = 0

                    beamlet_data = 0 * beamlet_data
                    row_index = 0 * row_index
                    col_index = 0 * col_index
                else:
                    num_unstacked_col += 1

                break

    # stack last cols
    A = sp.csc_matrix((beamlet_data[:data_id], (row_index[:data_id], col_index[:data_id])),
                      shape=(NbrVoxels, num_unstacked_col), dtype=np.float32)
    if BeamletMatrix is None:
        BeamletMatrix = A
    else:
        BeamletMatrix = sp.hstack([BeamletMatrix, A])

    logger.info('Beamlets imported in {} sec'.format(time.time() - time_start))

    _print_memory_usage(BeamletMatrix)

    fid.close()
    return BeamletMatrix


def _print_memory_usage(BeamletMatrix):
    """
    Print memory usage of the sparse beamlets matrix

    Parameters
    ----------
    BeamletMatrix : csc_matrix
        The sparse beamlets matrix
    """
    if BeamletMatrix == []:
        logger.info("Beamlets not loaded")


    else:
        mat_size = BeamletMatrix.data.nbytes + BeamletMatrix.indptr.nbytes + BeamletMatrix.indices.nbytes
        logger.info("Beamlets loaded")
        logger.info("Matrix size: {}".format(BeamletMatrix.shape))
        logger.info("Non-zero values: {}".format(BeamletMatrix.nnz))
        logger.info("data format: {}".format(BeamletMatrix.dtype))
        logger.info("Memory usage: {} GB".format(mat_size / 1024 ** 3))


def readDose(filePath)->DoseImage:
    """
    Read a dose file from MCsquare (MHD format) and give the dose Image

    Parameters
    ----------
    filePath : str
        Path to the dose file

    Returns
    -------
    DoseImage
        The dose image
     """
    doseMHD = readMCsquareMHD(filePath)

    doseImage = DoseImage.fromImage3D(doseMHD)

    return doseImage

def readMCsquareMHD(filePath) -> Image3D:
    """
    Read MHD file from MCsquare and give the 3D image

    Parameters
    ----------
    filePath : str
        Path to the MHD file

    Returns
    -------
    image:Image3D
        The 3D image
    """
    image = importImageMHD(filePath)

    image.origin[0] = image.origin[0] + image.spacing[0]/2
    image.origin[2] = image.origin[2] + image.spacing[2]/2
    image.origin[1] = - image.origin[1] - image.spacing[1] * image.gridSize[1] + image.spacing[1]/2

    # Convert data for compatibility with MCsquare
    # These transformations may be modified in a future version
    image.imageArray = np.flip(image.imageArray, 0)
    image.imageArray = np.flip(image.imageArray, 1)

    return image


def readMCsquarePlan(ct: CTImage, file_path):
    """
    Read a plan file from MCsquare and give the plan

    Parameters
    ----------
    ct : CTImage
        The CT image
    file_path : str
        Path to the plan file

    Returns
    -------
    plan:RTPlan
        The RT plan
    """
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

            elif line == "#FIELD-DESCRIPTION":
                plan._beams.append(PlanIonBeam())
                plan.beams[-1].seriesInstanceUID = plan.seriesInstanceUID

            elif line == "###FieldID" and len(plan.beams) > 0:
                plan.beams[-1].name = f.readline()

            elif line == "###GantryAngle":
                plan.beams[-1].gantryAngle = float(f.readline())

            elif line == "###PatientSupportAngle":
                plan.beams[-1].couchAngle = float(f.readline())

            elif line == "###IsocenterPosition":
                # read isocenter in MCsquare coordinates
                iso = f.readline().replace('\r', '').replace('\n', '').replace('\t', ' ').split()
                iso = [float(i) for i in iso]

                plan.beams[-1].mcsquareIsocenter = iso

                plan.beams[-1].isocenterPosition = _mcsquareToDicom(iso, ct.origin, ct.spacing, ct.gridSize)

            elif line == "###RangeShifterID":
                plan.beams[-1].rangeShifter.ID = f.readline().replace('\r', '').replace('\n', '').replace('\t', '')

            elif line == "###RangeShifterType":
                plan.beams[-1].rangeShifter.ID = f.readline().replace('\r', '').replace('\n', '').replace('\t', '')

            elif line == "####ControlPointIndex":
                plan.beams[-1]._layers.append(PlanIonLayer())
                plan.beams[-1].layers[-1].seriesInstanceUID = plan.seriesInstanceUID
                line = f.readline()

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

            elif line == "####XYWeight":
                for s in range(numSpots):
                    data = f.readline().replace('\r', '').replace('\n', '').replace('\t', '').split()
                    plan.beams[-1].layers[-1]._appendSingleSpot(float(data[0]), float(data[1]), float(data[2]))


            elif line == "####XYWeightTime":
                for s in range(numSpots):
                    data = f.readline().replace('\r', '').replace('\n', '').replace('\t', '').split()
                    plan.beams[-1].layers[-1]._appendSingleSpot(float(data[0]), float(data[1]), float(data[2]),
                                                                float(data[3]))

            line = f.readline()
    plan.isLoaded = 1

    return plan


def updateWeightsFromPlanPencil(ct: CTImage, initialPlan: RTPlan, file_path, bdl):
    """
    Update the weights of the initial plan with those from PlanPencil

    Parameters
    ----------
    ct : CTImage
        The CT image
    initialPlan : RTPlan
        The initial plan
    file_path : str
        Path to the MCsquare Plan file (PlanPencil)
    """
    # read PlanPencil generated by MCsquare
    PlanPencil = readMCsquarePlan(ct, file_path)

    # update weight of initial plan with those from PlanPencil
    initialPlan.deliveredProtons = 0
    for b in range(len(PlanPencil.beams)):
        for l in range(len(PlanPencil.beams[b].layers)):
            initialPlan.beams[b].layers[l].spotMUs = PlanPencil.beams[b].layers[l].spotMUs

def writeCT(ct: CTImage, filtePath, overwriteOutsideROI=None):
    """
    Write a CT image to a file

    Parameters
    ----------
    ct : CTImage
        The CT image
    filtePath : str
        The file path
    overwriteOutsideROI : ROI, optional
        The ROI to use for cropping the CT image
    """
    # Convert data for compatibility with MCsquare
    # These transformations may be modified in a future version
    image = ct.copy()

    # Crop CT image with contour
    if overwriteOutsideROI is not None:
        logger.info(f'Cropping CT around {overwriteOutsideROI.name}')
        contour_mask = overwriteOutsideROI.getBinaryMask(image.origin, image.gridSize, image.spacing)
        image.imageArray[contour_mask.imageArray.astype(bool) == False] = -1024

    # TODO: cropCTContour:
    # ctCropped = CTImage.fromImage3D(ct)
    # box = crop3D.getBoxAroundROI(cropCTContour)
    # crop3D.crop3DDataAroundBox(ctCropped, box)

    image.imageArray = np.flip(image.imageArray, 0)
    image.imageArray = np.flip(image.imageArray, 1)

    # DICOM to MCsquare coordinates
    image.origin[0] = image.origin[0] - image.spacing[0] / 2.0
    image.origin[2] = image.origin[2] - image.spacing[2] / 2.0
    image.origin[1] = -image.origin[1] - image.spacing[1] * \
                                    image.gridSize[1] + \
                                    image.spacing[1] / 2.0 #  inversion of Y, which is flipped in MCsquare

    exportImageMHD(filtePath, image)


def writeCTCalibrationAndBDL(calibration: AbstractCTCalibration, scannerPath, materialPath, bdl: BDL, bdlFileName):
    """
    Write a CT calibration and a BDL to a file

    Parameters
    ----------
    calibration : AbstractCTCalibration
        The CT calibration
    scannerPath : str
        The path to the scanner
    materialPath : str
        The path to the material
    bdl : BDL
        The BDL
    bdlFileName : str
        The BDL file name
    """
    _writeCTCalibration(calibration, scannerPath, materialPath)

    materials = MCsquareMaterial.getMaterialList(materialPath)
    matNames = [mat["name"] for mat in materials]

    with open(os.path.join(materialPath, 'list.dat'), "a") as listFile:
        for rangeShifter in bdl.rangeShifters:
            rangeShifter.material.write(materialPath, matNames)
            listFile.write(str(len(materials) + 1) + ' ' + rangeShifter.material.name)

    materials = MCsquareMaterial.getMaterialList(materialPath)

    _writeBDL(bdl, bdlFileName, materials)


def _writeCTCalibration(calibration: AbstractCTCalibration, scannerPath, materialPath):
    """
    Write a CT calibration to a file

    Parameters
    ----------
    calibration : AbstractCTCalibration
        The CT calibration
    scannerPath : str
        The path to the scanner
    materialPath : str
        The path to the material
    """
    if not isinstance(calibration, MCsquareCTCalibration):
        calibration = MCsquareCTCalibration.fromCTCalibration(calibration)

    calibration.write(scannerPath, materialPath)


def writeConfig(config: MCsquareConfig, file_path):
    """
    Write a MCsquare configuration to a file

    Parameters
    ----------
    config : MCsquareConfig
        The MCsquare configuration
    file_path : str
        The file path
    """
    fid = open(file_path, 'w',encoding="utf-8")
    fid.write(config.mcsquareFormatted())
    fid.close()


def readBDL(path, materialsPath='default') -> BDL:
    """
    Read a BDL file

    Parameters
    ----------
    path : str
        The file path
    materialsPath : str, optional
        The path to the materials

    Returns
    -------
    bdl:BDL
        The BDL object to be used
    """
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
                bdl.rangeShifters.append(RS)

            if ("RS_ID" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                bdl.rangeShifters[-1].ID = value

            if ("RS_type" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                bdl.rangeShifters[-1].type = value.lower()

            if ("RS_material" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')

                material = MCsquareMolecule.load(int(value), materialsPath)

                bdl.rangeShifters[-1].material = material

            if ("RS_density" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                bdl.rangeShifters[-1].density = float(value)

            if ("RS_WET" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                bdl.rangeShifters[-1].WET = float(value)

    # parse BDL table
    BDL_table = np.atleast_2d(np.loadtxt(path, skiprows=table_line))

    bdl.nominalEnergy = BDL_table[:, 0]
    bdl.meanEnergy = BDL_table[:, 1]
    bdl.energySpread = BDL_table[:, 2]
    bdl.protonsMU = BDL_table[:, 3]
    bdl.weight1 = BDL_table[:, 4]
    bdl.spotSize1x = BDL_table[:, 5]
    bdl.divergence1x = BDL_table[:, 6]
    bdl.correlation1x = BDL_table[:, 7]
    bdl.spotSize1y = BDL_table[:, 8]
    bdl.divergence1y = BDL_table[:, 9]
    bdl.correlation1y = BDL_table[:, 10]
    bdl.weight2 = BDL_table[:, 11]
    bdl.spotSize2x = BDL_table[:, 12]
    bdl.divergence2x = BDL_table[:, 13]
    bdl.correlation2x = BDL_table[:, 14]
    bdl.spotSize2y = BDL_table[:, 15]
    bdl.divergence2y = BDL_table[:, 16]
    bdl.correlation2y = BDL_table[:, 17]

    bdl.isLoaded = 1

    return bdl


def _writeBDL(bdl: BDL, fileName, materials):
    """
    Write a BDL file

    Parameters
    ----------
    bdl : BDL
        The BDL object to store
    fileName : str
        The file path
    materials : list
        The list of materials
    """
    with open(fileName, 'w') as f:
        f.write(bdl.mcsquareFormatted(materials))


def writePlan(plan: RTPlan, file_path, CT: CTImage, bdl: BDL):
    """
    Write a treatement plan file

    Parameters
    ----------
    plan : RTPlan
        The plan to write
    file_path : str
        The file path to store the plan
    CT : CTImage
        The CT image
    bdl : BDL
        The BDL object
    """
    if (plan.scanMode != "MODULATED"):
        logger.error("Error: cannot simulate this treatment modality. Please convert the plan to PBS delivery mode.")
        return

    DestFolder, DestFile = os.path.split(file_path)
    FileName, FileExtension = os.path.splitext(DestFile)

    # export plan
    logger.info("Write plan: {}".format(file_path))

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
        fid.write("%f\n" % beam.couchAngle)
        fid.write("###IsocenterPosition\n")
        fid.write(
            "%f\t %f\t %f\n" % _dicomIsocenterToMCsquare(beam.isocenterPosition, CT.origin, CT.spacing, CT.gridSize))

        if not (beam.rangeShifter is None):
            print([rs.ID for rs in bdl.rangeShifters])
            if beam.rangeShifter.ID not in [rs.ID for rs in bdl.rangeShifters]:
                raise Exception('Range shifter with ID ' + beam.rangeShifter.ID + ' in plan not in BDL')
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
                    RS_index = [rs.ID for rs in bdl.rangeShifters]
                    ID = RS_index.index(beam.rangeShifter.ID)
                    fid.write("%f\n" % bdl.rangeShifters[ID].WET)
                else:
                    fid.write("%f\n" % layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness)

            fid.write("####NbOfScannedSpots\n")
            fid.write("%d\n" % len(layer))

            fid.write("####X Y Weight\n")
            for i, xy in enumerate(layer.spotXY):
                fid.write("%f %f %f\n" % (xy[0], xy[1], layer.spotMUs[i]))

    fid.close()


def writeContours(contour: ROIMask, folder_path):
    """
    Write a MHD contour file into a given folder

    Parameters
    ----------
    contour : ROIMask
        The contour to write
    folder_path : str
        The path to the folder where the contour will be written
    """
    # Convert data for compatibility with MCsquare
    # These transformations may be modified in a future version
    # contour.imageArray = np.flip(contour.imageArray, (0,1))
    contourCopy = contour.copy()
    contourCopy.imageArray = np.flip(contourCopy.imageArray, 0)
    contourCopy.imageArray = np.flip(contourCopy.imageArray, 1)

    if not os.path.isdir(folder_path):
        os.mkdir(folder_path)
    contourCopy.name = contour.name
    contourName = contourCopy.name.replace(' ', '_').replace('-', '_').replace('.', '_').replace('/', '_')
    file_path = os.path.join(folder_path, contourName + ".mhd")
    mhdIO.exportImageMHD(file_path, contourCopy)

def writeObjectives(objectives: ObjectivesList, file_path):
    """
    Write Objectives file at the given path

    Parameters
    ----------
    objectives : ObjectivesList
        The objectives list to write
    file_path : str
        The path to the file where the objectives will be written
    """
    if isinstance(objectives.targetName,Iterable):
        targetName = objectives.targetName[0].replace(' ', '_').replace('-', '_').replace('.', '_').replace('/', '_')
    else:
        targetName = objectives.targetName[0].replace(' ', '_').replace('-', '_').replace('.', '_').replace('/', '_')

    logger.info("Write plan objectives: {}".format(file_path))
    fid = open(file_path, 'w');
    fid.write("# List of objectives for treatment plan planOptimization\n\n")
    fid.write("Target_ROIName:\n" + targetName + "\n\n")
    if isinstance(objectives.targetPrescription,Iterable):
        fid.write("Dose_prescription:\n" + str(objectives.targetPrescription[0]) + "\n\n")
    else:
        fid.write("Dose_prescription:\n" + str(objectives.targetPrescription) + "\n\n")
    fid.write("Number_of_objectives:\n" + str(len(objectives.fidObjList)) + "\n\n")

    for objective in objectives.fidObjList:
        contourName = objective.roiName.replace(' ', '_').replace('-', '_').replace('.', '_').replace('/', '_')

        fid.write("Objective_parameters:\n")
        fid.write("ROIName = " + contourName + "\n")
        fid.write("Weight = " + str(objective.weight) + "\n")
        if objective.metric == objective.Metrics.DMIN:
            metric = "Dmin"
            condition = ">"
        elif objective.metric == objective.Metrics.DMAX:
            metric = "Dmax"
            condition = "<"
        elif objective.metric == objective.Metrics.DMEAN:
            metric = "Dmean"
            condition = "<"
        else:
            logger.error("Error: objective metric {} is not supported.".format(metric))
        fid.write(metric + " " + condition + " " + str(objective.limitValue) + "\n")
        fid.write("\n")

    fid.close()


def _dicomIsocenterToMCsquare(isocenter, ctImagePositionPatient, ctPixelSpacing, ctGridSize):
    """
    Convert DICOM isocenter coordinates to MCsquare coordinates

    Parameters
    ----------
    isocenter : tuple
        DICOM isocenter coordinates
    ctImagePositionPatient : tuple
        The image position of the patient in the DICOM file
    ctPixelSpacing : tuple
        DICOM PixelSpacing value
    ctGridSize : tuple
        DICOM grid size value

    Returns
    -------
    tuple
        MCsquare isocenter coordinates in [x,y,z] format
    """
    MCsquareIsocenter0 = isocenter[0] - ctImagePositionPatient[0] + ctPixelSpacing[
        0] / 2  # change coordinates (origin is now in the corner of the image)
    MCsquareIsocenter1 = isocenter[1] - ctImagePositionPatient[1] + ctPixelSpacing[1] / 2
    MCsquareIsocenter2 = isocenter[2] - ctImagePositionPatient[2] + ctPixelSpacing[2] / 2

    MCsquareIsocenter1 = ctGridSize[1] * ctPixelSpacing[1] - MCsquareIsocenter1  # flip coordinates in Y direction

    return (MCsquareIsocenter0, MCsquareIsocenter1, MCsquareIsocenter2)

def _mcsquareToDicom(isocenter, ctImagePositionPatient, ctPixelSpacing, ctGridSize):
    """
    Convert MCsquare isocenter coordinates to DICOM coordinates

    Parameters
    ----------
    isocenter : tuple
        MCsquare isocenter coordinates
    ctImagePositionPatient : tuple
        The image position of the patient in the DICOM file
    ctPixelSpacing : tuple
        DICOM PixelSpacing value
    ctGridSize : tuple
        DICOM grid size value

    Returns
    -------
    tuple
        DICOM isocenter coordinates in [x,y,z] format
    """
    MCsquareIsocenter0 = isocenter[0] + ctImagePositionPatient[0] - ctPixelSpacing[0] / 2  # change coordinates (origin is now in the corner of the image)
    MCsquareIsocenter1 = ctGridSize[1] * ctPixelSpacing[1] - isocenter[1]  # flip coordinates in Y direction
    MCsquareIsocenter1 = MCsquareIsocenter1 + ctImagePositionPatient[1] + ctPixelSpacing[1] / 2
    MCsquareIsocenter2 = isocenter[2] + ctImagePositionPatient[2] - ctPixelSpacing[2] / 2


    return (MCsquareIsocenter0, MCsquareIsocenter1, MCsquareIsocenter2)



def writeBin(destFolder):
    """
    Write MCsquare binaries to the given folder

    Parameters
    ----------
    destFolder : str
        The folder where the binaries will be written
    """
    import opentps.core.processing.doseCalculation.MCsquare as MCsquareModule
    mcsquarePath = str(MCsquareModule.__path__[0])

    if (platform.system() == "Linux"):
        source_path = os.path.join(mcsquarePath, "libMCsquare.so")
        destination_path = os.path.join(destFolder, "libMCsquare.so")
        shutil.copyfile(source_path, destination_path)  # copy file
        shutil.copymode(source_path, destination_path)  # copy permissions

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

        source_path = os.path.join(mcsquarePath, "MCsquare_opti_win.bat")
        destination_path = os.path.join(destFolder, "MCsquare_opti_win.bat")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

        source_path = os.path.join(mcsquarePath, "MCsquare_win.exe")
        destination_path = os.path.join(destFolder, "MCsquare_win.exe")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

        source_path = os.path.join(mcsquarePath, "MCsquare_opti_win.exe")
        destination_path = os.path.join(destFolder, "MCsquare_opti_win.exe")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)


        source_path = os.path.join(mcsquarePath, "libiomp5md.dll")
        destination_path = os.path.join(destFolder, "libiomp5md.dll")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

    elif (platform.system() == "Darwin"):

        source_path = os.path.join(mcsquarePath, "MCsquare")
        destination_path = os.path.join(destFolder, "MCsquare")
        shutil.copyfile(source_path, destination_path)  # copy file
        shutil.copymode(source_path, destination_path)  # copy permissions

        source_path = os.path.join(mcsquarePath, "MCsquare_mac")
        destination_path = os.path.join(destFolder, "MCsquare_mac")
        shutil.copyfile(source_path, destination_path)
        shutil.copymode(source_path, destination_path)

    else:
        raise Exception("Error: Operating system " + platform.system() + " is not supported by MCsquare.")


class MCsquareIOTestCase(unittest.TestCase):
    """
    Test case for the MCsquareIO module.
    """
    def testWrite(self):
        """
        Test the write function.
        """
        from opentps.core.data.plan._planIonBeam import PlanIonBeam
        from opentps.core.data.plan._planIonLayer import PlanIonLayer

        import opentps.core.processing.doseCalculation.MCsquare.BDL as BDLModule

        bdl = readBDL(os.path.join(str(BDLModule.__path__[0]), 'BDL_default_DN_RangeShifter.txt'))

        plan = RTPlan()
        beam = PlanIonBeam()
        layer = PlanIonLayer(nominalEnergy=100.)
        layer.appendSpot(0, 0, 1)
        layer.appendSpot(0, 1, 2)

        beam.appendLayer(layer)

        plan.appendBeam(beam)

        writePlan(plan, 'plan_test.txt', CTImage(), bdl)
