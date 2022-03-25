import numpy as np

## ------------------------------------------------------------
def getBinaryMaskFromROIDRR(drr):

    mask = drr > 2
    return mask

## ------------------------------------------------------------
def get2DMaskCenterOfMass(maskArray):

    ones = np.where(maskArray == True)

    return [np.mean(ones[0]), np.mean(ones[1])]

## ------------------------------------------------------------