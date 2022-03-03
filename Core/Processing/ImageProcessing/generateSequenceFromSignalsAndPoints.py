import numpy as np
import matplotlib.pyplot as plt
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from Core.IO.serializedObjectIO import saveSerializedObjects
from Core.Processing.weightMaps import generateDeformationFromTrackers, generateDeformationFromTrackersAndWeightMaps

def generateDynSeqFromBreathingSignalPointsAndModel(model, signalList, ROIList, dimensionUsed='Z'):

    if len(signalList) != len(ROIList):
        print('Numbers of signals and ROI do not match')
        return

    ## get displacement fields from velocity fields
    for fieldIndex, field in enumerate(model.deformationList):
        field.displacement = field.velocity.exponentiateField()

    ## for each ROI and signal pair
    ## - extract model values at ROI position
    ## - for each sample in the signal
    ## --> get phase value

    ## 1. From model and ROIList --> get model values at ROI position
    # modelDefValuesByPoint = [[] for roi in ROIList]

    phaseValueByROIList = []
    for ROIndex, ROI in enumerate(ROIList):

        modelDefValuesArray = getAverageModelValuesAroundPosition(ROI, model, dimensionUsed=dimensionUsed)

        # plt.figure()
        # plt.plot(modelDefValuesArray)
        # plt.show()

        meanPos = np.mean(modelDefValuesArray)  ## in case of synthetic signal use, this should be 0 ? this is not exactly 0 by using this mean on a particular dimension

        # split ascent descent and get ascent and descent indexes
        ascentPart, ascentPartIndexes, descentPart, descentPartIndexes, amplitude = splitAscentDescentSubsets(modelDefValuesArray)

        phaseValueList = []
        for sampleIndex in range(signalList[ROIndex].shape[0]):

            ascentOrDescentCase = isAscentOrDescentCase(signalList[ROIndex], sampleIndex)

            if ascentOrDescentCase == "descending":
                phaseRatio = computePhaseRatio(signalList[ROIndex][sampleIndex], descentPart, descentPartIndexes, ascentOrDescentCase, meanPos)
            elif ascentOrDescentCase == "ascending":
                phaseRatio = computePhaseRatio(signalList[ROIndex][sampleIndex], ascentPart, ascentPartIndexes, ascentOrDescentCase, meanPos)
            phaseValueList.append(phaseRatio)
            # print(phaseValueList[-1])

        phaseValueByROIList.append(phaseValueList)

    ## 2.
    print('youhou')
    print(len(phaseValueByROIList))
    print(len(phaseValueByROIList[0]))

    dynseq = Dynamic3DSequence()
    dynseq.name = 'Inversed_Lungs'
    print(dynseq.name)


    for breathingSignalSampleIndex in range(len(phaseValueByROIList[0])):

        phaseList = []
        amplitudeList = []
        for ROIndex in range(len(phaseValueByROIList)):

            phase = phaseValueByROIList[ROIndex][breathingSignalSampleIndex]
            print(phase)
            if phase[0] == 'I':
                phaseList.append((phase[1]+phase[2])/10)
                amplitudeList.append(1)
            elif phase[0] == 'E':
                phaseList.append(phase[1]/10)
                amplitudeList.append(phase[2])

        print('Image:', breathingSignalSampleIndex)
        print(len(ROIList), len(phaseList), len(amplitudeList))
        print(phaseList)
        print(amplitudeList)


        df1, wm = generateDeformationFromTrackers(model, phaseList, amplitudeList, ROIList)
        im1 = df1.deformImage(model.midp, fillValue='closest')
        print(type(im1))
        dynseq.dyn3DImageList.append(im1)

    return dynseq

    ## get phase list from model and



## ---------------------------------------------------------------------------------------------
def getAverageModelValuesAroundPosition(position, model, dimensionUsed='Z'):

    modelDefValuesList = []
    for fieldIndex, field in enumerate(model.deformationList):
        modelDefValuesList.append(getAverageFieldValueAroundPosition(position, field.displacement, dimensionUsed=dimensionUsed))

    modelDefValuesArray = np.array(modelDefValuesList)

    return modelDefValuesArray

