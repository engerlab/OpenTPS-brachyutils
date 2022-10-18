import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import math
from opentps.core.data.dynamicData._dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._roiMask import ROIMask


def createSynthetic3DCT(diaphragmPos = 20, targetPos = [50, 100, 35], returnTumorMask = False):
    # GENERATE SYNTHETIC CT IMAGE
    # background
    im = np.full((170, 170, 100), -1000)
    im[20:150, 70:130, :] = 0
    # left lung
    im[30:70, 80:120, diaphragmPos:] = -800
    # right lung
    im[100:140, 80:120, diaphragmPos:] = -800
    # target
    im[targetPos[0]-5:targetPos[0]+5, targetPos[1]-5:targetPos[1]+5, targetPos[2]-5:targetPos[2]+5] = 0
    # vertebral column
    im[80:90, 95:105, :] = 800
    # couch
    im[:, 130:135, :] = 100
    ct = CTImage(imageArray=im, name='fixed', origin=[0, 0, 0], spacing=[1, 1, 2])

    if returnTumorMask:
        mask = np.full((170, 170, 100), 0)
        mask[targetPos[0]:targetPos[0]+10, targetPos[1]:targetPos[1]+10, targetPos[2]:targetPos[2]+10] = 1
        roi = ROIMask(imageArray=mask, origin=[0, 0, 0], spacing=[1, 1, 2])

        return ct, roi

    else:
        return ct


def createSynthetic4DCT(numberOfPhases = 4, returnTumorMasks = False):

    # GENERATE SYNTHETIC 4D INPUT SEQUENCE
    CT4D = Dynamic3DSequence()

    ## For the diaphragm position
    diaphMotionAmp = 12
    diaphMinPos = 20
    diaphPosList = getPhasesPositions(numberOfPhases, diaphMinPos, diaphMinPos+diaphMotionAmp)

    diaphNoise = [[3, 1],
              [6, -1],
              [9, -1],
              [12, 1],
              [15, 1]]

    for elemIdx in range(len(diaphNoise)):
        if diaphNoise[elemIdx][0] <= numberOfPhases - 1:
            diaphPosList[diaphNoise[elemIdx][0]] += diaphNoise[elemIdx][1]
    # print('diaphPosList', diaphPosList)

    ## For the target z position
    zMotionAmp = int(np.round(diaphMotionAmp * 0.8))
    zMinPos = 30
    zPosList = getPhasesPositions(numberOfPhases, zMinPos, zMinPos+zMotionAmp)

    zNoise = [[3, 1],
              [6, -1],
              [9, -1],
              [12, 1],
              [15, 1]]

    for elemIdx in range(len(zNoise)):
        if zNoise[elemIdx][0] <= numberOfPhases - 1:
            zPosList[zNoise[elemIdx][0]] += zNoise[elemIdx][1]
    # print('zPosList', zPosList)

    ## For the target x position
    xMotionAmp = 6
    xMinPos = 42
    xPosList = getPhasesPositions(numberOfPhases, xMinPos, xMinPos+xMotionAmp)

    xNoise = [[3, 1],
              [6, -1],
              [9, -1],
              [12, 1],
              [15, 1]]

    for elemIdx in range(len(xNoise)):
        if xNoise[elemIdx][0] <= numberOfPhases-1:
            xPosList[xNoise[elemIdx][0]] += xNoise[elemIdx][1]

    xPosList = np.roll(xPosList, 2)
    # print('xPosList', xPosList)

    phaseList = []
    if returnTumorMasks:
        maskList = []
        for phaseIndex in range(numberOfPhases):
            phase,  mask = createSynthetic3DCT(targetPos=[xPosList[phaseIndex], 95, zPosList[phaseIndex]], diaphragmPos=diaphPosList[phaseIndex], returnTumorMask=returnTumorMasks)
            phaseList.append(phase)
            maskList.append(mask)

    else:
        for phaseIndex in range(numberOfPhases):
            phase = createSynthetic3DCT(targetPos=[xPosList[phaseIndex], 95, zPosList[phaseIndex]], diaphragmPos=diaphPosList[phaseIndex])
            phaseList.append(phase)

    CT4D.dyn3DImageList = phaseList

    # # DISPLAY RESULTS
    # fig = plt.figure(tight_layout=True)
    # gs = gridspec.GridSpec(2, numberOfPhases)
    #
    # xPosList = np.append(xPosList, xPosList[0])
    # zPosList = np.append(zPosList, zPosList[0])
    #
    # ax = fig.add_subplot(gs[1, int(numberOfPhases/2)])
    # ax.plot(xPosList, zPosList)
    #
    # y_slice = 95
    # for i in range(numberOfPhases):
    #     ax = fig.add_subplot(gs[0, i])
    #     ax.imshow(CT4D.dyn3DImageList[i].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    #     ax.title.set_text('Phase' + str(i))
    #     ax.scatter(xPosList[i], CT4D.dyn3DImageList[i].imageArray.shape[2] - zPosList[i])
    #
    # plt.show()

    if returnTumorMasks:
        return CT4D, maskList
    else:
        return CT4D

def getPhasesPositions(numberOfPhases, minValue, maxValue):

    angleList = np.linspace(0, 2 * math.pi, numberOfPhases + 1)[:-1]
    cosList = np.cos(angleList)

    diff = maxValue - minValue

    posList = minValue + diff / 2 + cosList * diff / 2

    return posList.astype(np.uint8)