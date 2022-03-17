import numpy as np
import logging

from Core.Data.Images.image3D import Image3D
from Core.Processing.Registration.registration import Registration

logger = logging.getLogger(__name__)


def matchProfiles(fixed, moving):
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

    def __init__(self, fixed, moving):
        Registration.__init__(self, fixed, moving)

    def compute(self, tryGPU=True):

        """Perform registration between fixed and moving images.

            Returns
            -------
            list
                Translation from moving to fixed images.
            """

        if self.fixed == [] or self.moving == []:
            logger.error("Image not defined in registration object")
            return

        logger.info("\nStart quick translation search.\n")

        translation = [0.0, 0.0, 0.0]

        # resample moving to same resolution as fixed
        self.deformed = self.moving.copy()
        gridSize = np.array(self.moving.gridSize()) * np.array(self.moving._spacing) / np.array(self.fixed._spacing)
        gridSize = gridSize.astype(np.int)
        self.deformed.resample(gridSize, self.moving._origin, self.fixed._spacing, tryGPU=tryGPU)

        # search shift in x
        fixedProfile = np.sum(self.fixed._imageArray, (0, 2))
        movingProfile = np.sum(self.deformed._imageArray, (0, 2))
        shift = matchProfiles(fixedProfile, movingProfile)
        translation[0] = self.fixed._origin[0] - self.moving._origin[0] + shift * self.deformed._spacing[0]
        # search shift in y
        fixedProfile = np.sum(self.fixed._imageArray, (1, 2))
        movingProfile = np.sum(self.deformed._imageArray, (1, 2))
        shift = matchProfiles(fixedProfile, movingProfile)
        translation[1] = self.fixed._origin[1] - self.moving._origin[1] + shift * self.deformed._spacing[1]

        # search shift in z
        fixedProfile = np.sum(self.fixed._imageArray, (0, 1))
        movingProfile = np.sum(self.deformed._imageArray, (0, 1))
        shift = matchProfiles(fixedProfile, movingProfile)
        translation[2] = self.fixed._origin[2] - self.moving._origin[2] + shift * self.deformed._spacing[2]

        self.translateOrigin(self.deformed, translation)

        return translation
