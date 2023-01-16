def getBaselineShift(movingMask, fixedMask, transform):
    deformedMask1 = transform.deformImage(movingMask)
    cm1 = deformedMask1.centerOfMass
    cm2 = fixedMask.centerOfMass
    baselineShift = cm2 - cm1
    return baselineShift