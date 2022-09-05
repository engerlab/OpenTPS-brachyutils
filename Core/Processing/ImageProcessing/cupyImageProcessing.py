import numpy as np
import cupy
import cupyx
from scipy.spatial.transform import Rotation as R
import matplotlib.pyplot as plt

## ------------------------------------------------------------------------------------------------
def translateCupy(dataArray, translationInPixels=[0, 0, 0], cval=-1000):
    """

    Parameters
    ----------
    dataArray : ND numpy array, the data to translate
    translationInPixels : sequence of the translation in pixels in the 3 direction [X, Y, Z]
    cval : the value to fill the data for points coming, after translation, from outside the image

    Returns
    -------
    ND numpy array, the translated data
    """
    cupyArray = cupy.asarray(dataArray)

    if not (np.array(translationInPixels == np.array([0, 0, 0])).all() or np.array(translationInPixels == np.array([0, 0, 0, 0])).all()):
        cupyArray = cupyx.scipy.ndimage.shift(cupyArray, translationInPixels, mode='constant', cval=cval)

    return cupy.asnumpy(cupyArray)

## ------------------------------------------------------------------------------------------------
def rotateCupy(dataArray, rotationInDeg=[0, 0, 0], cval=-1000):
    """

    Parameters
    ----------
    dataArray : ND numpy array, the data to rotate
    rotationInDeg : the rotation in degrees around each axis, that will be applied successively in X,Y,Z order
    cval : the value to fill the data if points come, after rotation, from outside the image

    Returns
    -------
    ND numpy array, the rotated data

    NB: the order of applied rotation is important because rotations in 3D are not commutative. So to change the order to something different than X, Y, Z
    the user can call the function multiple time with the angles specified in the order or rotation

    !!! This does not take into account a difference in voxel spacing !!!
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

## ------------------------------------------------------------------------------------------------
def affineTransformCupy(img, matrix, cval=-1000):

    """
    WIP
    Parameters
    ----------
    img
    matrix
    cval

    Returns
    -------

    """

    cupyArray = cupy.asarray(img.imageArray)
    cupyMatrix = cupy.asarray(matrix)
    cupyArray = cupyx.scipy.ndimage.affine_transform(cupyArray, cupyMatrix, offset=[30, 0, 0])#img.gridSize/2)

    img.imageArray = cupy.asnumpy(cupyArray)

    # plt.figure()
    # plt.imshow(img.imageArray[:, 100, :])
    # plt.show()


## ------------------------------------------------------------------------------------------------
def rotateUsingMapCoordinatesCupy(img, rotAngleInDeg, rotAxis=1):
    """
    WIP
    Parameters
    ----------
    img
    rotAngleInDeg
    rotAxis

    Returns
    -------

    """
    voxelCoordsAroundCenterOfImageX = np.linspace((-img.gridSize[0] / 2) + 0.5, (img.gridSize[0] / 2) + 0.5, num=img.gridSize[0]) * img.spacing[0]
    voxelCoordsAroundCenterOfImageY = np.linspace((-img.gridSize[1] / 2) + 0.5, (img.gridSize[1] / 2) + 0.5, num=img.gridSize[1]) * img.spacing[1]
    voxelCoordsAroundCenterOfImageZ = np.linspace((-img.gridSize[2] / 2) + 0.5, (img.gridSize[2] / 2) + 0.5, num=img.gridSize[2]) * img.spacing[2]

    x, y, z = np.meshgrid(voxelCoordsAroundCenterOfImageX, voxelCoordsAroundCenterOfImageY, voxelCoordsAroundCenterOfImageZ, indexing='ij')
    print(img.spacing)
    print(voxelCoordsAroundCenterOfImageX[:10])
    print(voxelCoordsAroundCenterOfImageY[:10])

    coordsMatrix = np.stack((x, y, z), axis=-1)

    print(coordsMatrix.shape)

    # test = np.roll(np.array([1, 0, 0]), rotAxis)
    r = R.from_rotvec(rotAngleInDeg * np.roll(np.array([1, 0, 0]), rotAxis), degrees=True)
    print(r.as_matrix())

    coordsVector = coordsMatrix.reshape((coordsMatrix.shape[0] * coordsMatrix.shape[1] * coordsMatrix.shape[2], 3))
    # voxel = 4000
    # print(flattenedVectorField.shape)
    # print(flattenedVectorField[voxel])

    rotatedCoordsVector = r.apply(coordsVector, inverse=True)

    # print(flattenedVectorField.shape)
    # print(flattenedVectorField[voxel])

    rotatedCoordsMatrix = rotatedCoordsVector.reshape((coordsMatrix.shape[0], coordsMatrix.shape[1], coordsMatrix.shape[2], 3))
    # print(coordsVector[:10])
    # np.stack((a, b), axis=-1)

    print('ici')
    print(rotatedCoordsMatrix.shape)
    print(img.imageArray.shape)
    # rotatedCoordsAndValue = np.concatenate((rotatedCoordsMatrix, img.imageArray))
    rotatedCoordsAndValue = np.stack((rotatedCoordsMatrix, img.imageArray), axis=1)
    print(rotatedCoordsAndValue.shape)

    interpolatedImage = cupy.asnumpy(cupyx.scipy.ndimage.map_coordinates(cupy.asarray(image), cupy.asarray(coordsMatrix), order=1, mode='constant', cval=-1000))

    # print(voxelCoordsAroundCenterOfImageX)

    cupyArray = cupy.asarray(img.imageArray)


def resampleCupy():
    """
    TODO
    Returns
    -------

    """

    return NotImplementedError