import numpy as np
import matplotlib.pyplot as plt
import logging

from opentps.core.data.images import CTImage
from opentps.core.data.images import ROIMask
from opentps.core.processing.imageProcessing.syntheticDeformation import applyBaselineShift

logger = logging.getLogger(__name__)

if __name__ == '__main__':

    # GENERATE SYNTHETIC CT IMAGE AND TUMOR MASK
    im = np.full((170, 170, 100), -1000)
    im[20:150, 70:130, :] = 0
    im[30:70, 80:120, 20:] = -800
    im[100:140, 80:120, 20:] = -800
    im[45:55, 95:105, 30:40] = 0 #tumor
    im[80:90, 95:105, :] = 800
    im[:, 130:135, :] = 100 #couch
    ct = CTImage(imageArray=im, origin=[0, 0, 0], spacing=[1, 2, 3])
    mask = np.full((170, 170, 100), 0)
    mask[45:55, 95:105, 30:40] = 1
    roi = ROIMask(imageArray=mask, origin=[0, 0, 0], spacing=[1, 2, 3])

    # APPLY BASELINE SHIFT
    ctDef1, maskDef1 = applyBaselineShift(ct, roi, [5, 5, 5])
    ctDef2, maskDef2 = applyBaselineShift(ct, roi, [-5, -5, -5])
    ctDef3, maskDef3 = applyBaselineShift(ct, roi, [0, 0, -20])

    # DISPLAY RESULTS
    fig, ax = plt.subplots(2, 4)
    fig.tight_layout()
    y_slice = 100
    z_slice = 35 #round(ct.imageArray.shape[2] / 2) - 1
    ax[0,0].imshow(ct.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,0].title.set_text('CT')
    ax[0,1].imshow(ctDef1.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,1].title.set_text('baseline shift 5,5,5')
    ax[0,2].imshow(ctDef2.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,2].title.set_text('baseline shift -5,-5,-5')
    ax[0,3].imshow(ctDef3.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,3].title.set_text('baseline shift 0,0,-20')

    ax[1,0].imshow(ct.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,0].title.set_text('CT')
    ax[1,1].imshow(ctDef1.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,1].title.set_text('baseline shift 5,5,5')
    ax[1,2].imshow(ctDef2.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,2].title.set_text('baseline shift -5,-5,-5')
    ax[1,3].imshow(ctDef3.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,3].title.set_text('baseline shift 0,0,-20')

    plt.show()

    print('done')
    print(' ')