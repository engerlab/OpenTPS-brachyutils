
import os
import numpy as np

# patient = 'Patient1'
#
# ## read a 4DCT
# dataPath = "/media/damien/data/ImageData/Liver/" + patient + "/4DCT/"
# dataList = loadAllData(dataPath)
#
# ## create a Dynamic3DSequence and change its name
# dynseq = Dynamic3DSequence(dyn3DImageList=dataList)
#
# model4D = Dynamic3DModel()
# model4D.computeMidPositionImage(dynseq)

# ## save it as a serialized object
# savingPath = '/home/damien/Desktop/' + 'PatientTest_dynMod.p'
# saveSerializedObject(newMod, savingPath)

""" Patient folder path for everything linked to the patient"""
patient = 'Patient1'
patientFolderPath = "/media/damien/data/ImageData/Liver/" + patient + '/'

""" Sequence folder path for everything linked to a specific MRI sequence """
#sequenceName = '1Plan1Pos'
sequenceName = '2Plans'
#sequenceName = '2PlansBis'
#sequenceName = '1Plan3Pos'
sequenceFolderPath = patientFolderPath + sequenceName + "/"

""" Motion signal path """
motionSignalPath = sequenceFolderPath + 'MotionSignals/'

#model4D =

## -----------------------------------------------------------------------------------------------------
def getMotionDictList(motionSigsFolderPath):

    motionSigsDictList = []

    for file in os.listdir(motionSigsFolderPath):
        if file.endswith(".txt") and not file.startswith("."):
            motionSigsDictList.append(readTxtNavToDict(motionSigsFolderPath+file))

    return motionSigsDictList


## -----------------------------------------------------------------------------------------------------
def readTxtNavToDict(filePath):

    with open(filePath) as f:
        content = f.readlines()
    # you may also want to remove whitespace characters like `\n` at the end of each line
    content = [x.strip() for x in content]

    navDict = {}

    navIDList = content[0].split(' ')
    navDict["type"] = navIDList[-3]
    navDict["sourceImage"] = navIDList[-4]
    navDict["navIndex"] = int(navIDList[-2])
    navDict["color"] = navIDList[-1]

    splittedList = navDict["sourceImage"].split("_")
    navDict["modality"] = splittedList[0]

    for element in splittedList:
        if 'Sag' in element or 'Cor' in element or 'Tra' in element:
            navDict["posName"] = element

    content[1] = content[1].replace("(", " ")
    content[1] = content[1].replace(")", " ")
    content[1] = content[1].replace("  ", " ")
    content[1] = content[1].split(' ')

    if len(content[1]) > 10:
        navPointsList = [(float(content[1][3]), float(content[1][4]), float(content[1][5])),
                         (float(content[1][6]), float(content[1][7]), float(content[1][8])),
                         (float(content[1][9]), float(content[1][10]), float(content[1][11]))]
    else:
        navPointsList = [(float(content[1][3]), float(content[1][4]), float(content[1][5])),
                         (float(content[1][6]), float(content[1][7]), float(content[1][8]))]

    navDict["pointList"] = navPointsList

    content[2] = content[2].split(' ')
    navDict["orientation"] = content[2][-3]
    navDict["angle"] = float(content[2][-1])

    numberOfColumn = len(content[4].split(' '))

    signalArray = np.zeros((len(content)-4, numberOfColumn))

    for i in range(4, len(content)):

        content[i] = content[i].split(' ')

        for j in range(0, numberOfColumn):
            signalArray[i-4, j] = float(content[i][j])

    navDict["signalArrayTGXYH"] = signalArray

    return navDict