## ---------------------------------------------------------------------------------------------
def getAverageFieldValueAroundPosition(position, field, dimensionUsed='Z'):

    voxelIndex = getVoxelIndexFromPosition(position, field)
    dataNumpy = field.imageArray[voxelIndex[0]-1:voxelIndex[0]+2, voxelIndex[1]-1:voxelIndex[1]+2, voxelIndex[2]-1:voxelIndex[2]+2]

    if dimensionUsed == 'norm':
        averageX = np.mean(dataNumpy[:, :, :, 0])
        averageY = np.mean(dataNumpy[:, :, :, 1])
        averageZ = np.mean(dataNumpy[:, :, :, 2])
        usedValue = np.linalg.norm(np.array([averageX, averageY, averageZ]))

    elif dimensionUsed == 'X':
        usedValue = np.mean(dataNumpy[:, :, :, 0])

    elif dimensionUsed == 'Y':
        usedValue = np.mean(dataNumpy[:, :, :, 1])

    elif dimensionUsed == 'Z':
        usedValue = np.mean(dataNumpy[:, :, :, 2])

    return usedValue

## ---------------------------------------------------------------------------------------------
def getFieldValueAtPosition(position, field, dimensionUsed='Z'):
    """
    Alternative function to getAverageFieldValueAroundPosition
    This one does not compute an average on a 3x3x3 cube around the position but gets the exact position value
    """
    voxelIndex = getVoxelIndexFromPosition(position, field)
    dataNumpy = field.imageArray[voxelIndex[0], voxelIndex[1], voxelIndex[2]]

    if dimensionUsed == 'norm':

        usedValue = np.linalg.norm(dataNumpy)

    elif dimensionUsed == 'X':
        usedValue = dataNumpy[0]

    elif dimensionUsed == 'Y':
        usedValue = dataNumpy[1]

    elif dimensionUsed == 'Z':
        usedValue = dataNumpy[2]

    return usedValue

## ---------------------------------------------------------------------------------------------
def getVoxelIndexFromPosition(position, field):

    positionInMM = np.array(position)
    shiftedPosInMM = positionInMM - field.origin
    posInVoxels = np.round(np.divide(shiftedPosInMM, field.spacing)).astype(np.int)

    return posInVoxels

## -------------------------------------------------------------------------------
def splitAscentDescentSubsets(CTPhasePositions):

    minIndex = np.argmin(CTPhasePositions)
    maxIndex = np.argmax(CTPhasePositions)
    #print('minIndex :', minIndex, 'maxIndex :', maxIndex)

    amplitude = CTPhasePositions[maxIndex] - CTPhasePositions[minIndex]

    if minIndex <= maxIndex:
        ascentPartIndexes = np.arange(minIndex, maxIndex + 1)
        descentPartIndexes = np.concatenate([np.arange(maxIndex, CTPhasePositions.shape[0]), np.arange(0, minIndex+1)])

    else:
        descentPartIndexes = np.arange(maxIndex, minIndex + 1)
        ascentPartIndexes = np.concatenate([np.arange(minIndex, CTPhasePositions.shape[0]), np.arange(0, maxIndex+1)])

    # print('ascentPartIndexes :', ascentPartIndexes)
    # print('descentPartIndexes :', descentPartIndexes)

    ascentPart = []
    for element in ascentPartIndexes:
        ascentPart.append(CTPhasePositions[element])
    ascentPart = np.array(ascentPart)

    descentPart = []
    for element in descentPartIndexes:
        descentPart.append(CTPhasePositions[element])
    descentPart = np.array(descentPart)

    # plt.figure()
    # plt.plot(descentPart, color='r', label='Descending part')
    # plt.plot(ascentPart, color='b', label='Ascending part')
    # plt.plot(CTPhasePositions, color='g', label='Phases from 0 to 9')
    # plt.legend()
    # plt.show()

    return ascentPart, ascentPartIndexes, descentPart, descentPartIndexes, amplitude

