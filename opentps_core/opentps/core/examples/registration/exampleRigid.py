import numpy as np
import matplotlib.pyplot as plt
import time
import logging

from opentps.core.data.images import CTImage
from opentps.core.processing.registration.registrationRigid import RegistrationRigid
from opentps.core.examples.syntheticData import *
from opentps.core.processing.imageProcessing.resampler3D import resampleImage3DOnImage3D
from opentps.core.processing.imageProcessing.sitkImageProcessing import rotateImage3DSitk

logger = logging.getLogger(__name__)

def run():

    # GENERATE SYNTHETIC INPUT IMAGES
    fixed_img = np.full((100, 100, 100), -1000)
    fixed_img[15:50, 25:50, 25:75] = 0
    fixed = CTImage(imageArray=fixed_img, name='fixed', origin=[0, 0, 0], spacing=[1, 1, 1])

    moving_img = np.full((100, 100, 100), -1000)
    moving_img[30:65, 50:75, 25:75] = 0
    moving = CTImage(imageArray=moving_img, name='moving', origin=[0, 0, 0], spacing=[1, 1, 1])

    rotateImage3DSitk(moving, rotAngleInDeg=5, rotAxis=2)

    # PERFORM REGISTRATION
    start_time = time.time()
    reg = RegistrationRigid(fixed, moving)
    transform = reg.compute()
    print(transform.tform)
    processing_time = time.time() - start_time
    print('Registration processing time was', processing_time, '\n')

    x_slice = round(fixed.imageArray.shape[0] / 2) - 1
    y_slice = round(fixed.imageArray.shape[1] / 2) - 1
    z_slice = round(fixed.imageArray.shape[2] / 2) - 1

    deformedImage = reg.deformed
    resampledOnFixedGrid = resampleImage3DOnImage3D(deformedImage, fixedImage=fixed, fillValue=-1000)

    fig, ax = plt.subplots(1, 4)
    ax[0].imshow(fixed.imageArray[:, :, z_slice])
    ax[0].set_title('Fixed')
    ax[0].set_xlabel('Origin: '+f'{fixed.origin[0]}'+','+f'{fixed.origin[1]}'+','+f'{fixed.origin[2]}')
    ax[1].imshow(moving.imageArray[:, :, z_slice])
    ax[1].set_title('Moving')
    ax[1].set_xlabel('Origin: ' + f'{moving.origin[0]}' + ',' + f'{moving.origin[1]}' + ',' + f'{moving.origin[2]}')
    ax[2].imshow(deformedImage.imageArray[:, :, z_slice])
    ax[2].set_title('DeformedMoving')
    ax[2].set_xlabel('Origin: ' + f'{deformedImage.origin[0]:.1f}' + ',' + f'{deformedImage.origin[1]:.1f}' + ',' + f'{deformedImage.origin[2]:.1f}')
    ax[3].imshow(resampledOnFixedGrid.imageArray[:, :, z_slice])
    ax[3].set_title('resampledOnFixedGrid')
    ax[3].set_xlabel('Origin: ' + f'{resampledOnFixedGrid.origin[0]:.1f}' + ',' + f'{resampledOnFixedGrid.origin[1]:.1f}' + ',' + f'{resampledOnFixedGrid.origin[2]:.1f}')
    plt.show()

if __name__ == "__main__":
    run()