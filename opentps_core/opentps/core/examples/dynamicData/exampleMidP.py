import numpy as np
import matplotlib.pyplot as plt
import time
import logging

from opentps.core.data.dynamicData.dynamic3DModel import Dynamic3DModel
from opentps.core.data.dynamicData.dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.images import CTImage

logger = logging.getLogger(__name__)

if __name__ == '__main__':

    # GENERATE SYNTHETIC 4D INPUT SEQUENCE
    CT4D = Dynamic3DSequence()
    phase0 = np.full((100, 100, 100), -1000)
    phase0[20:80,20:80,:] = 0
    phase0[30:70,30:70,20:] = -800
    phase0[45:55,45:55,30:40] = 0
    CT4D.dyn3DImageList.append(CTImage(imageArray=phase0, name='fixed', origin=[0,0,0], spacing=[1,1,1]))
    phase1 = np.full((100, 100, 100), -1000)
    phase1[20:80,20:80,:] = 0
    phase1[30:70,30:70,30:] = -800
    phase1[42:52,45:55,40:50] = 0
    CT4D.dyn3DImageList.append(CTImage(imageArray=phase1, name='fixed', origin=[0,0,0], spacing=[1,1,1]))
    phase2 = np.full((100, 100, 100), -1000)
    phase2[20:80,20:80,:] = 0
    phase2[30:70,30:70,40:] = -800
    phase2[45:55,45:55,50:60] = 0
    CT4D.dyn3DImageList.append(CTImage(imageArray=phase2, name='fixed', origin=[0,0,0], spacing=[1,1,1]))
    phase3 = np.full((100, 100, 100), -1000)
    phase3[20:80,20:80,:] = 0
    phase3[30:70,30:70,30:] = -800
    phase3[48:58,45:55,40:50] = 0
    CT4D.dyn3DImageList.append(CTImage(imageArray=phase3, name='fixed', origin=[0,0,0], spacing=[1,1,1]))

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

    # DISPLAY RESULTS
    fig, ax = plt.subplots(2, 4)
    fig.tight_layout()
    y_slice = round(Model4D.midp.imageArray.shape[1]/2)-1
    ax[0,0].imshow(CT4D.dyn3DImageList[0].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,0].title.set_text('Phase 0')
    ax[0,1].imshow(CT4D.dyn3DImageList[1].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,1].title.set_text('Phase 1')
    ax[0,2].imshow(CT4D.dyn3DImageList[2].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,2].title.set_text('Phase 2')
    ax[0,3].imshow(CT4D.dyn3DImageList[3].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,3].title.set_text('Phase 3')
    ax[1,0].imshow(Model4D.midp.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,0].title.set_text('MidP python')
    ax[1,1].imshow(im1.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,1].title.set_text('phase 0.5 - amplitude 1')
    ax[1,2].imshow(im2.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,2].title.set_text('phase 2 - amplitude 2')
    ax[1,3].imshow(im3.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,3].title.set_text('phase 2 - amplitude 0.5')

    plt.show()

    print('done')
    print(' ')
