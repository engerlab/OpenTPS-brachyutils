import numpy as np
import matplotlib.pyplot as plt

def generateDynSeqFromBreathingSignalPointsAndModel(model, signalList, ROIList):

    if len(signalList) != len(ROIList):
        print('Numbers of signals and ROI do not match')
        return

    print(type(model))
    print(type(model.deformationList[0]))
    print(type(model.deformationList[0].velocity))

    modelDisplacementList = []
    print('in generateDynSeqFromBreathingSignalPointsAndModel, --> manually limited to 3 fields for speed testing pusrposes')
    pointDefValues = []

    modelDefValuesByPoint = [[] for roi in ROIList]
    print(modelDefValuesByPoint)
    for fieldIndex, field in enumerate(model.deformationList):
        field.displacement = field.velocity.exponentiateField()
        for pointIndex, point in enumerate(ROIList):
            print(point, type(field))
            modelDefValuesByPoint[pointIndex].append(getDataAtPosition(point, field.displacement))

    print(len(modelDefValuesByPoint[0]))
    print(modelDefValuesByPoint[0])



    for pointIndex in range(len(modelDefValuesByPoint)):
        modelDefValuesByPoint[pointIndex] = getDefDim(modelDefValuesByPoint[pointIndex], dim='X')

    for signal in signalList:
        getPhaseFromSampleAndDefValues(signal, )


    # for point in ROIList:
    #     pointDefValues = []
    #     for field in model.deformationList[:3]:
    #         pointDefValues.append(getDeformationValueFromPointInCoordinates(point))
    # print(len(modelDisplacementList))
    # print(type(modelDisplacementList)[0])
    # print(modelDisplacementList[0]._imageArray.shape)
    # print(modelDisplacementList[0].origin)
    # print(modelDisplacementList[0].spacing)


def getDataAtPosition(position, field):

    voxelIndex = getVoxelIndexFromPosition(position, field)
    dataNumpy = field.imageArray[voxelIndex[0], voxelIndex[1], voxelIndex[2]]

    return dataNumpy


def getVoxelIndexFromPosition(position, field):

    positionInMM = np.array(position)
    shiftedPosInMM = positionInMM - field.origin
    posInVoxels = np.round(np.divide(shiftedPosInMM, field.spacing)).astype(np.int)

    return posInVoxels

def getDefDim(defValueList, dim='norm'):

    print('in getDefDim', defValueList)

    defValueNormList = []
    for fieldIndex in range(len(defValueList)):
        defValueNormList.append(np.linalg.norm(defValueList[fieldIndex]))
    print('defValueNormList', defValueNormList)

    X = [defValueList[fieldIndex][0] for fieldIndex in range(len(defValueList))]
    Y = [defValueList[fieldIndex][1] for fieldIndex in range(len(defValueList))]
    Z = [defValueList[fieldIndex][2] for fieldIndex in range(len(defValueList))]

    plt.figure()
    plt.subplot(4, 1, 1)
    plt.plot(defValueNormList)
    plt.subplot(4, 1, 2)
    plt.plot(X)
    plt.subplot(4, 1, 3)
    plt.plot(Y)
    plt.subplot(4, 1, 4)
    plt.plot(Z)
    plt.show()

    if dim == 'norm':
        for fieldIndex in range(len(defValueList)):
            defValueList[fieldIndex] = np.linalg.norm(defValueList[fieldIndex])



    if dim == 'X':
        index = 0
    elif dim == 'Y':
        index = 1
    elif dim == 'Z':
        index = 2

## -----------------------------------------------------------------------------------------------------
def getBreathingPhasesInCTFromMotionSignalsNEW(MRIPos, CTPhasePositions, ascendDescendCase):

    meanPos = np.mean(CTPhasePositions[:-1])

    CTPhaseAscendingPart, ascentPartIndexes, CTPhaseDescendingPart, descentPartIndexes, amplitude = splitAscentDescentPartNEW(CTPhasePositions[:-1])

    if ascendDescendCase == "descending":
        phaseRatio = computePhaseRatioNEW(MRIPos, CTPhaseDescendingPart, descentPartIndexes, ascendDescendCase, meanPos)
    elif ascendDescendCase == "ascending":
        phaseRatio = computePhaseRatioNEW(MRIPos, CTPhaseAscendingPart, ascentPartIndexes, ascendDescendCase, meanPos)

    return phaseRatio

