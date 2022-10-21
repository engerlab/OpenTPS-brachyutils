import numpy as np
import matplotlib.pyplot as plt
import time
import logging

from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel
from opentps.core.data.dynamicData._dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.images import CTImage
from opentps.core.examples.syntheticData import *

logger = logging.getLogger(__name__)

def run():

    # GENERATE SYNTHETIC 4D INPUT SEQUENCE
    CT4D = createSynthetic4DCT()

    # GENERATE MIDP
    Model4D = Dynamic3DModel()
    startTime = time.time()
    Model4D.computeMidPositionImage(CT4D, 0, tryGPU=True)
    stopTime = time.time()
    print('midP computed in ', np.round(stopTime - startTime, 2), 'seconds')

    # GENERATE ADDITIONAL PHASES
    im1 = Model4D.generate3DImage(0.5/4, amplitude=1, tryGPU=False)
    im2 = Model4D.generate3DImage(2/4, amplitude=2.0, tryGPU=False)
    im3 = Model4D.generate3DImage(2/4, amplitude=0.5, tryGPU=False)

    # CHECK RESULTS
    assert (Model4D.midp.imageArray[50,100,35] == 0) & (Model4D.midp.imageArray[50,100,33] == -800), f"Wrong midp"
    assert (im1.imageArray[50, 100, 33] == 0) & (im1.imageArray[50, 100, 31] < -600), f"Wrong generated phase 0.5"
    assert (im2.imageArray[50, 100, 43] == 0) & (im2.imageArray[50, 100, 41] < -600), f"Wrong generated phase 2 with amplitude 2"

    # DISPLAY RESULTS
    fig, ax = plt.subplots(2, 4)
    fig.tight_layout()
    y_slice = 95
    ax[0,0].imshow(CT4D.dyn3DImageList[0].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,0].title.set_text('Phase 0')
    ax[0,1].imshow(CT4D.dyn3DImageList[1].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,1].title.set_text('Phase 1')
    ax[0,2].imshow(CT4D.dyn3DImageList[2].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,2].title.set_text('Phase 2')
    ax[0,3].imshow(CT4D.dyn3DImageList[3].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,3].title.set_text('Phase 3')
    ax[1,0].imshow(Model4D.midp.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,0].title.set_text('MidP image')
    ax[1,1].imshow(im1.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,1].title.set_text('phase 0.5 - amplitude 1')
    ax[1,2].imshow(im2.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,2].title.set_text('phase 2 - amplitude 2')
    ax[1,3].imshow(im3.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,3].title.set_text('phase 2 - amplitude 0.5')

    plt.show()

    print('MidP example completed')

if __name__ == "__main__":
    run()