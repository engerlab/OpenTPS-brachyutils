import numpy as np
import matplotlib.pyplot as plt
from opentps.core.data.dynamicData.dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._roiMask import ROIMask


def createSynthetic3DCT(diaphragmPos = 20, targetPos = [45, 95, 30], returnTumorMask = False):
    # GENERATE SYNTHETIC CT IMAGE
    # background
    im = np.full((170, 170, 100), -1000)
    im[20:150, 70:130, :] = 0
    # left lung
    im[30:70, 80:120, diaphragmPos:] = -800
    # right lung
    im[100:140, 80:120, diaphragmPos:] = -800
    # target
    im[targetPos[0]:targetPos[0]+10, targetPos[1]:targetPos[1]+10, targetPos[2]:targetPos[2]+10] = 0
    # vertebral column
    im[80:90, 95:105, :] = 800
    # couch
    im[:, 130:135, :] = 100
    ct = CTImage(imageArray=im, name='fixed', origin=[0, 0, 0], spacing=[1, 1, 2])

    if returnTumorMask:
        mask = np.full((170, 170, 100), 0)
        mask[45:55, 95:105, 30:40] = 1
        roi = ROIMask(imageArray=mask, origin=[0, 0, 0], spacing=[1, 1, 2])

        return ct, roi

    else:
        return ct


def createSynthetic4DCT(returnTumorMasks = False):

    # GENERATE SYNTHETIC 4D INPUT SEQUENCE
    CT4D = Dynamic3DSequence()

    if returnTumorMasks:
        phase0,  mask0 = createSynthetic3DCT(targetPos=[45, 95, 30], diaphragmPos=20, returnTumorMask=returnTumorMasks)
        phase1,  mask1 = createSynthetic3DCT(targetPos=[42, 95, 35], diaphragmPos=25, returnTumorMask=returnTumorMasks)
        phase2,  mask2 = createSynthetic3DCT(targetPos=[45, 95, 40], diaphragmPos=30, returnTumorMask=returnTumorMasks)
        phase3,  mask3 = createSynthetic3DCT(targetPos=[48, 95, 35], diaphragmPos=25, returnTumorMask=returnTumorMasks)

        maskList = [mask0, mask1, mask2, mask3]

    else:
        phase0 = createSynthetic3DCT(targetPos=[45, 95, 30], diaphragmPos=20)
        phase1 = createSynthetic3DCT(targetPos=[42, 95, 35], diaphragmPos=25)
        phase2 = createSynthetic3DCT(targetPos=[45, 95, 40], diaphragmPos=30)
        phase3 = createSynthetic3DCT(targetPos=[48, 95, 35], diaphragmPos=25)

    CT4D.dyn3DImageList = [phase0, phase1, phase2, phase3]

    # # DISPLAY RESULTS
    # fig, ax = plt.subplots(1, 4)
    # fig.tight_layout()
    # y_slice = 100
    # ax[0].imshow(CT4D.dyn3DImageList[0].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    # ax[0].title.set_text('Phase 0')
    # ax[1].imshow(CT4D.dyn3DImageList[1].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    # ax[1].title.set_text('Phase 1')
    # ax[2].imshow(CT4D.dyn3DImageList[2].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    # ax[2].title.set_text('Phase 2')
    # ax[3].imshow(CT4D.dyn3DImageList[3].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    # ax[3].title.set_text('Phase 3')
    # plt.show()

    if returnTumorMasks:
        return CT4D, maskList
    else:
        return CT4D