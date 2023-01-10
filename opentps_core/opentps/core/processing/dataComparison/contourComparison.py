def getBaselineShift(movingMask, fixedMask, transform):
    cm1 = fixedMask.centerOfMass
    deformedMask = transform.deformImage(movingMask)
    cm2 = deformedMask.centerOfMass

    baselineShift = cm1 - cm2
    return baselineShift