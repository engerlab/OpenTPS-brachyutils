import numpy as np
import matplotlib.pyplot as plt
import logging

from opentps.core.data.images import CTImage
from opentps.core.data.images import ROIMask
from opentps.core.processing.imageProcessing.syntheticDeformation import applyBaselineShift
from opentps.core.examples.syntheticData import *

logger = logging.getLogger(__name__)

def run():

    # GENERATE SYNTHETIC CT IMAGE AND TUMOR MASK
    ct, roi = createSynthetic3DCT(returnTumorMask=True)

    # APPLY BASELINE SHIFT
    ctDef1, maskDef1 = applyBaselineShift(ct, roi, [4, 4, 4])
    ctDef2, maskDef2 = applyBaselineShift(ct, roi, [-4, -4, -4])
    ctDef3, maskDef3 = applyBaselineShift(ct, roi, [0, 0, -16])

    # CHECK RESULTS
    assert (ctDef1.imageArray[58, 108, 41] > -100) & (ctDef1.imageArray[49, 99, 31] < -700), f"Error for baseline shift +4,+4,+4"
    assert (ctDef2.imageArray[41, 91, 28] > -100) & (ctDef2.imageArray[50, 100, 38] < -700), f"Error for baseline shift -4,-4,-4"
    assert (ctDef3.imageArray[50, 100, 23] > -100) & (ctDef3.imageArray[50, 100, 33] < -700), f"Error for baseline shift 0,0,-16"

    # DISPLAY RESULTS
    fig, ax = plt.subplots(2, 4)
    fig.tight_layout()
    y_slice = 100
    z_slice = 35 #round(ct.imageArray.shape[2] / 2) - 1
    ax[0,0].imshow(ct.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,0].title.set_text('CT')
    ax[0,1].imshow(ctDef1.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,1].title.set_text('baseline shift 4,4,4')
    ax[0,2].imshow(ctDef2.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,2].title.set_text('baseline shift -4,-4,-4')
    ax[0,3].imshow(ctDef3.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,3].title.set_text('baseline shift 0,0,-16')

    ax[1,0].imshow(ct.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,0].title.set_text('CT')
    ax[1,1].imshow(ctDef1.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,1].title.set_text('baseline shift 4,4,4')
    ax[1,2].imshow(ctDef2.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,2].title.set_text('baseline shift -4,-4,-4')
    ax[1,3].imshow(ctDef3.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,3].title.set_text('baseline shift 0,0,-16')

    plt.show()

    print('Baseline shift example completed')

if __name__ == "__main__":
    run()