import os
import struct
import logging

import numpy as np
import scipy.sparse as sp
from scipy.sparse import csc_matrix
from opentps.core.data.images import CTImage
from opentps.core.data.plan._photonPlan import PhotonPlan
import math
from opentps.core.data import SparseBeamlets
import math
from opentps.core.data.images._doseImage import DoseImage
from typing import Optional, Sequence, Union
from opentps.core.data import ROIContour
from opentps.core.data.images import ROIMask
from matplotlib import pyplot as plt

logger = logging.getLogger(__name__)

def rotateVector(vec, angle, axis):
    if axis == 'x':
        x = vec[0]
        y = vec[1] * math.cos(angle) - vec[2] * math.sin(angle)
        z = vec[1] * math.sin(angle) + vec[2] * math.cos(angle)
    elif axis == 'y':
        x = vec[0] * math.cos(angle) + vec[2] * math.sin(angle)
        y = vec[1]
        z = -vec[0] * math.sin(angle) + vec[2] * math.cos(angle)
    elif axis == 'z':
        x = vec[0] * math.cos(angle) - vec[1] * math.sin(angle)
        y = vec[0] * math.sin(angle) + vec[1] * math.cos(angle)
        z = vec[2]
    return [x, y, z]

def getRotatedVersors(gantryAngle, couchAngle, collimatorAngle): ### In the CCC algorithm x is pointing to the gantry when gantryAngle = 0 and couchAngle = 0, z has the direction of the treatment coach
    i = [0, 1.0, 0]  
    i = rotateVector(i, math.radians(collimatorAngle), 'x') # rotation for collimator angle
    i = rotateVector(i, math.radians(gantryAngle), 'z')  # rotation for gantry angle
    i = rotateVector(i, math.radians(couchAngle), 'x')  # rotation for couch angle

    j = [0, 0, 1.0]  
    j = rotateVector(j, math.radians(collimatorAngle), 'x') # rotation for collimator angle
    j = rotateVector(j, math.radians(gantryAngle), 'z')  # rotation for gantry angle
    j = rotateVector(j, math.radians(couchAngle), 'x')  # rotation for couch angle   

    k = [1.0, 0, 0]  
    k = rotateVector(k, math.radians(gantryAngle), 'z')  # rotation for gantry angle
    k = rotateVector(k, math.radians(couchAngle), 'x')  # rotation for couch angle
    return i, j, k

def writeBeamletInFile(f, number, SAD, x, y, dx, dy, i, j, k): ### Parameters for Dose Engine should be in cm
    yvec = -1 * np.array(k) * SAD 
    f.write('num\n'+str(number)+'\n')
    f.write('SAD xp yp del_xp del_yp\n')
    f.write('{SAD:f} {xp:f} {yp:f} {del_xp:f} {del_yp:f}\n'.format(SAD = SAD, xp = x, yp = y, del_xp = dx, del_yp = dy))
    f.write('y_vec\n')
    f.write('{:f} {:f} {:f}\n'.format(yvec[0], yvec[1], yvec[2]))
    f.write('ip\n')
    f.write('{:f} {:f} {:f}\n'.format(i[0], i[1], i[2]))
    f.write('jp\n')
    f.write('{:f} {:f} {:f}\n'.format(j[0], j[1], j[2]))
    f.write('kp\n')
    f.write('{:f} {:f} {:f}\n'.format(k[0], k[1], k[2]))
    f.write('\n \n')

