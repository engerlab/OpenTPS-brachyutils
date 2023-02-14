import numpy as np


def getMaskVolume(mask, inVoxels=False):
    volumeInvoxels = np.count_nonzero(mask.imageArray > 0)
    if inVoxels:
        return volumeInvoxels
    else:
        volumeInMMCube = volumeInvoxels * mask.spacing[0] * mask.spacing[1] * mask.spacing[2]
        return volumeInMMCube