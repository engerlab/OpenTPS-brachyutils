from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
from Core.Processing.DeformableDataAugmentationToolBox.generateRandomSamplesFromModel import generateRandomSamplesFromModel
import os
from pathlib import Path
import cProfile

testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')

## read a serialized dynamic sequence
# dataPath = testDataPath + "superLightDynSeqWithMod.p"
dataPath = '/home/damien/Desktop/Patient0/Patient0_Model_bodyCropped.p'
dynMod = loadDataStructure(dataPath)[0]

pr = cProfile.Profile()
pr.enable()

imageList = generateRandomSamplesFromModel(dynMod, numberOfSamples=5, ampDistribution='gaussian', tryGPU=False)

pr.disable()
pr.print_stats(sort="cumulative")