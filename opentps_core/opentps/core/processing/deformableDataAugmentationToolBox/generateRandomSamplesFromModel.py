import matplotlib.pyplot as plt
import numpy as np
import time

def generateRandomImagesFromModel(model, numberOfSamples = 1, amplitudeRange = [0.8, 1.2], ampDistribution="uniform", tryGPU=True, outputType=np.int16):
    """
    generate random images from a model

    parameters
    ----------
    model : DeformableModel
        the model to generate the images from
    numberOfSamples : int
        number of images to generate
    amplitudeRange : list of 2 floats
        range of the amplitude of the deformation
    ampDistribution : string
        distribution of the amplitude of the deformation
    tryGPU : bool
        try to use the GPU
    outputType : numpy type
        type of the output image

    returns
    -------
    sampleImageList : list of numpy arrays
        list of the generated images
    """
    #should we call this a "uniform" sample ? to differentiate with the weight maps combination ?

    sampleImageList = []

    deformationSampleList = generateRandomDeformationsFromModel(model, numberOfSamples=numberOfSamples, amplitudeRange=amplitudeRange, ampDistribution=ampDistribution)
    for deform in deformationSampleList:
        im1 = deform.deformImage(model.midp, fillValue='closest', outputType=outputType, tryGPU=tryGPU)
        sampleImageList.append(im1)

    return sampleImageList

def generateRandomDeformationsFromModel(model, numberOfSamples = 1, amplitudeRange = [0.8, 1.2], ampDistribution="uniform"):
    """
    generate random deformations from a model

    parameters
    ----------
    model : DeformableModel
        the model to generate the deformations from
    numberOfSamples : int
        number of deformations to generate
    amplitudeRange : list of 2 floats
        range of the amplitude of the deformation
    ampDistribution : string
        distribution of the amplitude of the deformation

    returns
    -------
    sampleDeformationList : list of Deformation
        list of the generated deformations
    """

    #should we call this a "uniform" sample ? to differentiate with the weight maps combination ?

    sampleDeformationList = []

    # distriTestList = []
    # phaseTestList = []

    for i in range(numberOfSamples):

        startTime = time.time()

        if ampDistribution == 'uniform':
            ran = np.random.random_sample()
            amplitude = (amplitudeRange[1] - amplitudeRange[0]) * ran + amplitudeRange[0]

        elif ampDistribution == 'gaussian':
            mu = amplitudeRange[0] + (amplitudeRange[1] - amplitudeRange[0]) / 2
            sigma = (amplitudeRange[1] - amplitudeRange[0]) / 2
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

        sampleDeformationList.append(model.generate3DDeformation(phase, amplitude=amplitude))

    return sampleDeformationList