def writePlan(plan: PhotonPlan, beamDirectory, batchSize):
    plan.simplify()
    beamsPerBatch = plan.numberOfBeamlets / batchSize
    beamNumber = 0
    planBeamlets = plan.beamlets
    planBeamSegments = plan.beamSegments
    bemaletNumberPerSegmentAccumulated = np.cumsum([len(beamSegment) for beamSegment in planBeamSegments])
    rotatedVersorsPerBeam = [getRotatedVersors(beamSegment.gantryAngle_degree, beamSegment.couchAngle_degree, beamSegment.beamLimitingDeviceAngle_degree) for beamSegment in plan.beamSegments]
    print('There are {} beams per batch file'.format(round(beamsPerBatch)))
    numofBeams = 0
    for batch in range(batchSize):
        beamletNumMin = math.floor(beamsPerBatch * batch) 
        beamletNumMax = math.floor(beamsPerBatch * (batch+1) + 1e-4) # To avoid float precision problem I add small number 
        numofBeams  += beamletNumMax - beamletNumMin
        f = open(os.path.join(beamDirectory,'pencilBeamSpecs_batch{}.txt'.format(batch)),'w')
        f.write('beamnum:\n'+str(beamletNumMax - beamletNumMin))
        f.write('\n \n')
        for beamlet in planBeamlets[beamletNumMin:beamletNumMax]:
            beamIndex = np.argwhere(beamNumber < bemaletNumberPerSegmentAccumulated)[0][0]
            i, j, k = rotatedVersorsPerBeam[beamIndex]
            # for beamlet in beam.beamlets:
            XY = beamlet.XY_mm[0]
            writeBeamletInFile(f, beamNumber, plan.SAD_mm / 10, XY[0] / 10, XY[1] / 10, planBeamSegments[beamIndex].xBeamletSpacing_mm / 10, planBeamSegments[beamIndex].yBeamletSpacing_mm / 10, i, j, k) ### Parameters for Dose Engine should be in cm
            beamNumber+=1

        f.close()

def writeCTHeaderFile(size, spacing, origin_shifted, origin, outputfile):
    f = open(os.path.join(outputfile, 'CT_HeaderFile.txt'),'w')
    f.write("Xcount Ycount Zcount\n")
    f.write("{} {} {}\n".format(size[1], size[0], size[2]))### In the CCC coordinate system the first two axis are switched (x is looking at the gantry)
    f.write("Xstart Ystart Zstart\n")
    f.write("{} {} {}\n".format(origin_shifted[1], origin_shifted[0], origin_shifted[2]))### In the CCC coordinate system the first two axis are switched (x is looking at the gantry)
    f.write("dx dy dz\n")
    f.write("{} {} {}\n".format(spacing[1], spacing[0], spacing[2]))### In the CCC coordinate system the first two axis are switched (x is looking at the gantry)
    f.write("Xorigin Yorigin Yorigin\n")
    f.write("{} {} {}\n".format(origin[0], origin[1], origin[2]))
    f.close()

def writeCTdirFile(outputfile):
    f = open(os.path.join(os.path.dirname(outputfile), 'CTdirectoryFile.txt'),'w')
    f.write('geometry_header\n')
    f.write('{}\n'.format(os.path.join(outputfile, 'CT_HeaderFile.txt')))
    f.write('geometry_density\n')
    f.write('{}\n'.format(os.path.join(outputfile, 'CT.bin')))
    f.close()

def writeCT(ct: CTImage, filtePath, IsocenterPosition_mm, overwriteOutsideROI=None):
    # Convert data for compatibility with MCsquare
    # These transformations may be modified in a future version
    image = ct.copy()

    # Crop CT image with contour
    if overwriteOutsideROI is not None:
        logger.info(f'Cropping CT around {overwriteOutsideROI.name}')
        contour_mask = overwriteOutsideROI.getBinaryMask(image.origin, image.gridSize, image.spacing)
        image.imageArray[contour_mask.imageArray.astype(bool) == False] = -1024

    img_array = ct.imageArray.transpose((2,0,1))
    img_array.ravel().astype(np.float32).tofile(os.path.join(filtePath, 'CT.bin'))
    origin_shifted = ct.origin - IsocenterPosition_mm ### I need to put the center of mass of the target in the 0,0,0 coordinates because that is what the CCC doseengine takes as isocenter
    writeCTHeaderFile(ct.imageArray.shape, ct.spacing / 10, origin_shifted / 10, ct.origin / 10, filtePath) ### The image dimension in the Dose Engine should be in cm
    writeCTdirFile(filtePath)

