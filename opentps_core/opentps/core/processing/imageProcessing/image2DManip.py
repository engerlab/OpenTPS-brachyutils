import numpy as np

## ------------------------------------------------------------
def getBinaryMaskFromROIDRR(drr):
    """
    Returns a binary mask from a DRR image.
    The mask is True where the DRR is greater than 2.

    Parameters:
    - drr: DRR image
    """
    mask = drr > 2
    return mask

## ------------------------------------------------------------
def get2DMaskCenterOfMass(maskArray):
    """
    Returns the center of mass of a 2D mask.

    Parameters:
    - maskArray: 2D mask
    """

    ones = np.where(maskArray == True)

    return [np.mean(ones[0]), np.mean(ones[1])]

## ------------------------------------------------------------