## -----------------------------------------------------------------------------------------------------
def separateDescentAscentParts(CTPhasePositions):

    if CTPhasePositions[1] > CTPhasePositions[0]:
        signValue = 1
        firstPart = "ascendingPart"
    elif CTPhasePositions[1] < CTPhasePositions[0]:
        signValue = -1
        firstPart = "descendingPart"

    changingPoint = 0
    while CTPhasePositions[changingPoint+1]*signValue > CTPhasePositions[changingPoint]*signValue:
        changingPoint += 1

    if firstPart == "ascendingPart":
        CTPhaseAscendingPart = CTPhasePositions[:changingPoint+1]
        CTPhaseDescendingPart = np.append(CTPhasePositions[changingPoint:], CTPhasePositions[0])
    elif firstPart == "descendingPart":
        CTPhaseDescendingPart = CTPhasePositions[:changingPoint+1]
        CTPhaseAscendingPart = np.append(CTPhasePositions[changingPoint:], CTPhasePositions[0])

    # plt.figure()
    # plt.plot(CTPhaseAscendingPart, color='r', label='Ascending part')
    # plt.plot(CTPhaseDescendingPart, label='Descending part')
    # plt.legend()
    # plt.show()

    return CTPhaseDescendingPart, CTPhaseAscendingPart, firstPart

## -----------------------------------------------------------------------------------------------------
def computePhaseRatioNEW(MRIPos, CTPhasesSubPart, CTPhasesPartsIndexes, ascendDescendCase, meanPos):

    correctedPhaseIndex = 0
    showingCondition = False

    interExtraCase = ''

    if ascendDescendCase == "descending":

        phaseIndex = 0

        if MRIPos > CTPhasesSubPart[0]:
            showingCondition = True
            interExtraCase = 'E'
            phaseIndex = CTPhasesPartsIndexes[0]
            correctedPhaseIndex = round(abs((MRIPos - meanPos) / (CTPhasesSubPart[0] - meanPos)), 2)

        elif MRIPos < CTPhasesSubPart[-1]:
            showingCondition = True
            interExtraCase = 'E'
            phaseIndex = CTPhasesPartsIndexes[-1]
            correctedPhaseIndex = round(abs((MRIPos - meanPos) / (CTPhasesSubPart[-1] - meanPos)), 2)

        else:
            showingCondition = True
            interExtraCase = 'I'
            while CTPhasesSubPart[phaseIndex] > MRIPos:
                phaseIndex += 1
            correctedPhaseIndex = (MRIPos - CTPhasesSubPart[phaseIndex - 1]) / (CTPhasesSubPart[phaseIndex] - CTPhasesSubPart[phaseIndex - 1])
            phaseIndex = CTPhasesPartsIndexes[phaseIndex - 1]

    elif ascendDescendCase == "ascending":

        phaseIndex = 0

        if MRIPos < CTPhasesSubPart[0]:
            showingCondition = True
            interExtraCase = 'E'
            phaseIndex = CTPhasesPartsIndexes[0]
            correctedPhaseIndex = round(abs((MRIPos - meanPos) / (CTPhasesSubPart[0] - meanPos)), 2)

        elif MRIPos > CTPhasesSubPart[-1]:
            showingCondition = True
            interExtraCase = 'E'
            phaseIndex = CTPhasesPartsIndexes[-1]
            correctedPhaseIndex = round(abs((MRIPos - meanPos) / (CTPhasesSubPart[-1] - meanPos)), 2)

        else:
            showingCondition = True
            interExtraCase = 'I'
            while CTPhasesSubPart[phaseIndex] < MRIPos:
                phaseIndex += 1
            correctedPhaseIndex = (MRIPos - CTPhasesSubPart[phaseIndex - 1]) / (CTPhasesSubPart[phaseIndex] - CTPhasesSubPart[phaseIndex - 1])
            phaseIndex = CTPhasesPartsIndexes[phaseIndex - 1]

    ## ----------------------
    # if showingCondition:
    #     plt.figure()
    #     plt.plot(CTPhasesSubPart, 'ro')
    #     plt.xticks(np.arange(len(CTPhasesSubPart)), CTPhasesPartsIndexes)
    #     #plt.xticks(x, my_xticks)
    #     plt.hlines(MRIPos, xmin=0, xmax=CTPhasesSubPart.shape[0], label='MRI tracked pos', color='b')
    #     plt.hlines(meanPos, xmin=0, xmax=CTPhasesSubPart.shape[0], label='MidP')
    #     plt.title(str(correctedPhaseIndex)+' - offset:'+str(phaseIndex) + ' - ' + interExtraCase + ' - ' + ascendDescendCase)
    #     plt.legend()
    #     plt.show()
    ## ----------------------

    return [interExtraCase, phaseIndex, correctedPhaseIndex]