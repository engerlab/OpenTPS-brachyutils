import os
import sys
currentWorkingDir = os.getcwd()
sys.path.append(currentWorkingDir)
import numpy as np
from pathlib import Path
import math

# from opentps.core.io.serializedObjectIO import loadDataStructure
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from opentps.core.data.dynamicData._breathingSignals import SyntheticBreathingSignal
from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel
from opentps.core.processing.deformableDataAugmentationToolBox.generateDynamicSequencesFromModel import generateDynSeqFromBreathingSignalsAndModel
from opentps.core.processing.imageProcessing.imageTransform3D import getVoxelIndexFromPosition
from opentps.core.processing.imageProcessing.resampler3D import resample
from opentps.core.examples.syntheticData import*

if __name__ == '__main__':

    CT4D = createSynthetic4DCT(numberOfPhases=10)
    # CT4D = resample(CT4D, gridSize=(80, 50, 50))

    plt.figure()
    fig = plt.gcf()
    def updateAnim(imageIndex):

        fig.clear()
        plt.imshow(np.rot90(CT4D.dyn3DImageList[imageIndex].imageArray[:, 95, :]))

    anim = FuncAnimation(fig, updateAnim, frames=len(CT4D.dyn3DImageList), interval=300)
    anim.save('D:/anim.gif')
    plt.show()

    # GENERATE MIDP
    dynMod = Dynamic3DModel()
    dynMod.computeMidPositionImage(CT4D, 0, tryGPU=True)

    print(dynMod.midp.origin, dynMod.midp.spacing, dynMod.midp.gridSize)
    print('Resample model image')
    dynMod = resample(dynMod, gridSize=(80, 50, 50))
    print('after resampling', dynMod.midp.origin, dynMod.midp.spacing, dynMod.midp.gridSize)

    # option 3
    for field in dynMod.deformationList:
        print('Resample model field')
        field.resample(spacing=dynMod.midp.spacing, gridSize=dynMod.midp.gridSize, origin=dynMod.midp.origin)
        print('after resampling', field.origin, field.spacing, field.gridSize)

    simulationTime = 10
    amplitude = 10

    newSignal = SyntheticBreathingSignal(amplitude=amplitude,
                                         breathingPeriod=4,
                                         meanNoise=0,
                                         varianceNoise=0,
                                         samplingPeriod=0.2,
                                         simulationTime=simulationTime,
                                         coeffMin=0,
                                         coeffMax=0,
                                         meanEvent=0/30,
                                         meanEventApnea=0)

    newSignal.generate1DBreathingSignal()
    linearIncrease = np.linspace(0.8, 10, newSignal.breathingSignal.shape[0])

    newSignal.breathingSignal = newSignal.breathingSignal * linearIncrease

    newSignal2 = SyntheticBreathingSignal()
    newSignal2.breathingSignal = -newSignal.breathingSignal

    signalList = [newSignal.breathingSignal, newSignal2.breathingSignal]

    pointRLung = np.array([50, 100, 50])
    pointLLung = np.array([120, 100, 50])

    ## get points in voxels --> for the plot, not necessary for the process example
    pointRLungInVoxel = getVoxelIndexFromPosition(pointRLung, dynMod.midp)
    pointLLungInVoxel = getVoxelIndexFromPosition(pointLLung, dynMod.midp)

    pointList = [pointRLung, pointLLung]
    pointVoxelList = [pointRLungInVoxel, pointLLungInVoxel]

    ## to show signals and ROIs
    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = prop_cycle.by_key()['color']
    plt.figure(figsize=(12, 6))
    signalAx = plt.subplot(2, 1, 2)
    for pointIndex, point in enumerate(pointList):
        ax = plt.subplot(2, 2 * len(pointList), 2 * pointIndex + 1)
        ax.set_title('Slice Y:' + str(pointVoxelList[pointIndex][1]))
        ax.imshow(np.rot90(dynMod.midp.imageArray[:, pointVoxelList[pointIndex][1], :]))
        ax.scatter([pointVoxelList[pointIndex][0]], [dynMod.midp.imageArray.shape[2] - pointVoxelList[pointIndex][2]], c=colors[pointIndex], marker="x", s=100)
        ax2 = plt.subplot(2, 2 * len(pointList), 2 * pointIndex + 2)
        ax2.set_title('Slice Z:' + str(pointVoxelList[pointIndex][2]))
        ax2.imshow(np.rot90(dynMod.midp.imageArray[:, :, pointVoxelList[pointIndex][2]], 3))
        ax2.scatter([pointVoxelList[pointIndex][0]], [pointVoxelList[pointIndex][1]], c=colors[pointIndex], marker="x", s=100)
        signalAx.plot(newSignal.timestamps / 1000, signalList[pointIndex], c=colors[pointIndex])
 
    signalAx.set_xlabel('Time (s)')
    signalAx.set_ylabel('Deformation amplitude in Z direction (mm)')
    plt.show()

    ## all in one seq version
    dynSeq = generateDynSeqFromBreathingSignalsAndModel(dynMod, signalList, pointList, dimensionUsed='Z', outputType=np.int16)
    dynSeq.breathingPeriod = newSignal.breathingPeriod
    dynSeq.timingsList = newSignal.timestamps

    ## save it as a serialized object
    # savingPath = 'C:/Users/damie/Desktop/' + 'PatientTest_InvLung'
    # saveSerializedObjects(dynSeq, savingPath)

    print('/'*80, '\n', '/'*80)

    plt.figure()
    fig = plt.gcf()
    def updateAnim(imageIndex):

        fig.clear()
        plt.imshow(np.rot90(dynSeq.dyn3DImageList[imageIndex].imageArray[:, 29, :]))

    anim = FuncAnimation(fig, updateAnim, frames=len(dynSeq.dyn3DImageList), interval=300)
    anim.save('D:/anim3.gif')
    plt.show()