def read_header(path):
    header = {}
    f = open(path)
    Lines = f.readlines()
    header['Size'] = np.array(Lines[1].rstrip('\n').split(' '),int)
    header['Size'][0], header['Size'][1] = header['Size'][1], header['Size'][0]
    header['Origin_shifted_cm'] = np.array(Lines[3].rstrip('\n').split(' '),float)
    header['Spacing_cm'] = np.array(Lines[5].rstrip('\n').split(' '),float)
    header['Origin_cm'] = np.array(Lines[7].rstrip('\n').split(' '),float)
    f.close()
    header['NbrVoxels'] = np.prod(header['Size'])
    return header


def convertTo3Dcoord(arr,size):
    i = arr//(size[1] * size[2])
    j = arr % (size[1] * size[2]) // size[2]
    k = arr % (size[1] * size[2]) % size[2]
    return i,j,k

def convertTo1Dcoord(arr,size):
    return arr[2] + arr[1] * size[2] + arr[0] * size[1] * size[2]

def convertTo1DcoordFortran(arr,size): ### Ravel the array in order='F' FortranMode
    return arr[0] + arr[1] * size[0] + arr[2] * size[1] * size[0]

def formatToOpenTPSformat(arr,size):
    return convertTo1DcoordFortran([size[0]-(arr[0]+1), size[1]-(arr[1]+1), arr[2]],size) ### Flip axis 0 and 1

def changeOfCoordinates(beamIndexes, size): ### The indexes exported in CCC have coordinates [size[2],size[0],size[1]]. This function change the index for size[0],size[1],size[2] in OpenTPS order
    i, j, k = convertTo3Dcoord(np.array(beamIndexes), [size[2], size[0], size[1]])
    return formatToOpenTPSformat([j, k, i], size) ### This transpose the axis j = 0, k = 1, i = 2 and order the indexes following the indexation used in OpenTPS 
        

def read_sparse_data(matrixBeamlets_path, header, BeamletMatrix = None):
    with open(matrixBeamlets_path, mode='rb') as file: # b is important -> binary
        fileContent = file.read()
    Nbeamlets = struct.unpack("i", fileContent[:4])[0]
    numberOfReadItems = 4 ### The first 4 are for the number of beamlets
    if BeamletMatrix is None:
        BeamletMatrix = []
    for i in range(Nbeamlets):
        BeamProp = struct.unpack("iiiii", fileContent[numberOfReadItems:numberOfReadItems+20])
        numberOfReadItems+=20
        beamIndexes = struct.unpack("i"*BeamProp[-1], fileContent[numberOfReadItems:numberOfReadItems+BeamProp[-1] * 4])
        numberOfReadItems += BeamProp[-1] * 4
        beamValues = struct.unpack("f"*BeamProp[-1], fileContent[numberOfReadItems:numberOfReadItems+BeamProp[-1] * 4])
        numberOfReadItems += BeamProp[-1] * 4
        beamIndexes = changeOfCoordinates(beamIndexes, header['Size'])
        d_beamletMatrix = sp.csc_matrix(
                        (beamValues, (beamIndexes, np.zeros(len(beamIndexes)))), shape=(header['NbrVoxels'], 1),
                        dtype=np.float32) 
        BeamletMatrix.append(d_beamletMatrix)
    return BeamletMatrix, Nbeamlets

def mergeContours(roi, flatAndFlip = True):
    if isinstance(roi, ROIMask):
        roi = [roi]
    logger.info("Beamlets are computed on {}".format([contour.name for contour in roi]))
    roiUnion = None
    for contour in roi:
        if flatAndFlip:
            roiData = np.flip(contour.imageArray,(0,1))
            roiData = np.ndarray.flatten(roiData,'F').astype('bool')
        else:
            roiData = contour.imageArray
        if roiUnion is None:
            roiUnion = roiData
        else:
            roiUnion = np.logical_or(roiUnion, roiData)
    return roiUnion

