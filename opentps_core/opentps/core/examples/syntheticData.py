import numpy as np
import matplotlib.pyplot as plt
from opentps.core.data.dynamicData.dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._roiMask import ROIMask


def createSynthetic3DCT(diaphragmPos = 20, targetPos = [45, 95, 30], returnTumorMaks = False):
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

    if returnTumorMaks:
        mask = np.full((170, 170, 100), 0)
        mask[45:55, 95:105, 30:40] = 1
        roi = ROIMask(imageArray=mask, origin=[0, 0, 0], spacing=[1, 1, 2])

        return ct, roi

    else:
        return ct


def createSynthetic4DCT(returnTumorMaks = False):

    # GENERATE SYNTHETIC 4D INPUT SEQUENCE
    CT4D = Dynamic3DSequence()
    # phase0 = np.full((170, 100, 100), -1000)
    # phase0[20:150, 20:80, :] = 0
    # phase0[30:70, 30:70, 20:] = -800
    # phase0[100:140, 30:70, 20:] = -800
    # phase0[80:90, 45:55, :] = 800
    # phase1 = phase0.copy()
    # phase2 = phase0.copy()
    # phase3 = phase0.copy()
    # phase0[45:55, 45:55, 30:40] = 0
    phase0 = createSynthetic3DCT(targetPos=[45, 95, 30], diaphragmPos=20)
    # phase1[30:70, 30:70, 20:25] = 0
    # phase1[100:140, 30:70, 20:25] = 0
    # phase1[42:52, 45:55, 35:45] = 0
    phase1 = createSynthetic3DCT(targetPos=[42, 95, 35], diaphragmPos=25)
    # phase2[30:70, 30:70, 20:30] = 0
    # phase2[100:140, 30:70, 20:30] = 0
    # phase2[45:55, 45:55, 40:50] = 0
    phase2 = createSynthetic3DCT(targetPos=[45, 95, 40], diaphragmPos=30)
    # phase3[30:70, 30:70, 20:25] = 0
    # phase3[100:140, 30:70, 20:25] = 0
    # phase3[48:58, 45:55, 35:45] = 0
    phase3 = createSynthetic3DCT(targetPos=[48, 95, 35], diaphragmPos=25)
    # CT4D.dyn3DImageList.append(CTImage(imageArray=phase0, name='fixed', origin=[0,0,0], spacing=[1,1,1]))
    # CT4D.dyn3DImageList.append(CTImage(imageArray=phase1, name='fixed', origin=[0,0,0], spacing=[1,1,1]))
    # CT4D.dyn3DImageList.append(CTImage(imageArray=phase2, name='fixed', origin=[0,0,0], spacing=[1,1,1]))
    # CT4D.dyn3DImageList.append(CTImage(imageArray=phase3, name='fixed', origin=[0,0,0], spacing=[1,1,1]))
    CT4D.dyn3DImageList = [phase0, phase1, phase2, phase3]

    # # DISPLAY RESULTS
    # fig, ax = plt.subplots(1, 4)
    # fig.tight_layout()
    # y_slice = 100
    #
    # ax[0].imshow(CT4D.dyn3DImageList[0].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper',
    #                 vmin=-1000, vmax=1000)
    # ax[0].title.set_text('Phase 0')
    # ax[1].imshow(CT4D.dyn3DImageList[1].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper',
    #                 vmin=-1000, vmax=1000)
    # ax[1].title.set_text('Phase 1')
    # ax[2].imshow(CT4D.dyn3DImageList[2].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper',
    #                 vmin=-1000, vmax=1000)
    # ax[2].title.set_text('Phase 2')
    # ax[3].imshow(CT4D.dyn3DImageList[3].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper',
    #                 vmin=-1000, vmax=1000)
    # ax[3].title.set_text('Phase 3')
    #
    # plt.show()

    return CT4D