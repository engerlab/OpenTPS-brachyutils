import numpy as np


def getBinaryMaskFromROIDRR(drr, outputType=np.bool):

    mask = drr > 2
    return mask

def get2DMaskCenterOfMass(maskArray):

    ones = np.where(maskArray == True)

    print(ones)