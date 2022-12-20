def getBaselineShift(fixedMask, movingMask, transform):
    cm1 = fixedMask.centerOfMass
    deformedMask = transform.deformImage(movingMask)
    cm2 = deformedMask.centerOfMass

    baselineShift = cm2 - cm1
    return baselineShift