import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import logging
from opentps_core.opentps.core.logConfigParser import parseArgs

from opentps_core.opentps.core.data import CTImage
from opentps_core.opentps.core import applyThreshold
from opentps_core.opentps.core.Processing.Segmentation.segmentationCT import SegmentationCT

currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)
os.chdir(currentWorkingDir)

logger = logging.getLogger(__name__)

if __name__ == '__main__':

    options = parseArgs(sys.argv[1:])

    # GENERATE SYNTHETIC CT IMAGE
    im = np.full((170, 170, 100), -1000)
    im[20:150, 70:130, :] = 0
    im[30:70, 80:120, 20:] = -800
    im[100:140, 80:120, 20:] = -800
    im[45:55, 95:105, 30:40] = 0
    im[80:90, 95:105, :] = 800
    im[:, 130:135, :] = 100 #couch
    ct = CTImage(imageArray=im, name='fixed', origin=[0, 0, 0], spacing=[1, 2, 3])

    # APPLY THRESHOLD SEGMENTATION
    mask = applyThreshold(ct, -750)

    # APPLY CT BODY SEGMENTATION
    seg = SegmentationCT(ct)
    body = seg.segmentBody()
    bones = seg.segmentBones()
    lungs = seg.segmentLungs()

    # DISPLAY RESULTS
    fig, ax = plt.subplots(2, 5)
    fig.tight_layout()
    y_slice = 100
    z_slice = 35 #round(ct.imageArray.shape[2] / 2) - 1
    ax[0,0].imshow(ct.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,0].title.set_text('CT')
    ax[0,1].imshow(mask.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=0, vmax=1)
    ax[0,1].title.set_text('Threshold')
    ax[0,2].imshow(body.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=0, vmax=1)
    ax[0,2].title.set_text('Body')
    ax[0,3].imshow(bones.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=0, vmax=1)
    ax[0,3].title.set_text('Bones')
    ax[0,4].imshow(lungs.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=0, vmax=1)
    ax[0,4].title.set_text('Lungs')

    ax[1,0].imshow(ct.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,0].title.set_text('CT')
    ax[1,1].imshow(mask.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=0, vmax=1)
    ax[1,1].title.set_text('Threshold')
    ax[1,2].imshow(body.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=0, vmax=1)
    ax[1,2].title.set_text('Body')
    ax[1,3].imshow(bones.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=0, vmax=1)
    ax[1,3].title.set_text('Bones')
    ax[1,4].imshow(lungs.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=0, vmax=1)
    ax[1,4].title.set_text('Lungs')

    plt.show()

    print('done')
    print(' ')