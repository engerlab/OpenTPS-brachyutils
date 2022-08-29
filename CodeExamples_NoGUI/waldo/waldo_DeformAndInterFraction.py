# -*- coding: utf-8 -*-
"""
Created on Thu Jun 30 10:36:12 2022

@author: grotsartdehe
"""

import matplotlib.pyplot as plt
import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)

import math
import time
import numpy as np 
import copy
from numpy.random import uniform as unif


from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
from Core.Data.DynamicData.breathingSignals import SyntheticBreathingSignal
from Core.Processing.DeformableDataAugmentationToolBox.generateDynamicSequencesFromModel import generateDeformationListFromBreathingSignalsAndModel
from Core.Processing.DeformableDataAugmentationToolBox.modelManipFunctions import *
from Core.Processing.DeformableDataAugmentationToolBox.interFractionChanges import shrinkOrgan, translateData, rotateData
from Core.Processing.ImageProcessing.resampler3D import *
from Core.Processing.Segmentation.segmentation3D import *
from Core.Processing.ImageProcessing.syntheticDeformation import applyBaselineShift
from Core.Processing.ImageSimulation.multiProcForkMethods import multiProcDRRs
from Core.Processing.DeformableDataAugmentationToolBox.multiProcSpawnMethods import multiProcDeform


## ------------------------------------------------------------------------------------