def readBeamlets(CTheaderfile_path, outputDir, batchSize, roi: Optional[Sequence[Union[ROIContour, ROIMask]]] = None): 
    if (not CTheaderfile_path.endswith('.txt')):
        raise NameError('File ', CTheaderfile_path, ' is not a valid sparse matrix header')

    # Read sparse beamlets header file
    logger.info('Reading header from: {}'.format(CTheaderfile_path))
    header = read_header(CTheaderfile_path)

    sparseBeamletsDose = None
    numberOfBeamlets = 0
    # Read sparse beamlets binary file
    for batch in range(batchSize):
        matrixBeamlets_path = os.path.join(outputDir,'sparseBeamletMatrix_batch{}.bin'.format(batch))
        logger.info('Read binary file: {}'.format(matrixBeamlets_path))
        sparseBeamletsDose, numberOfBeamletsInBatch = read_sparse_data(matrixBeamlets_path, header, sparseBeamletsDose)
        numberOfBeamlets+=numberOfBeamletsInBatch
    
    sparseBeamletsDose = sp.hstack(sparseBeamletsDose)
    header["NbrBeamlets"] = numberOfBeamlets

    if not(roi is None) or (roi is list and not(len(roi)==0)):
        roiUnion = mergeContours(roi)
        sparseBeamletsDose = sp.csc_matrix.dot(sp.diags(roiUnion.astype(np.int32), format='csc'),
                                              sparseBeamletsDose)
        
    beamletDose = SparseBeamlets()
    beamletDose.setUnitaryBeamlets(sparseBeamletsDose)
    # beamletDose.beamletWeights = np.ones(header["NbrBeamlets"])
    beamletDose.doseOrigin = header["Origin_cm"] * 10
    beamletDose.doseSpacing = header["Spacing_cm"] * 10
    beamletDose.doseGridSize = header["Size"]
     
    return beamletDose


def readDose(CTheaderfile_path, outputDir, batchSize, Mu): 
    if (not CTheaderfile_path.endswith('.txt')):
        raise NameError('File ', CTheaderfile_path, ' is not a valid sparse matrix header')

    # Read sparse beamlets header file
    logger.info('Reading header from: {}'.format(CTheaderfile_path))
    header = read_header(CTheaderfile_path)
    totalDose = None
    sparseBeamletsDose = None
    numberOfBeamlets = 0
    # Read sparse beamlets binary file
    for batch in range(batchSize):
        matrixBeamlets_path = os.path.join(outputDir,'sparseBeamletMatrix_batch{}.bin'.format(batch))
        logger.info('Read binary file: {}'.format(matrixBeamlets_path))
        sparseBeamletsDose, numberOfBeamletsInBatch = read_sparse_data(matrixBeamlets_path, header)
        sparseBeamletsDose = sp.hstack(sparseBeamletsDose)
        if totalDose is None:
            totalDose = csc_matrix.dot(sparseBeamletsDose, Mu[numberOfBeamlets:numberOfBeamlets+numberOfBeamletsInBatch])
        else:
            totalDose += csc_matrix.dot(sparseBeamletsDose, Mu[numberOfBeamlets:numberOfBeamlets+numberOfBeamletsInBatch])
        numberOfBeamlets+=numberOfBeamletsInBatch

    orientation = (1, 0, 0, 0, 1, 0, 0, 0, 1)
    totalDose = np.reshape(totalDose, header["Size"], order='F')
    totalDose = np.flip(totalDose, 0)
    totalDose = np.flip(totalDose, 1)

    doseImage = DoseImage(imageArray=totalDose, origin=header["Origin_cm"] * 10, spacing=header["Spacing_cm"] * 10,
                            angles=orientation) ### The TPS works with mm


    return doseImage