## ---------------------------------------------------------------------------------------------------
def splitSignalsByImagePosByPairNEW(motionSigsDictList):

    motionSigsDictList = sorted(motionSigsDictList, key=lambda navDict: navDict["modality"])
    splitedSignalsByPairDictList = []
    posList = []

    for navDict1 in motionSigsDictList[:int(round(len(motionSigsDictList)/2))]:

        posList.append(navDict1["posName"])

        for navDict2 in motionSigsDictList[int(round(len(motionSigsDictList)/2)):]:
            if navDict1["posName"] == navDict2["posName"] and navDict1["navIndex"] == navDict2["navIndex"] and navDict1["modality"] != navDict2["modality"]:

                if navDict1["modality"] == 'MRI':
                    splitedSignalsByPairDictList.append([navDict1, navDict2])
                else:
                    splitedSignalsByPairDictList.append([navDict2, navDict1])

    posList = list(set(posList))

    signalByPosByPairDictList = [[] for _ in range(len(posList))]

    for i in range(len(splitedSignalsByPairDictList)):
        for j in range(len(posList)):
            if posList[j] == splitedSignalsByPairDictList[i][0]["posName"]:
                signalByPosByPairDictList[j].append(splitedSignalsByPairDictList[i])

    return signalByPosByPairDictList, posList


## -----------------------------------------------------------------------------------------------------
def getSignalIndexToUse(signalToUseStr):

    sigToUse = 0

    if signalToUseStr == 'G':
        sigToUse = 1
    elif signalToUseStr == 'X':
        sigToUse = 2
    elif signalToUseStr == 'Y':
        sigToUse = 3
    elif signalToUseStr == 'H':
        sigToUse = 4

    return sigToUse

## -----------------------------------------------------------------------------------------------------
def getBreathingPhasesInCTFromMotionSignalsNEW(MRIPos, CTPhasePositions, ascendDescendCase):

    meanPos = np.mean(CTPhasePositions[:-1])

    CTPhaseAscendingPart, ascentPartIndexes, CTPhaseDescendingPart, descentPartIndexes, amplitude = splitAscentDescentPartNEW(CTPhasePositions[:-1])

    if ascendDescendCase == "descending":
        phaseRatio = computePhaseRatioNEW(MRIPos, CTPhaseDescendingPart, descentPartIndexes, ascendDescendCase, meanPos)
    elif ascendDescendCase == "ascending":
        phaseRatio = computePhaseRatioNEW(MRIPos, CTPhaseAscendingPart, ascentPartIndexes, ascendDescendCase, meanPos)

    return phaseRatio

## -------------------------------------------------------------------------------
def splitAscentDescentPartNEW(CTPhasePositions):

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

    print('ascentPartIndexes :', ascentPartIndexes)
    print('descentPartIndexes :', descentPartIndexes)

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

## ----------------------------------------------------------------------------------------------------------
## ----------------------------------------------------------------------------------------------------------
## ----------------------------------------------------------------------------------------------------------
motionSigsDictList = getMotionDictList(motionSignalPath)
print(len(motionSigsDictList), "motion signals found in motionSigFolderPath")

completeList = []
splitedSignalsByPosByPairDictList, posList = splitSignalsByImagePosByPairNEW(motionSigsDictList)

print(len(splitedSignalsByPosByPairDictList), 'different source image found')
print(posList)

