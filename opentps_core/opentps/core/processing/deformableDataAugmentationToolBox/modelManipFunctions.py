import numpy as np

from opentps.core.processing.imageProcessing.imageTransform3D import getVoxelIndexFromPosition


## ---------------------------------------------------------------------------------------------
def getAverageModelValuesAroundPosition(position, model, dimensionUsed='Z', tryGPU=True):
    """
    Get the average values in the specified dimension around the given position for each field in a Dynamic3DModel.

    Parameters
    ----------
    position : tuple or list of 3 elements
        The 3D position at which the fields values are extracted
    model : Dynamic3DModel
        The dynamic 3D model containing the deformation fields
    dimensionUsed : str
        X, Y, Z or norm, the dimension extracted from the deformation fields

    Returns
    -------
    modelDefValuesArray (np.ndarray): the average deformation values on the 3X3X3 cube in the specified dimension
    around the speficied position for each field in the deformation model
    """

    modelDefValuesList = []
    for fieldIndex, field in enumerate(model.deformationList):
        if field.displacement == None:
            print('Compute displacement field from velocity field for field', fieldIndex)
            field.displacement = field.velocity.exponentiateField(tryGPU=tryGPU)
        modelDefValuesList.append(getAverageFieldValueAroundPosition(position, field.displacement, dimensionUsed=dimensionUsed))

    modelDefValuesArray = np.array(modelDefValuesList)

    return modelDefValuesArray

## ---------------------------------------------------------------------------------------------
def getAverageFieldValueAroundPosition(position, field, dimensionUsed='Z'):
    """
    Get the average values in the specified dimension around the given position in the given field.

    Parameters
    ----------
    position : tuple or list of 3 elements
        The 3D position around which the 3x3x3 field values are extracted
    field : VectorField3D
        The 3D vector field from which the data is extracted
    dimensionUsed : str
        X, Y, Z or norm, the dimension extracted from the 3D vector field

    Returns
    -------
    usedValue (float): the average deformation value on the 3X3X3 cube in the specified dimension around the field
    speficied position
    """
    voxelIndex = getVoxelIndexFromPosition(position, field)
    dataNumpy = field.imageArray[voxelIndex[0]-1:voxelIndex[0]+2, voxelIndex[1]-1:voxelIndex[1]+2, voxelIndex[2]-1:voxelIndex[2]+2]

    if dimensionUsed == 'norm':
        averageX = np.mean(dataNumpy[:, :, :, 0])
        averageY = np.mean(dataNumpy[:, :, :, 1])
        averageZ = np.mean(dataNumpy[:, :, :, 2])
        usedValue = np.linalg.norm(np.array([averageX, averageY, averageZ]))

    elif dimensionUsed == 'X':
        usedValue = np.mean(dataNumpy[:, :, :, 0])

    elif dimensionUsed == 'Y':
        usedValue = np.mean(dataNumpy[:, :, :, 1])

    elif dimensionUsed == 'Z':
        usedValue = np.mean(dataNumpy[:, :, :, 2])

    return usedValue

## ---------------------------------------------------------------------------------------------
def getFieldValueAtPosition(position, field, dimensionUsed='Z'):
    """
    Get the field value in the specified dimension at the given position in the given field.
    Alternative function to getAverageFieldValueAroundPosition. This one does not compute an average on a 3x3x3 cube
    around the position but gets the exact position value.

    Parameters
    ----------
    position : tuple or list of 3 elements
        The 3D position at which the field value is extracted
    field : VectorField3D
        The 3D vector field from which the data is extracted
    dimensionUsed : str
        X, Y, Z or norm, the dimension extracted from the 3D vector field

    Returns
    -------
    usedValue (float): the deformation value in the specified dimension at the field speficied position
    """
    voxelIndex = getVoxelIndexFromPosition(position, field)
    dataNumpy = field.imageArray[voxelIndex[0], voxelIndex[1], voxelIndex[2]]

    if dimensionUsed == 'norm':

        usedValue = np.linalg.norm(dataNumpy)

    elif dimensionUsed == 'X':
        usedValue = dataNumpy[0]

    elif dimensionUsed == 'Y':
        usedValue = dataNumpy[1]

    elif dimensionUsed == 'Z':
        usedValue = dataNumpy[2]

    return usedValue

## ---------------------------------------------------------------------------------------------
