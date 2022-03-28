import numpy as np
import matplotlib.pyplot as plt

from Core.Data.Images.ctImage import CTImage
import Core.Processing.Segmentation.segmentation as segmentation
from Core.Processing.Segmentation.segmentationCT import SegmentationCT

if __name__ == '__main__':

    # GENERATE SYNTHETIC CT IMAGE
    im = np.full((170, 100, 100), -1000)
    im[20:150, 20:80, :] = 0
    im[30:70, 30:70, 20:] = -800
    im[100:140, 30:70, 20:] = -800
    im[45:55, 45:55, 30:40] = 0
    im[80:90, 45:55, :] = 800
    im[:, 80:85, :] = 100 #couch
    ct = CTImage(imageArray=im, name='fixed', origin=[0, 0, 0], spacing=[1, 1, 1])

    # APPLY THRESHOLD SEGMENTATION
    mask = segmentation.applyThreshold(ct, -750)

    # APPLY CT BODY SEGMENTATION
    seg = SegmentationCT(ct)
    body = seg.segmentBody()

    # DISPLAY RESULTS
    fig, ax = plt.subplots(2, 3)
    fig.tight_layout()
    y_slice = round(ct.imageArray.shape[1] / 2) - 1
    z_slice = 35 #round(ct.imageArray.shape[2] / 2) - 1
    ax[0,0].imshow(ct.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0,0].title.set_text('CT')
    ax[0,1].imshow(mask.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=0, vmax=1)
    ax[0,1].title.set_text('Threshold')
    ax[0,2].imshow(body.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=0, vmax=1)
    ax[0,2].title.set_text('Body')
    ax[1,0].imshow(ct.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1,0].title.set_text('CT')
    ax[1,1].imshow(mask.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=0, vmax=1)
    ax[1,1].title.set_text('Threshold')
    ax[1,2].imshow(body.imageArray[:, :, z_slice].T[::1, ::1], cmap='gray', origin='upper', vmin=0, vmax=1)
    ax[1,2].title.set_text('Body')

    plt.show()

    print('done')
    print(' ')