for signalsByPairDictListIndex, signalsByPairDictList in enumerate(splitedSignalsByPosByPairDictList):

    print(len(signalsByPairDictList), 'tracker pairs found for the position', signalsByPairDictListIndex)

    trackerMidPosList = []

    for pairIndex in range(len(signalsByPairDictList)):
        point1 = signalsByPairDictList[pairIndex][0]['pointList'][0]
        point2 = signalsByPairDictList[pairIndex][0]['pointList'][1]
        trackerMidPos = (float(point1[0] + (point2[0] - point1[0]) * 0.5),
                         float(point1[1] + (point2[1] - point1[1]) * 0.5),
                         float(point1[2] + (point2[2] - point1[2]) * 0.5))
        trackerMidPosList.append(trackerMidPos)

    if signalsByPairDictList[0][0]['posName'] == 'Pos1Cor':
        print('yeah')
    #
    #     for file in os.listdir(phaseInfoByFramePath):
    #         print(file)

        for imageIndex in range(signalsByPairDictList[0][0]['signalArrayTGXYH'].shape[0]):

            print('------- image :', imageIndex, '------------------------')
            trackedPhasesList = []

            for pairIndex in range(len(signalsByPairDictList)):

                print('pairIndex', pairIndex, signalsByPairDictList[pairIndex][0]['sourceImage'], '',
                      signalsByPairDictList[pairIndex][1]['sourceImage'])
                # print(signalsByPairDictList[pairIndex][0]['sourceImage'])
                # print(signalsByPairDictList[pairIndex][1]['sourceImage'])
                # print(signalsByPairDictList[pairIndex][0].keys())
                # print(signalsByPairDictList[pairIndex][1].keys())
                print('navIndex : ', signalsByPairDictList[pairIndex][0]['navIndex'])
                # print(signalsByPairDictList[pairIndex][1]['pointList'])
                # print(signalsByPairDictList[pairIndex][0]['signalArrayTGXYH'][imageIndex])
                # print(signalsByPairDictList[pairIndex][1]['signalArrayTGXYH'][imageIndex])

                print(
                    'ATTENTION !!! l ordre des points a peut être une importance !!! je suppose ici que le point1 est le point à partir duquel le tracker est mesuré, est ce vrai ?')
                # point1 = signalsByPairDictList[pairIndex][0]['pointList'][0]
                # point2 = signalsByPairDictList[pairIndex][0]['pointList'][1]
                signalIndexToUse = getSignalIndexToUse('G')
                MRIPosition = signalsByPairDictList[pairIndex][0]['signalArrayTGXYH'][imageIndex, signalIndexToUse]

                if imageIndex == 0:
                    MRINextPosition = signalsByPairDictList[pairIndex][0]['signalArrayTGXYH'][
                        imageIndex + 1, signalIndexToUse]
                    if MRIPosition > MRINextPosition:
                        ascendDescendCase = "descending"
                    elif MRIPosition <= MRINextPosition:
                        ascendDescendCase = "ascending"
                else:
                    MRILastPosition = signalsByPairDictList[pairIndex][0]['signalArrayTGXYH'][
                        imageIndex - 1, signalIndexToUse]
                    if MRIPosition < MRILastPosition:
                        ascendDescendCase = "descending"
                    elif MRIPosition >= MRILastPosition:
                        ascendDescendCase = "ascending"

                # distanceBetweenPoints = math.sqrt((math.pow(point2[0]-point1[0], 2) + math.pow(point2[1]-point1[1], 2) + math.pow(point2[2]-point1[2], 2))) ## Not optimized to do that here because it will do the same computation for each image
                # print('distanceBetweenPoints', distanceBetweenPoints)
                # ratio = MRIPosition / distanceBetweenPoints
                # print('ratio', ratio)
                # trackerPos = (float(point1[0] + (point2[0]-point1[0]) * ratio), float(point1[1] + (point2[1]-point1[1]) * ratio), float(point1[2] + (point2[2]-point1[2]) * ratio))
                # print('trackerPos', trackerPos, type(trackerPos))
                # print(dataDict['dynamic2DImageList'][0]['completeName'])

                CTPhasePositions = signalsByPairDictList[pairIndex][1]["signalArrayTGXYH"][:10 + 1, signalIndexToUse]
                CTTrackedBreathingPhases = getBreathingPhasesInCTFromMotionSignalsNEW(MRIPosition, CTPhasePositions,ascendDescendCase)
                CTTrackedBreathingPhases.append(signalsByPairDictList[pairIndex][0]['navIndex'])
                trackedPhasesList.append(CTTrackedBreathingPhases)

            # GENERATE ADDITIONAL PHASES
            phaseList = []
            amplitudeList = []

            for phase in trackedPhasesList:
                print(phase)
                if phase[0] == 'I':
                    phaseList.append((phase[1]+phase[2])/10)
                    amplitudeList.append(1)
                elif phase[0] == 'E':
                    phaseList.append(phase[1]/10)
                    amplitudeList.append(phase[2])

            print(phaseList)
            print(amplitudeList)

            print(signalsByPairDictList[pairIndex][1].keys())
            print(signalsByPairDictList[pairIndex][1]['posName'])
            print(signalsByPairDictList[pairIndex][0]['sourceImage'])
            print(signalsByPairDictList[pairIndex][1]['sourceImage'])
            #print(signalsByPairDictList[pairIndex][0]['signalArrayTGXYH'])

            print(imageIndex)

            # df1, wm = generateDeformationFromTrackers(model4D, phaseList, amplitudeList, trackerMidPosList)
            # im1 = df1.deformImage(model4D.midp, fillValue='closest')



