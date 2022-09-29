import numpy as np
import matplotlib.pyplot as plt
import logging

from opentps.core.data.images import CTImage
from opentps.core.data.images import ROIMask
from opentps.core.processing.imageProcessing.syntheticDeformation import applyBaselineShift
from opentps.core.data.dynamicData.dynamic3DModel import Dynamic3DModel
from opentps.core.data.dynamicData.dynamic3DSequence import Dynamic3DSequence

logger = logging.getLogger(__name__)

if __name__ == '__main__':

    # GENERATE SYNTHETIC CT IMAGE
    im = np.full((210, 150, 100), -1000)
    im[20:190, 30:110, :] = 0
    im[30:90, 40:100, 20:] = -800 # right lung
    im[120:180, 40:100, 20:] = -800 # left lung
    im[100:110, 65:75, :] = 800 # spine
    im[:, 110:115, :] = 100 # couch
    ct = CTImage(imageArray=im, origin=[0, 0, 0], spacing=[1, 1, 1.5])

    # GENERATE MASK
    mask = np.full((210, 150, 100), 0)
    mask[52:68, 65:75, 35:55] = 1
    roi = ROIMask(imageArray=mask, origin=[0, 0, 0], spacing=[1, 1, 1.5])

    # GENERATE SYNTHETIC 4D INPUT SEQUENCE
    CT4D = Dynamic3DSequence()
    phase0 = ct.copy()
    phase0._imageArray[55:65, 65:75, 35:45] = 0  # tumor
    phase0._imageArray[30:90, 40:100, 15:20] = -800  # right lung3
    phase0._imageArray[120:180, 40:100, 15:20] = -800  # left lung
    CT4D.dyn3DImageList.append(phase0)
    phase1 = ct.copy()
    phase1._imageArray[52:62, 65:75, 40:50] = 0  # tumor
    CT4D.dyn3DImageList.append(phase1)
    phase2 = ct.copy()
    phase2._imageArray[55:65, 65:75, 45:55] = 0  # tumor
    phase2._imageArray[30:90, 40:100, 20:25] = 0
    phase2._imageArray[120:180, 40:100, 20:25] = 0
    CT4D.dyn3DImageList.append(phase2)
    phase3 = ct.copy()
    phase3._imageArray[58:68, 65:75, 40:50] = 0  # tumor
    CT4D.dyn3DImageList.append(phase3)

    # GENERATE MIDP
    Model = Dynamic3DModel()
    Model.computeMidPositionImage(CT4D, 0, tryGPU=True)

    # APPLY BASELINE SHIFT
    ModelShifted, maskShifted = applyBaselineShift(Model, roi, [5, 0, 10])

    # REGENERATE 4D SEQUENCES FROM MODELS
    CT4DRegen = Dynamic3DSequence()
    for i in range(len(CT4D.dyn3DImageList)):
        CT4DRegen.dyn3DImageList.append(Model.generate3DImage(i / len(CT4D.dyn3DImageList), amplitude=1))
    CT4DShifted = Dynamic3DSequence()
    for i in range(len(CT4D.dyn3DImageList)):
        CT4DShifted.dyn3DImageList.append(ModelShifted.generate3DImage(i/len(CT4D.dyn3DImageList), amplitude=1))

    # DISPLAY RESULTS
    fig, ax = plt.subplots(3, 7)
    fig.tight_layout()
    y_slice = 70
    ax[1, 0].imshow(Model.midp.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1, 0].title.set_text('MidP')
    ax[2, 0].imshow(ModelShifted.midp.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[2, 0].title.set_text('MidP shifted')

    average = CT4D.dyn3DImageList[0].copy()
    for i in range(len(CT4D.dyn3DImageList)-1):
        average._imageArray += CT4D.dyn3DImageList[i+1]._imageArray
    average._imageArray = average.imageArray/len(CT4D.dyn3DImageList)
    averageRegen = CT4DRegen.dyn3DImageList[0].copy()
    for i in range(len(CT4DRegen.dyn3DImageList) - 1):
        averageRegen._imageArray += CT4DRegen.dyn3DImageList[i + 1]._imageArray
    averageRegen._imageArray = averageRegen.imageArray / len(CT4DRegen.dyn3DImageList)
    averageShifted = CT4DShifted.dyn3DImageList[0].copy()
    for i in range(len(CT4DShifted.dyn3DImageList) - 1):
        averageShifted._imageArray += CT4DShifted.dyn3DImageList[i + 1]._imageArray
    averageShifted._imageArray = averageShifted.imageArray / len(CT4DShifted.dyn3DImageList)
    ax[0, 1].imshow(average.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0, 1].title.set_text('Average')
    ax[1, 1].imshow(averageRegen.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1, 1].title.set_text('Gen average')
    ax[2, 1].imshow(averageShifted.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[2, 1].title.set_text('Gen average shifted')

    averageRegen._imageArray -= average._imageArray
    averageShifted._imageArray -= average._imageArray
    average._imageArray -= average._imageArray
    ax[0, 0].imshow(average.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0, 0].title.set_text('-')
    ax[0, 2].imshow(average.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0, 2].title.set_text('-')
    ax[1, 2].imshow(averageRegen.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1, 2].title.set_text('Gen average diff')
    ax[2, 2].imshow(averageShifted.imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[2, 2].title.set_text('Gen average shifted diff')

    ax[0, 3].imshow(CT4D.dyn3DImageList[0].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0, 3].title.set_text('Phase 0')
    ax[1, 3].imshow(CT4DRegen.dyn3DImageList[0].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1, 3].title.set_text('Gen phase 0')
    ax[2, 3].imshow(CT4DShifted.dyn3DImageList[0].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[2, 3].title.set_text('Gen phase 0 shifted')

    ax[0, 4].imshow(CT4D.dyn3DImageList[1].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0, 4].title.set_text('Phase 1')
    ax[1, 4].imshow(CT4DRegen.dyn3DImageList[1].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1, 4].title.set_text('Gen phase 1')
    ax[2, 4].imshow(CT4DShifted.dyn3DImageList[1].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[2, 4].title.set_text('Gen phase 1 shifted')

    ax[0, 5].imshow(CT4D.dyn3DImageList[2].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0, 5].title.set_text('Phase 2')
    ax[1, 5].imshow(CT4DRegen.dyn3DImageList[2].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1, 5].title.set_text('Gen phase 2')
    ax[2, 5].imshow(CT4DShifted.dyn3DImageList[2].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[2, 5].title.set_text('Gen phase 2 shifted')

    ax[0, 6].imshow(CT4D.dyn3DImageList[3].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[0, 6].title.set_text('Phase 3')
    ax[1, 6].imshow(CT4DRegen.dyn3DImageList[3].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[1, 6].title.set_text('Gen phase 3')
    ax[2, 6].imshow(CT4DShifted.dyn3DImageList[3].imageArray[:, y_slice, :].T[::-1, ::1], cmap='gray', origin='upper', vmin=-1000, vmax=1000)
    ax[2, 6].title.set_text('Gen phase 3 shifted')

    plt.show()

    print('done')
