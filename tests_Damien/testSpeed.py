from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
from Core.Processing.DeformableDataAugmentationToolBox.generateRandomSamplesFromModel import generateRandomImagesFromModel
import os
from pathlib import Path
import cProfile
import time
import numpy as np
import concurrent

testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')

## read a serialized dynamic sequence
# dataPath = testDataPath + "superLightDynSeqWithMod.p"
dataPath = '/home/damien/Desktop/Patient0/Patient0_Model_bodyCropped.p'
dynMod = loadDataStructure(dataPath)[0]

pr = cProfile.Profile()
pr.enable()

startTime = time.time()
imageList = generateRandomImagesFromModel(dynMod, numberOfSamples=5, ampDistribution='gaussian', tryGPU=True)
print('first test done in ', np.round(time.time()- startTime, 2))

pr.disable()
pr.print_stats(sort="cumulative")
#
# imageList = []
#
# test = [0, 0, 0, 0, 0]
# # processes = []
# # for deformationIndex, deformation in enumerate(deformationList):
# print('start multi process deformation')
# startTime = time.time()
# with concurrent.futures.ProcessPoolExecutor() as executor:
#
#     results = [executor.submit(generateRandomSamplesFromModel, dynMod, tryGPU=False) for _ in range(5)]
#     # imageList += results
# print('second test done in ', np.round(time.time()- startTime, 2))