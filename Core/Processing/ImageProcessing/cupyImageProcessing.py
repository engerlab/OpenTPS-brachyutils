import numpy as np
import cupy
import cupyx

## ------------------------------------------------------------------------------------------------
def translateCupy(dataArray, translationInPixels=[0, 0, 0], cval=-1000):

    cupyArray = cupy.asarray(dataArray)

    if not (np.array(translationInPixels == np.array([0, 0, 0])).all() or np.array(translationInPixels == np.array([0, 0, 0, 0])).all()):
        print('Apply translation in pixels', translationInPixels)
        cupyArray = cupyx.scipy.ndimage.shift(cupyArray, translationInPixels, mode='constant', cval=cval)

    return cupy.asnumpy(cupyArray)

def rotateCupy(dataArray, rotationInDeg=[0, 0, 0], cval=-1000):
    """

    Parameters
    ----------
    dataArray : ND numpy array, the data to rotate
    rotationInDeg : the rotation in degrees around each axis, that will be applied successively in X,Y,Z order
    cval : the value to fill the data if points come, after rotation, from outside the image

    Returns
    -------
    NB: the order of applied rotation is important because rotations in 3D are not commutative. So to change the order to something different than X, Y, Z
    the user can call the function multiple time with the angles specified in the order or rotation
    """
    cupyArray = cupy.asarray(dataArray)

    if not np.array(rotationInDeg == np.array([0, 0, 0])).all():
        if rotationInDeg[0] != 0:
            print('Apply rotation around X', rotationInDeg[0])
            cupyArray = cupyx.scipy.ndimage.rotate(cupyArray, rotationInDeg[0], axes=[1, 2], reshape=False, mode='constant', cval=cval)
        if rotationInDeg[1] != 0:
            print('Apply rotation around Y', rotationInDeg[1])
            cupyArray = cupyx.scipy.ndimage.rotate(cupyArray, rotationInDeg[1], axes=[0, 2], reshape=False, mode='constant', cval=cval)
        if rotationInDeg[2] != 0:
            print('Apply rotation around Z', rotationInDeg[2])
            cupyArray = cupyx.scipy.ndimage.rotate(cupyArray, rotationInDeg[2], axes=[0, 1], reshape=False, mode='constant', cval=cval)

    return cupy.asnumpy(cupyArray)