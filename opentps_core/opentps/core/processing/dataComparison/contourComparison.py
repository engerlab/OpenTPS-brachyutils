def getBaselineShift(movingMask, fixedMask, transform=None):
    if not transform == None:
        movingMask = transform.deformImage(movingMask, inPlace=True)
    cm1 = movingMask.centerOfMass
    cm2 = fixedMask.centerOfMass
    baselineShift = cm2 - cm1
    return baselineShift


def compareMasks(mask1, mask2):
    results = []
    mask1Name = mask1.name
    mask1Origin = mask1.origin
    mask1Spacing = mask1.spacing
    mask1GridSize = mask1.gridSize
    mask1VolumeInVox = mask1.getVolume(inVoxels=True)
    mask1VolumeInMMCube = mask1.getVolume(inVoxels=False)

    return results