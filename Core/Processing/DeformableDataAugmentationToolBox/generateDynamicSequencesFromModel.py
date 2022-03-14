import numpy as np
from Core.Data.DynamicData.dynamic3DSequence import Dynamic3DSequence
from Core.Processing.DeformableDataAugmentationToolBox.weightMaps import generateDeformationFromTrackers
from Core.Processing.DeformableDataAugmentationToolBox.modelManipFunctions import *


## -------------------------------------------------------------------------------
def generateDynSeqFromBreathingSignalsAndModel(model, signalList, ROIList, signalIdxUsed=[0, 0], dimensionUsed='Z', outputType=np.float32):

    """
    Generate a dynamic 3D sequence from a model, in which each given ROI follows its breathing signal

    Parameters
    ----------
    model : Dynamic3DModel
        The dynamic 3D model that will be used to create the images of the resulting sequence
    signalList : list
        list of breathing signals as 1D numpy arrays
    ROIList : list
        list of points as [X, Y, Z] or (X, Y, Z) --> does not work with ROI's as masks or struct
    dimensionUsed : str
        X, Y, Z or norm, the dimension used to compare the breathing signals with the model deformation values
    outputType : pixel data type (np.float32, np.uint16, etc)

    Returns
    -------
    dynseq (Dynamic3DSequence): a new sequence containing the generated images

    """

    if len(signalList) != len(ROIList):
        print('Numbers of signals and ROI do not match')
        return

    ## get displacement fields from velocity fields
    if model.deformationList[0].displacement == None:
        print('Compute displacement fields')
        for fieldIndex, field in enumerate(model.deformationList):
            print('Field', fieldIndex+1, '/', len(model.deformationList))
            field.displacement = field.velocity.exponentiateField()

    if signalIdxUsed == [0, 0]:
        signalIdxUsed = [0, signalList[0].shape[0]]

    # print('Signal indexes used', signalIdxUsed)

    ## loop over ROIs
    phaseValueByROIList = []
    for ROIndex, ROI in enumerate(ROIList):

        ## get model deformation values for the specified dimension at the ROI location
        modelDefValuesArray = getAverageModelValuesAroundPosition(ROI, model, dimensionUsed=dimensionUsed)

        # plt.figure()
        # plt.plot(modelDefValuesArray)
        # plt.show()

        ## get the midP value for the specified dimension
        meanPos = np.mean(modelDefValuesArray)  ## in case of synthetic signal use, this should be 0 ? this is not exactly 0 by using this mean on a particular dimension

        # split into ascent and descent subset for the ROI location
        ascentPart, ascentPartIndexes, descentPart, descentPartIndexes, amplitude = splitAscentDescentSubsets(modelDefValuesArray)

        phaseValueList = []
        ## loop over breathing signal samples
        for sampleIndex in range(signalIdxUsed[0], signalIdxUsed[1]):

            ## get the ascent or descent situation and compute the phase value for each sample
            ascentOrDescentCase = isAscentOrDescentCase(signalList[ROIndex], sampleIndex)

            if ascentOrDescentCase == "descending":
                phaseRatio = computePhaseRatio(signalList[ROIndex][sampleIndex], descentPart, descentPartIndexes, ascentOrDescentCase, meanPos)
            elif ascentOrDescentCase == "ascending":
                phaseRatio = computePhaseRatio(signalList[ROIndex][sampleIndex], ascentPart, ascentPartIndexes, ascentOrDescentCase, meanPos)
            ## add the resulting phase to the list for each breathing signal sample
            phaseValueList.append(phaseRatio)

        ## add the phaseValueList to the complete list for each ROI
        phaseValueByROIList.append(phaseValueList)

    ## At this point the phase information are computed, now the part where the images are created starts
    ## New empty dynamic 3D sequence is created
    dynseq = Dynamic3DSequence()
    dynseq.name = 'GeneratedFromBreathingSignal'

    ## loop over breathing signal sample
    for breathingSignalSampleIndex in range(len(phaseValueByROIList[0])):

        print('Deform image', signalIdxUsed[0] + breathingSignalSampleIndex)
        ## translate the phase infos into phase and amplitude lists
        phaseList = []
        amplitudeList = []
        for ROIndex in range(len(phaseValueByROIList)):

            phase = phaseValueByROIList[ROIndex][breathingSignalSampleIndex]
            if phase[0] == 'I':
                phaseList.append((phase[1]+phase[2])/10)
                amplitudeList.append(1)
            elif phase[0] == 'E':
                phaseList.append(phase[1]/10)
                amplitudeList.append(phase[2])

        ## generate the deformation field combining the fields for each points and phase info
        df1, wm = generateDeformationFromTrackers(model, phaseList, amplitudeList, ROIList)
        ## apply it to the midp image
        im1 = df1.deformImage(model.midp, fillValue='closest', outputType=outputType)
        im1.name = dynseq.name + '_' + str(breathingSignalSampleIndex)
        ## add the image to the dynamic sequence
        dynseq.dyn3DImageList.append(im1)

    return dynseq

