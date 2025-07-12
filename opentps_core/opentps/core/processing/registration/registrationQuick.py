import numpy as np
import logging

from opentps.core.data._transform3D import Transform3D
from opentps.core.processing.registration.registration import Registration

logger = logging.getLogger(__name__)


def matchProfiles(fixed, moving):
    """
    Find shift between two profiles by minimizing the mean squared error (MSE).

    Parameters
    ----------
    fixed : array
        fixed profile.
    moving : array
        moving profile.

    Returns
    -------
    int
        shift between profiles.
    """
    mse = []

    for index in range(len(moving)):
        shift = index - round(len(moving) / 2)

        # shift profiles
        shifted = np.roll(moving, shift)

        # crop profiles to same size
        if (len(shifted) > len(fixed)):
            vec1 = shifted[:len(fixed)]
            vec2 = fixed
        else:
            vec1 = shifted
            vec2 = fixed[:len(shifted)]

        # compute MSE
        mse.append(((vec1 - vec2) ** 2).mean())

    return (np.argmin(mse) - round(len(moving) / 2))


class RegistrationQuick(Registration):
    """
    Perform quick translation search between fixed and moving images. inherited from Registration class.

    Attributes
    ----------
    fixed : Image3D
        Fixed image.
    moving : Image3D
        Moving image.
    """
    def __init__(self, fixed, moving):
        Registration.__init__(self, fixed, moving)

    def compute(self, tryGPU=True):

        """Perform registration between fixed and moving images.

            Returns
            -------
            Transform3D
                Translation from moving to fixed images.
            """

        if self.fixed == [] or self.moving == []:
            logger.error("Image not defined in registration object")
            return

        logger.info("\nStart quick translation search.\n")

        translation = [0.0, 0.0, 0.0]

        # resample moving to same resolution as fixed
        self.deformed = self.moving.copy()
        gridSize = np.array(self.moving.gridSize * np.array(self.moving.spacing) / np.array(self.fixed.spacing))
        gridSize = gridSize.astype(int)
        self.deformed.resample(self.fixed.spacing, gridSize, self.moving.origin, tryGPU=tryGPU)

        # search shift in x
        fixedProfile = np.sum(self.fixed.imageArray, (0, 2))
        movingProfile = np.sum(self.deformed.imageArray, (0, 2))
        shift = matchProfiles(fixedProfile, movingProfile)
        translation[0] = self.fixed.origin[0] - self.moving.origin[0] + shift * self.deformed.spacing[0]
        # search shift in y
        fixedProfile = np.sum(self.fixed.imageArray, (1, 2))
        movingProfile = np.sum(self.deformed.imageArray, (1, 2))
        shift = matchProfiles(fixedProfile, movingProfile)
        translation[1] = self.fixed.origin[1] - self.moving.origin[1] + shift * self.deformed.spacing[1]

        # search shift in z
        fixedProfile = np.sum(self.fixed.imageArray, (0, 1))
        movingProfile = np.sum(self.deformed.imageArray, (0, 1))
        shift = matchProfiles(fixedProfile, movingProfile)
        translation[2] = self.fixed.origin[2] - self.moving.origin[2] + shift * self.deformed.spacing[2]
        
        self.translateOrigin(self.deformed, translation)

        tform = np.zeros((4, 4))
        tform[0:-1, -1] = translation
        tform[0:-1, 0:-1] = np.eye(3)

        transform = Transform3D(tform=tform)
        self.deformed = transform.deformImage(self.moving, fillValue='closest')
        self.deformed.setName(self.moving.name + '_registered_to_' + self.fixed.name)
        return transform
