import os
import sys
import math
import numpy as np
import matplotlib.pyplot as plt
import logging
from logConfigParser import parseArgs

from opentps_core.opentps.core.Processing.ImageSimulation.ForwardProjectorTigre import forwardProjectionTigre
from opentps_core.opentps.core.IO import loadDataStructure

currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)
os.chdir(currentWorkingDir)

logger = logging.getLogger(__name__)

if __name__ == '__main__':

    options = parseArgs(sys.argv[1:])

    # Get the current working directory, its parent, then add the testData folder at the end of it
    testDataPath = os.path.join(currentWorkingDir, 'testData/')

    # read a serialized dynamic sequence
    dataPath = testDataPath + "lightDynSeq.p"
    dynSeq = loadDataStructure(dataPath)[0]

    # Compute projections
    angles = np.array([0,90,180])*2*math.pi/360
    DRR_no_noise = forwardProjectionTigre(dynSeq.dyn3DImageList[0], angles, axis='Z', poissonNoise=None, gaussianNoise=None)
    DRR_realistic = forwardProjectionTigre(dynSeq.dyn3DImageList[0], angles, axis='Z')
    DRR_high_noise = forwardProjectionTigre(dynSeq.dyn3DImageList[0], angles, axis='Z', poissonNoise=3e4, gaussianNoise=30)

    # Compute error
    error_realistic_projections = np.abs(DRR_realistic-DRR_no_noise)
    error_realistic_projections_high_noise = np.abs(DRR_high_noise-DRR_no_noise)

    # Display results
    fig, ax = plt.subplots(3, 5)
    ax[0,0].imshow(DRR_no_noise[0][::-1, ::1], cmap='gray', origin='upper', vmin=np.min(DRR_no_noise), vmax=np.max(DRR_no_noise))
    ax[0,1].imshow(DRR_realistic[0][::-1, ::1], cmap='gray', origin='upper', vmin=np.min(DRR_no_noise), vmax=np.max(DRR_no_noise))
    ax[0,2].imshow(error_realistic_projections[0][::-1, ::1], cmap='gray', origin='upper', vmin=0, vmax=np.max(DRR_no_noise)/100)
    ax[0,3].imshow(DRR_high_noise[0][::-1, ::1], cmap='gray', origin='upper', vmin=np.min(DRR_no_noise), vmax=np.max(DRR_no_noise))
    ax[0,4].imshow(error_realistic_projections_high_noise[0][::-1, ::1], cmap='gray', origin='upper', vmin=0, vmax=np.max(DRR_no_noise)/100)
    ax[1,0].imshow(DRR_no_noise[1][::-1, ::1], cmap='gray', origin='upper', vmin=np.min(DRR_no_noise), vmax=np.max(DRR_no_noise))
    ax[1,1].imshow(DRR_realistic[1][::-1, ::1], cmap='gray', origin='upper', vmin=np.min(DRR_no_noise), vmax=np.max(DRR_no_noise))
    ax[1,2].imshow(error_realistic_projections[1][::-1, ::1], cmap='gray', origin='upper', vmin=0, vmax=np.max(DRR_no_noise)/100)
    ax[1,3].imshow(DRR_high_noise[1][::-1, ::1], cmap='gray', origin='upper', vmin=np.min(DRR_no_noise), vmax=np.max(DRR_no_noise))
    ax[1,4].imshow(error_realistic_projections_high_noise[1][::-1, ::1], cmap='gray', origin='upper', vmin=0, vmax=np.max(DRR_no_noise)/100)
    ax[2,0].imshow(DRR_no_noise[2][::-1, ::1], cmap='gray', origin='upper', vmin=np.min(DRR_no_noise), vmax=np.max(DRR_no_noise))
    ax[2,1].imshow(DRR_realistic[2][::-1, ::1], cmap='gray', origin='upper', vmin=np.min(DRR_no_noise), vmax=np.max(DRR_no_noise))
    ax[2,2].imshow(error_realistic_projections[2][::-1, ::1], cmap='gray', origin='upper', vmin=0, vmax=np.max(DRR_no_noise)/100)
    ax[2,3].imshow(DRR_high_noise[2][::-1, ::1], cmap='gray', origin='upper', vmin=np.min(DRR_no_noise), vmax=np.max(DRR_no_noise))
    ax[2,4].imshow(error_realistic_projections_high_noise[2][::-1, ::1], cmap='gray', origin='upper', vmin=0, vmax=np.max(DRR_no_noise)/100)
    ax[0,0].title.set_text('Perfect DRR')
    ax[0,1].title.set_text('DRR with moderate noise')
    ax[0,2].title.set_text('Moderate noise')
    ax[0,3].title.set_text('DRR with high noise')
    ax[0,4].title.set_text('High noise')
    plt.show()

    print('done')