if __name__ == '__main__':

    organ = 'lung'
    patientFolder = 'Patient_12'
    patientComplement = '/1/FDG1'
    basePath = '/DATA2/public/'

    ## parameters selection ------------------------------------

    ## sequence duration, sampling and signal's regularity
    regularityIndex = 1
    numberOfSequences = 1
    numberOfImages = 5
    sequenceDurationInSecs = 5#205
    samplingFrequency = 5
    #subSequenceSize = 20
    outputSize = [64, 64]
    GPUNumber = 0
    ## ROI choice and crop options 
    bodyContourToUse = 'patient'#'external'#'Body'
    targetContourToUse = 'gtv t'#'GTVp'#'GTV T'
    lungContourToUse = 'R lung'
    contourToAddShift = targetContourToUse
    """
    # interfraction changes parameters
    baselineShift = [-20, 0, 0]
    translation = [-20, 0, 10]
    rotation = [0, 5, 0]
    shrinkSize = [2, 2, 2]
    """
    croppingContoursUsedXYZ = [targetContourToUse, bodyContourToUse, targetContourToUse]
    isBoxHardCoded = False
    hardCodedBox = [[88, 451], [79, 322], [20, 157]]
    marginInMM = [50, 0, 100]

    # breathing signal parameters
    amplitude = 'model'
    breathingPeriod = 4
    meanNoise = 0
    samplingPeriod = 1 / samplingFrequency
    simulationTime = sequenceDurationInSecs
    
    # use Z - 0 for Coronal and Z - 90 for sagittal
    projAngle = 0
    projAxis = 'Z'

    # multiProcessing 
    maxMultiProcUse = 15
    subSequenceSize = maxMultiProcUse
    
    if regularityIndex == 1:
        regularityFolder = '/Regular'
    elif regularityIndex == 2:
        regularityFolder = '/Middle'
    elif regularityIndex == 3:
        regularityFolder = '/Irregular'
    else:
        print("Regularity index error. Choose an index between 1 and 3.")
    #number of experience to generate
    #one experience corresponds to 5 sequences
    for idxExp in range(1,2):
        resultFolder = regularityFolder + '/sim5k/Test/Training/exp' + str(idxExp) + '/'
        resultDataFolder = 'data/'
    
        dataPath = basePath + organ  + '/' + patientFolder + patientComplement + '/dynModAndROIs.p'#'/dynModAndROIs_bodyCropped.p'
        savingPath = basePath + organ  + '/' + patientFolder + patientComplement + resultFolder
    
        if not os.path.exists(savingPath):
            os.umask(0)
            os.makedirs(savingPath)  # Create a new directory because it does not exist
            os.makedirs(savingPath + resultDataFolder)  # Create a new directory because it does not exist
            print("New directory created to save the data: ", savingPath)
        try:
            import cupy
            import cupyx
            cupy.cuda.Device(GPUNumber).use()
        except:
            print('cupy not found.')
        
    
        ## Start the script ---------------------------------
        patient = loadDataStructure(dataPath)[0]
        dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]
        rtStruct = patient.getPatientDataOfType("RTStruct")[0]
    
        ## Get the ROI and mask on which we want to apply the motion signal
        print('Available ROIs')
        rtStruct.print_ROINames()
    
        gtvContour = rtStruct.getContourByName(targetContourToUse)
        GTVMask = gtvContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize,
                                           spacing=dynMod.midp.spacing)
        gtvBox = getBoxAroundROI(GTVMask)
    
        ## get the body contour to adjust the crop in the direction of the DRR projection
        bodyContour = rtStruct.getContourByName(bodyContourToUse)
        bodyMask = bodyContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize,
                                             spacing=dynMod.midp.spacing)
        bodyBox = getBoxAroundROI(bodyMask)
        print('Body Box from contour', bodyBox)
    
        ##Define the cropping box
        croppingBox = [[], [], []]
        for i in range(3):
            if croppingContoursUsedXYZ[i] == bodyContourToUse:
                croppingBox[i] = bodyBox[i]
            elif croppingContoursUsedXYZ[i] == targetContourToUse:
                croppingBox[i] = gtvBox[i]
        
        ## crop the model data using the box
        crop3DDataAroundBox(dynMod, croppingBox, marginInMM=marginInMM)
    
        ## get the mask in cropped version (the dynMod.midp is now cropped so its origin and gridSize has changed)
        GTVMask = gtvContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize,
                                           spacing=dynMod.midp.spacing)
    
        ## if you want to see the crop in the GUI you can save the data in cropped version
        saveSerializedObjects(patient, savingPath + 'croppedModelAndROIs')
    
        ## get the 3D center of mass of this ROI
        gtvCenterOfMass = gtvContour.getCenterOfMass(dynMod.midp.origin, dynMod.midp.gridSize, dynMod.midp.spacing)
        gtvCenterOfMassInVoxels = getVoxelIndexFromPosition(gtvCenterOfMass, dynMod.midp)
        print('Used ROI name', gtvContour.name)
        print('Used ROI center of mass :', gtvCenterOfMass)
        print('Used ROI center of mass in voxels:', gtvCenterOfMassInVoxels)
        
        dynModCopy = copy.deepcopy(dynMod)
        GTVMaskCopy = copy.deepcopy(GTVMask)
        for idxImg in range(numberOfImages):
            shrinkValue = unif(0,3)
            # interfraction changes parameters
            baselineShift = [unif(-5,5), unif(-5,5), unif(-5,5)]
            translation = [unif(-3,3), unif(-3,3), unif(-3,3)]
            rotation = [unif(-2,2), unif(-2,2), 0]
            shrinkSize = [shrinkValue+np.random.normal(0,0.5), shrinkValue+np.random.normal(0,0.5), shrinkValue+np.random.normal(0,0.5)]
            
            dynModCopy = copy.deepcopy(dynMod)
            GTVMaskCopy = copy.deepcopy(GTVMask)
        
            startTime = time.time()
        
            print('-' * 50)
            if contourToAddShift == targetContourToUse:
                print('Apply baseline shift of', baselineShift, 'to', contourToAddShift)
                dynModCopy, GTVMaskCopy = applyBaselineShift(dynModCopy, GTVMaskCopy, baselineShift)
            else:
                print('Not implemented in this script --> must use the get contour by name function')
        
            print('-' * 50)
            translateData(dynModCopy, translationInMM=translation)
            translateData(GTVMaskCopy, translationInMM=translation)
        
            print('-'*50)
            rotateData(dynModCopy, rotationInDeg=rotation)
            rotateData(GTVMaskCopy, rotationInDeg=rotation)
        
            print('-' * 50)
            dynModCopy, GTVMaskCopy, newMask3DCOM = shrinkOrgan(dynModCopy, GTVMaskCopy, shrinkSize=shrinkSize)
            #shrinkedDynMod.name = 'MidP_ShrinkedGTV'
        
            print('-' * 50)
        
            stopTime = time.time()
            print('time for data augmentation: ', stopTime-startTime)
            
            #patient.appendPatientData(shrinkedDynMod)
            #patient.appendPatientData(shrinkedOrganMask)
            
            if amplitude == 'model':
                ## to get amplitude from model !!! it takes some time because 10 displacement fields must be computed just for this
                modelValues = getAverageModelValuesAroundPosition(gtvCenterOfMass, dynModCopy, dimensionUsed='Z')
                amplitude = np.max(modelValues) - np.min(modelValues)
                valZ = modelValues
                valX = getAverageModelValuesAroundPosition(gtvCenterOfMass, dynModCopy, dimensionUsed='X')
                valY = getAverageModelValuesAroundPosition(gtvCenterOfMass, dynModCopy, dimensionUsed='Y')
                print("Dim X",gtvCenterOfMass[0]+np.max(valX),gtvCenterOfMass[0]+np.min(valX))
                print("Dim Y",gtvCenterOfMass[1]+np.max(valZ),gtvCenterOfMass[1]+np.min(valY))
                print("Dim Z",gtvCenterOfMass[2]+np.max(valZ),gtvCenterOfMass[2]+np.min(valZ))
                print('Amplitude of deformation at ROI center of mass', amplitude)
            
            for seqIdx in range(numberOfSequences):
                
                ## Signal creation
                if regularityIndex == 1:
                    varianceNoise = np.random.uniform(0.5,1.5)
                    coeffMin = 0.10
                    coeffMax = 0.15
                    meanEvent = 1/60
                    meanEventApnea = 0/120
                elif regularityIndex == 2:
                    varianceNoise = np.random.uniform(1.5,2.5)
                    coeffMin = 0.10
                    coeffMax = 0.45
                    meanEvent = 1/30
                    meanEventApnea = 0/120
                elif regularityIndex == 3:
                    varianceNoise = np.random.uniform(2.5,3.5)
                    coeffMin = 0.10
                    coeffMax = 0.45
                    meanEvent = 1/20
                    meanEventApnea = 1/120
                else:
                    print("Regularity index error. Choose an index between 1 and 3.")
                    
                newSignal = SyntheticBreathingSignal(amplitude=amplitude,
                                                     breathingPeriod=breathingPeriod,
                                                     meanNoise=meanNoise,
                                                     varianceNoise=varianceNoise,
                                                     samplingPeriod=samplingPeriod,
                                                     simulationTime=sequenceDurationInSecs,
                                                     coeffMin=coeffMin,
                                                     coeffMax=coeffMax,
                                                     meanEvent=meanEvent,
                                                     meanEventApnea=meanEventApnea)
            
                newSignal.generate1DBreathingSignal()
            
                pointList = [gtvCenterOfMass]
                pointVoxelList = [gtvCenterOfMassInVoxels]
                signalList = [newSignal.breathingSignal]
            
                saveSerializedObjects([signalList, pointList], savingPath + 'ROIsAndSignalObjects')
            
                ## to show signals and ROIs
                ## -------------------------------------------------------------
                prop_cycle = plt.rcParams['axes.prop_cycle']
                colors = prop_cycle.by_key()['color']
                plt.figure(figsize=(12, 6))
                signalAx = plt.subplot(2, 1, 2)
            
                for pointIndex, point in enumerate(pointList):
                    ax = plt.subplot(2, 2 * len(pointList), 2 * pointIndex + 1)
                    ax.set_title('Slice Y:' + str(pointVoxelList[pointIndex][1]))
                    ax.imshow(np.rot90(dynModCopy.midp.imageArray[:, pointVoxelList[pointIndex][1], :]))
                    ax.imshow(np.rot90(GTVMaskCopy.imageArray[:, pointVoxelList[pointIndex][1], :]), alpha=0.3)
                    ax.scatter([pointVoxelList[pointIndex][0]], [dynModCopy.midp.imageArray.shape[2] - pointVoxelList[pointIndex][2]],
                               c=colors[pointIndex], marker="x", s=100)
                    ax2 = plt.subplot(2, 2 * len(pointList), 2 * pointIndex + 2)
                    ax2.set_title('Slice Z:' + str(pointVoxelList[pointIndex][2]))
                    ax2.imshow(np.rot90(dynModCopy.midp.imageArray[:, :, pointVoxelList[pointIndex][2]], 3))
                    ax2.imshow(np.rot90(GTVMaskCopy.imageArray[:, :, pointVoxelList[pointIndex][2]], 3), alpha=0.3)
                    ax2.scatter([pointVoxelList[pointIndex][0]], [pointVoxelList[pointIndex][1]],
                               c=colors[pointIndex], marker="x", s=100)
                    signalAx.plot(newSignal.timestamps / 1000, signalList[pointIndex], c=colors[pointIndex])
            
                signalAx.set_xlabel('Time (s)')
                signalAx.set_ylabel('Deformation amplitude in Z direction (mm)')
                plt.savefig(savingPath + 'ROI_And_Signals_fig.pdf', dpi=300)
                plt.show()
            
                ## -------------------------------------------------------------
            
                sequenceSize = newSignal.breathingSignal.shape[0]
                print('Sequence Size =', sequenceSize, 'split by stack of ', subSequenceSize, '. Multiprocessing =', maxMultiProcUse)
            
                subSequencesIndexes = [subSequenceSize * i for i in range(math.ceil(sequenceSize / subSequenceSize))]
                subSequencesIndexes.append(sequenceSize)
                print('Sub sequences indexes', subSequencesIndexes)
            
                resultList = []
            
                if subSequenceSize > maxMultiProcUse:  ## re-adjust the subSequenceSize since this will be done in multi processing
                    subSequenceSize = maxMultiProcUse
                    print('SubSequenceSize put to', maxMultiProcUse, 'for multiprocessing.')
                    print('Sequence Size =', sequenceSize, 'split by stack of ', subSequenceSize, '. Multiprocessing =', maxMultiProcUse)
                    subSequencesIndexes = [subSequenceSize * i for i in range(math.ceil(sequenceSize / subSequenceSize))]
                    subSequencesIndexes.append(sequenceSize)
            
                startTime = time.time()
                for i in range(len(subSequencesIndexes) - 1):
                    print('Creating deformations for images', subSequencesIndexes[i], 'to', subSequencesIndexes[i + 1] - 1)
            
                    deformationList = generateDeformationListFromBreathingSignalsAndModel(dynModCopy,
                                                                                            signalList,
                                                                                            pointList,
                                                                                            signalIdxUsed=[subSequencesIndexes[i],
                                                                                                            subSequencesIndexes[
                                                                                                                i + 1]],
                                                                                            dimensionUsed='Z',
                                                                                            outputType=np.float32)
            
            
                    print('Start multi process deformation with', len(deformationList), 'deformations')
                    deformedImgMaskAnd3DCOMList = multiProcDeform(deformationList, dynModCopy, GTVMaskCopy)
                    
                    if i == 0:
                        plt.figure()
                        plt.imshow(deformedImgMaskAnd3DCOMList[-1][0].imageArray[:,:,50])
                        plt.imshow(deformedImgMaskAnd3DCOMList[-1][1].imageArray[:,:,50], alpha=0.5)
                        plt.savefig(savingPath + 'resultDeform.pdf', dpi=300)
            
                    print('Start multi process DRRs with', len(deformationList), 'pairs of image-mask')
                    projectionResults = []
                    projectionResults += multiProcDRRs(deformedImgMaskAnd3DCOMList, projAngle, projAxis, outputSize)
            
                    if i == 0:
                        plt.figure()
                        plt.imshow(projectionResults[-1][0])
                        plt.imshow(projectionResults[-1][1], alpha=0.5)
                        plt.savefig(savingPath + 'resultDRR.pdf', dpi=300)
                        plt.show()
            
                    ## add 3D center of mass in scanner coordinates to the result lists
                    for imgIndex in range(len(projectionResults)):
                        projectionResults[imgIndex].append(deformedImgMaskAnd3DCOMList[imgIndex][2])
            
                    resultList += projectionResults
                    print('ResultList lenght', len(resultList))
            
                stopTime = time.time()
            
                print('Script with multiprocessing. Sub-sequence size:', str(subSequenceSize), 'and total sequence size:', len(resultList), 'finished in', np.round(stopTime - startTime, 2) / 60, 'minutes')
                print(np.round((stopTime - startTime) / len(resultList), 2), 'sec per sample')
                
                #serieSavingPath = savingPath + resultDataFolder + patientFolder + f'_{sequenceSize}_DRRMasksAndCOM_serie_{seqIdx}'
                serieSavingPath = savingPath + resultDataFolder + patientFolder + f'_{sequenceSize}_DRRMasksAndCOM_serie_{idxImg}'
                saveSerializedObjects(resultList, serieSavingPath)