## ---------------------------------------------------------------------------------------------
def isAscentOrDescentCase(signal, currentIndex):

    currentPosition = signal[currentIndex]

    if currentIndex == 0:
        nextPosition = signal[currentIndex + 1]
        if currentPosition > nextPosition:
            ascendDescendCase = "descending"
        elif currentPosition <= nextPosition:
            ascendDescendCase = "ascending"
    else:
        lastPosition = signal[currentIndex - 1]
        if currentPosition < lastPosition:
            ascendDescendCase = "descending"
        elif currentPosition >= lastPosition:
            ascendDescendCase = "ascending"

    return ascendDescendCase

## -----------------------------------------------------------------------------------------------------
def computePhaseRatio(sampleValuePos, CTPhasesSubPart, CTPhasesPartsIndexes, ascendDescendCase, meanPos):

    correctedPhaseIndex = 0
    showingCondition = False

    interExtraCase = ''

    if ascendDescendCase == "descending":

        phaseIndex = 0

        if sampleValuePos > CTPhasesSubPart[0]:
            showingCondition = True
            interExtraCase = 'E'
            phaseIndex = CTPhasesPartsIndexes[0]
            correctedPhaseIndex = round(abs((sampleValuePos - meanPos) / (CTPhasesSubPart[0] - meanPos)), 2)

        elif sampleValuePos < CTPhasesSubPart[-1]:
            showingCondition = True
            interExtraCase = 'E'
            phaseIndex = CTPhasesPartsIndexes[-1]
            correctedPhaseIndex = round(abs((sampleValuePos - meanPos) / (CTPhasesSubPart[-1] - meanPos)), 2)

        else:
            showingCondition = True
            interExtraCase = 'I'
            while CTPhasesSubPart[phaseIndex] > sampleValuePos:
                phaseIndex += 1
            correctedPhaseIndex = (sampleValuePos - CTPhasesSubPart[phaseIndex - 1]) / (CTPhasesSubPart[phaseIndex] - CTPhasesSubPart[phaseIndex - 1])
            phaseIndex = CTPhasesPartsIndexes[phaseIndex - 1]

    elif ascendDescendCase == "ascending":

        phaseIndex = 0

        if sampleValuePos < CTPhasesSubPart[0]:
            showingCondition = True
            interExtraCase = 'E'
            phaseIndex = CTPhasesPartsIndexes[0]
            correctedPhaseIndex = round(abs((sampleValuePos - meanPos) / (CTPhasesSubPart[0] - meanPos)), 2)

        elif sampleValuePos > CTPhasesSubPart[-1]:
            showingCondition = True
            interExtraCase = 'E'
            phaseIndex = CTPhasesPartsIndexes[-1]
            correctedPhaseIndex = round(abs((sampleValuePos - meanPos) / (CTPhasesSubPart[-1] - meanPos)), 2)

        else:
            showingCondition = True
            interExtraCase = 'I'
            while CTPhasesSubPart[phaseIndex] < sampleValuePos:
                phaseIndex += 1
            correctedPhaseIndex = (sampleValuePos - CTPhasesSubPart[phaseIndex - 1]) / (CTPhasesSubPart[phaseIndex] - CTPhasesSubPart[phaseIndex - 1])
            phaseIndex = CTPhasesPartsIndexes[phaseIndex - 1]

    ## ----------------------
    # if showingCondition:
    #     plt.figure()
    #     plt.plot(CTPhasesSubPart, 'ro')
    #     plt.xticks(np.arange(len(CTPhasesSubPart)), CTPhasesPartsIndexes)
    #     #plt.xticks(x, my_xticks)
    #     plt.hlines(sampleValuePos, xmin=0, xmax=CTPhasesSubPart.shape[0], label='MRI tracked pos', color='b')
    #     plt.hlines(meanPos, xmin=0, xmax=CTPhasesSubPart.shape[0], label='MidP')
    #     plt.title(str(correctedPhaseIndex)+' - offset:'+str(phaseIndex) + ' - ' + interExtraCase + ' - ' + ascendDescendCase)
    #     plt.legend()
    #     plt.show()
    ## ----------------------

    return [interExtraCase, phaseIndex, correctedPhaseIndex]

