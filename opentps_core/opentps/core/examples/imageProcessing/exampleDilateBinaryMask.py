import numpy as np
import matplotlib.pyplot as plt
from opentps.core.data.images._roiMask import ROIMask
from opentps.core.processing.imageProcessing.roiMasksProcessing import buildStructElem, dilateMaskScipy
import os
import logging

logger = logging.getLogger(__name__)

def run():
    output_path = os.path.join(os.getcwd(), 'Output', 'ExampleDilateBinaryMask')
    if not os.path.exists(output_path):
            os.makedirs(output_path)
    logger.info('Files will be stored in {}'.format(output_path))


    roi = ROIMask(name='TV')
    roi.color = (255, 0, 0)# red
    data = np.zeros((100, 100, 100)).astype(bool)
    data[50:60, 50:60, 50:60] = True
    roi.imageArray = data
    roi.spacing = np.array([1, 1, 2])

    radius = np.array([4, 4, 6])
    struct = buildStructElem(radius / np.array(roi.spacing))

    roi_scipy = roi.copy()
    dilateMaskScipy(roi_scipy, radius=radius)  # scipy
    print(radius, 'before roi_sitk')
    roi_sitk = roi.copy()
    roi_sitk.dilateMask(radius=radius)

    plt.figure()
    plt.subplot(2, 4, 1)
    plt.imshow(roi.imageArray[55, :, :], cmap='gray')
    plt.title("Original")

    plt.subplot(2, 4, 2)
    plt.imshow(roi_scipy.imageArray[55, :, :], cmap='gray')
    plt.title("Scipy")

    plt.subplot(2, 4, 3)
    plt.imshow(roi_sitk.imageArray[55, :, :], cmap='gray')
    plt.title("SITK")

    plt.subplot(2, 4, 5)
    plt.imshow(roi_scipy.imageArray[55, :, :] ^ roi_sitk.imageArray[55, :, :], cmap='gray')
    plt.title("diff Scipy-SITK")

    plt.subplot(2, 4, 6)
    plt.imshow(roi_scipy.imageArray[55, :, :] ^ roi.imageArray[55, :, :], cmap='gray')
    plt.title("diff Scipy-ori")

    plt.subplot(2, 4, 7)
    plt.imshow(roi_sitk.imageArray[55, :, :] ^ roi.imageArray[55, :, :], cmap='gray')
    plt.title("diff SITK-ori")

    plt.show()
    plt.savefig(os.path.join(output_path, 'ExampleDilateBinary.png')) 

if __name__ == "__main__":
    run()