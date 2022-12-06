import copy

import numpy as np
import matplotlib.pyplot as plt
import time
import logging

from opentps.core.data.images import CTImage
from opentps.core.processing.registration.registrationRigid import RegistrationRigid
from opentps.core.examples.syntheticData import *
from opentps.core.processing.imageProcessing.resampler3D import resampleImage3DOnImage3D
from opentps.core.processing.imageProcessing.sitkImageProcessing import rotateImage3DSitk, translateImage3DSitk

logger = logging.getLogger(__name__)

def run():

    # GENERATE SYNTHETIC INPUT IMAGES
    fixed_img = np.full((100, 100, 100), -1000)
    fixed_img[15:40, 25:40, 25:75] = 0
    fixed = CTImage(imageArray=fixed_img, name='fixed', origin=[0, 0, 0], spacing=[1, 1, 1])

    # fixed = createSynthetic3DCT()

    moving = copy.copy(fixed)
    translateImage3DSitk(moving, [10, 5, 0])
    rotateImage3DSitk(moving, rotAngleInDeg=5, rotAxis=2)

    # PERFORM REGISTRATION
    start_time = time.time()
    reg = RegistrationRigid(fixed, moving)
    transform = reg.compute()

    print(transform.tform)
    print('rotation in rad', transform.getRotationAngles())
    print('rotation in deg', transform.getRotationAngles(inDegrees=True))
    print('translation', transform.getTranslation())

    processing_time = time.time() - start_time
    print('Registration processing time was', processing_time, '\n')

    x_slice = round(fixed.imageArray.shape[0] / 2) - 1
    y_slice = round(fixed.imageArray.shape[1] / 2) - 1
    z_slice = round(fixed.imageArray.shape[2] / 2) - 1

    deformedImage = reg.deformed
    resampledOnFixedGrid = resampleImage3DOnImage3D(deformedImage, fixedImage=fixed, fillValue=-1000)

    fig, ax = plt.subplots(2, 3)
    ax[0, 0].imshow(fixed.imageArray[:, :, z_slice])
    ax[0, 0].set_title('Fixed')
    ax[0, 0].set_xlabel('Origin: '+f'{fixed.origin[0]}'+','+f'{fixed.origin[1]}'+','+f'{fixed.origin[2]}')
    ax[0, 1].imshow(moving.imageArray[:, :, z_slice])
    ax[0, 1].set_title('Moving')
    ax[0, 1].set_xlabel('Origin: ' + f'{moving.origin[0]}' + ',' + f'{moving.origin[1]}' + ',' + f'{moving.origin[2]}')
    ax[0, 2].imshow(fixed.imageArray[:, :, z_slice]-moving.imageArray[:, :, z_slice])
    ax[0, 2].set_title('Diff')
    ax[1, 0].imshow(deformedImage.imageArray[:, :, z_slice])
    ax[1, 0].set_title('DeformedMoving')
    ax[1, 0].set_xlabel('Origin: ' + f'{deformedImage.origin[0]:.1f}' + ',' + f'{deformedImage.origin[1]:.1f}' + ',' + f'{deformedImage.origin[2]:.1f}')
    ax[1, 1].imshow(resampledOnFixedGrid.imageArray[:, :, z_slice])
    ax[1, 1].set_title('resampledOnFixedGrid')
    ax[1, 1].set_xlabel('Origin: ' + f'{resampledOnFixedGrid.origin[0]:.1f}' + ',' + f'{resampledOnFixedGrid.origin[1]:.1f}' + ',' + f'{resampledOnFixedGrid.origin[2]:.1f}')
    ax[1, 2].imshow(fixed.imageArray[:, :, z_slice] - resampledOnFixedGrid.imageArray[:, :, z_slice])
    ax[1, 2].set_title('Diff')
    plt.show()

if __name__ == "__main__":
    run()