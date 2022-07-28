import numpy as np
import matplotlib.pyplot as plt
import time
import copy
from skimage.morphology import ball
from skimage.transform import AffineTransform

from Core.Data.DynamicData.dynamic3DSequence import Dynamic3DSequence
from Core.Data.DynamicData.breathingSignals import SyntheticBreathingSignal
from Core.Data.Images.ctImage import CTImage



def createSphere(size):

    sphere = ball(size)#*density
    # noise = np.random.normal(density, noiseVar, sphere.shape)

    return sphere


## ----------------------------------------------------------------------------------------
def createImmobileSpace(size=(50, 50, 50), backgroundDensity = -1000):

    # imobileSpace = np.ones(size)*backgroundDensity
    imobileSpace = np.full(size, backgroundDensity)
    imobileSpace[20:150, 20:80, :] = 0
    imobileSpace[30:70, 30:70, 20:] = -800
    imobileSpace[100:140, 30:70, 20:] = -800
    imobileSpace[45:55, 45:55, 30:40] = 0

    return imobileSpace


## ----------------------------------------------------------------------------------------
def createSyntheticSequence(spaceSize, targetSize, targetDensity, targetNoiseVar, motionSignal, backgroundDensity = -1000, backgroundNoiseVar = 50, imobileSpace=False):

    spaceNoise = np.random.normal(backgroundDensity, backgroundNoiseVar, spaceSize)

    if imobileSpace:
        space = createImmobileSpace(size=spaceSize) * spaceNoise
    else:
        space = spaceNoise

    spaceCenter = np.round(np.array(space.shape)/2).astype(np.int16)

    dyn3DSeq = Dynamic3DSequence()

    targetMask = createSphere(targetSize)
    targetDensity = np.random.normal(targetDensity, targetNoiseVar, targetMask.shape)
    targetDensity[targetMask == 0] = np.random.normal(backgroundDensity, backgroundNoiseVar, targetDensity[targetMask == 0].shape)

    targetSize = np.array(targetMask.shape)

    for point in motionSignal.breathingSignal:
        spaceCopy = copy.copy(space)
        spaceCopy[spaceCenter[0]-int(targetSize[0]/2): spaceCenter[0]-int(targetSize[0]/2)+targetSize[0],
                spaceCenter[1]-int(targetSize[1]/2): spaceCenter[1]-int(targetSize[1]/2)+targetSize[1],
                spaceCenter[2]-int(targetSize[2]/2) + int(point): spaceCenter[2]-int(targetSize[2]/2)+targetSize[2] + int(point)] = targetDensity

        dyn3DSeq.dyn3DImageList.append(CTImage(imageArray=spaceCopy, name='fixed', origin=[0, 0, 0], spacing=[1, 1, 1]))

    return dyn3DSeq


## ----------------------------------------------------------------------------------------

simulationTime = 10
amplitude = 20
samplingPeriod = 0.2
targetDensity = -200
targetNoiseVar = 70
targetSize = 10
spaceSize = (100, 100, 100)

newSignal = SyntheticBreathingSignal(amplitude=amplitude,
                                     breathingPeriod=4,
                                     meanNoise=0,
                                     varianceNoise=1,
                                     samplingPeriod=samplingPeriod,
                                     simulationTime=simulationTime,
                                     coeffMin=0,
                                     coeffMax=0,
                                     meanEvent=3/30,
                                     meanEventApnea=0)

newSignal.generate1DBreathingSignal()

plt.figure()
plt.plot(newSignal.timestamps, newSignal.breathingSignal)
plt.show()

imgSeq = createSyntheticSequence(spaceSize, targetSize, targetDensity, targetNoiseVar, newSignal)

print('Sequence of', len(imgSeq.dyn3DImageList), 'images is created')

plt.figure()
for img in imgSeq.dyn3DImageList:

    plt.imshow(img.imageArray[:, int(img.gridSize[1]/2), :])
    plt.draw()
    plt.pause(samplingPeriod)
    plt.clf()
