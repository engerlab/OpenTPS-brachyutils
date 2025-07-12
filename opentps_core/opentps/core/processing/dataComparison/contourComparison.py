def getBaselineShift(movingMask, fixedMask, transform=None):
    """
    Calculates the baseline shift between two masks.
    The baseline shift is the difference between the center of mass of the
    moving mask and the center of mass of the fixed mask.

    Parameters
    ----------
    movingMask : Mask
        The moving mask.
    fixedMask : Mask
        The fixed mask.
    transform : Transform, optional
        The transform to apply to the moving mask before calculating the
        baseline shift. The default is None.

    Returns
    -------
    baselineShift : np.ndarray
        The baseline shift as a numpy array.
    """
    if not transform == None:
        movingMask = transform.deformImage(movingMask)
    cm1 = movingMask.centerOfMass
    cm2 = fixedMask.centerOfMass
    baselineShift = cm2 - cm1
    return baselineShift


def compareMasks(mask1, mask2):
    """
    Compares two masks and returns a dictionary with the results.

    !!! This function is not implemented yet !!!

    Parameters
    ----------
    mask1 : Mask
        The first mask to compare.
    mask2 : Mask
        The second mask to compare.

    Returns
    -------
    results : dict
        A dictionary with the results of the comparison.
    """
    # TODO implement
    results = []
    mask1Name = mask1.name
    mask1Origin = mask1.origin
    mask1Spacing = mask1.spacing
    mask1GridSize = mask1.gridSize
    mask1VolumeInVox = mask1.getVolume(inVoxels=True)
    mask1VolumeInMMCube = mask1.getVolume(inVoxels=False)

    return results