## -------------------------------------------------------------------------------
def generateDeformationListFromBreathingSignalsAndModel(model, signalList, ROIList, signalIdxUsed=[0, 0], dimensionUsed='Z', outputType=np.float32):

    """
    Generate a dynamic 3D sequence from a model, in which each given ROI follows its breathing signal

    Parameters
    ----------
    model : Dynamic3DModel
        The dynamic 3D model that will be used to create the images of the resulting sequence
    signalList : list
        list of breathing signals as 1D numpy arrays
    ROIList : list
        list of points as [X, Y, Z] or (X, Y, Z) --> does not work with ROI's as masks or struct
    dimensionUsed : str
        X, Y, Z or norm, the dimension used to compare the breathing signals with the model deformation values
    outputType : pixel data type (np.float32, np.uint16, etc)

    Returns
    -------
    dynseq (Dynamic3DSequence): a new sequence containing the generated images

    """

    if len(signalList) != len(ROIList):
        print('Numbers of signals and ROI do not match')
        return

    ## get displacement fields from velocity fields
    if model.deformationList[0].displacement == None:
        print('Compute displacement fields')
        for fieldIndex, field in enumerate(model.deformationList):
            print(fieldIndex)
            field.displacement = field.velocity.exponentiateField(outputType=outputType)

    if signalIdxUsed == [0, 0]:
        signalIdxUsed = [0, signalList[0].shape[0]]

    print('Signal indexes used', signalIdxUsed)

    ## loop over ROIs
    phaseValueByROIList = []
    for ROIndex, ROI in enumerate(ROIList):

        ## get model deformation values for the specified dimension at the ROI location
        modelDefValuesArray = getAverageModelValuesAroundPosition(ROI, model, dimensionUsed=dimensionUsed)

        # plt.figure()
        # plt.plot(modelDefValuesArray)
        # plt.show()

        ## get the midP value for the specified dimension
        meanPos = np.mean(modelDefValuesArray)  ## in case of synthetic signal use, this should be 0 ? this is not exactly 0 by using this mean on a particular dimension

        # split into ascent and descent subset for the ROI location
        ascentPart, ascentPartIndexes, descentPart, descentPartIndexes, amplitude = splitAscentDescentSubsets(modelDefValuesArray)

        phaseValueList = []
        ## loop over breathing signal samples
        for sampleIndex in range(signalIdxUsed[0], signalIdxUsed[1]):

            ## get the ascent or descent situation and compute the phase value for each sample
            ascentOrDescentCase = isAscentOrDescentCase(signalList[ROIndex], sampleIndex)

            if ascentOrDescentCase == "descending":
                phaseRatio = computePhaseRatio(signalList[ROIndex][sampleIndex], descentPart, descentPartIndexes, ascentOrDescentCase, meanPos)
            elif ascentOrDescentCase == "ascending":
                phaseRatio = computePhaseRatio(signalList[ROIndex][sampleIndex], ascentPart, ascentPartIndexes, ascentOrDescentCase, meanPos)
            ## add the resulting phase to the list for each breathing signal sample
            phaseValueList.append(phaseRatio)

        ## add the phaseValueList to the complete list for each ROI
        phaseValueByROIList.append(phaseValueList)

    ## At this point the phase information are computed, now the part where the images are created starts
    ## New empty dynamic 3D sequence is created
    # dynseq = Dynamic3DSequence()
    # dynseq.name = 'GeneratedFromBreathingSignal'
    deformationList = []

    ## loop over breathing signal sample
    for breathingSignalSampleIndex in range(len(phaseValueByROIList[0])):

        ## translate the phase infos into phase and amplitude lists
        phaseList = []
        amplitudeList = []
        for ROIndex in range(len(phaseValueByROIList)):

            phase = phaseValueByROIList[ROIndex][breathingSignalSampleIndex]
            if phase[0] == 'I':
                phaseList.append((phase[1]+phase[2])/10)
                amplitudeList.append(1)
            elif phase[0] == 'E':
                phaseList.append(phase[1]/10)
                amplitudeList.append(phase[2])

        ## generate the deformation field combining the fields for each points and phase info
        df1, wm = generateDeformationFromTrackers(model, phaseList, amplitudeList, ROIList)
        deformationList.append(df1)

    return deformationList

## -------------------------------------------------------------------------------
def splitAscentDescentSubsets(CTPhasePositions):
    """
    Split ...

    Parameters
    ----------
    CTPhasePositions :

    Returns
    -------
    ascentPart : the ...
    ascentPartIndexes
    descentPart
    descentPartIndexes
    amplitude
    """
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
    """
    TODO
    """
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
    """
    TODO
    """
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

