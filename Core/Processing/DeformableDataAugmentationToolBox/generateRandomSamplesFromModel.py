import matplotlib.pyplot as plt
import numpy as np
import time

def generateRandomSamplesFromModel(model, numberOfSamples = 1, amplitudeRange = [0.8, 1.2], phaseRange = [0, 100], ampDistribution="uniform", tryGPU=True):
    """
    should we call this a "uniform" sample ? to differentiate with the weight maps combination ?
    """

    sampleImageList = []

    # distriTestList = []
    # phaseTestList = []

    for i in range(numberOfSamples):

        startTime = time.time()

        if ampDistribution == 'uniform':
            ran = np.random.random_sample()
            amplitude = (amplitudeRange[1] - amplitudeRange[0]) * ran + amplitudeRange[0]

        elif ampDistribution == 'gaussian':
            mu = amplitudeRange[0] + (amplitudeRange[1] - amplitudeRange[0])/2
            sigma = (amplitudeRange[1] - amplitudeRange[0])/2
            amplitude = mu + sigma * np.random.randn()

        phase = np.random.random_sample()

        # distriTestList.append(amplitude)
        # phaseTestList.append(phase)

    # plt.figure()
    #
    # plt.subplot(1, 2, 1)
    # n, bins, patches = plt.hist(distriTestList, 50, density=True, facecolor='g', alpha=0.75)
    # plt.grid(True)
    #
    # plt.subplot(1, 2, 2)
    # n2, bins2, patches2 = plt.hist(phaseTestList, 50, density=True, facecolor='g', alpha=0.75)
    # plt.grid(True)
    #
    # plt.show()

        sampleImageList.append(model.generate3DImage(phase, amplitude=amplitude, tryGPU=tryGPU))
        print('sample', str(i), 'took', np.round((time.time() - startTime), 2), 'sec to create.', 'GPU used =', tryGPU)

    return sampleImageList

def generateRandomDeformationsFromModel(model, numberOfSamples = 1, amplitudeRange = [0.8, 1.2], phaseRange = [0, 100], ampDistribution="uniform"):

    ## this is the same as above but to generate random velocity fields samples --> to deform images AND contours and save the field for example

    return 0