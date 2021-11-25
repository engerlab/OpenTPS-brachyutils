import numpy as np

from Core.Processing.Registration.registration import Registration


class RegistrationQuick(Registration):

    def __init__(self, fixed, moving):

        Registration.__init__(self, fixed, moving)

    def compute(self):
        if self.fixed == [] or self.moving == []:
            print("Image not defined in registration object")
            return

        print("\nStart quick translation search.\n")

        translation = [0.0, 0.0, 0.0]

        # resample moving to same resolution as fixed
        self.deformed = self.moving.copy()
        GridSize = np.array(self.moving.GridSize) * np.array(self.moving.PixelSpacing) / np.array(
            self.fixed.PixelSpacing)
        GridSize = GridSize.astype(np.int)
        self.deformed.resample_image(GridSize, self.moving.ImagePositionPatient, self.fixed.PixelSpacing)

        # search shift in x
        fixedProfile = np.sum(self.fixed.Image, (0, 2))
        movingProfile = np.sum(self.deformed.Image, (0, 2))
        shift = matchProfiles(fixedProfile, movingProfile)
        translation[0] = self.fixed.ImagePositionPatient[0] - self.moving.ImagePositionPatient[0] + shift * \
                         self.deformed.PixelSpacing[0]
        # search shift in y
        fixedProfile = np.sum(self.fixed.Image, (1, 2))
        movingProfile = np.sum(self.deformed.Image, (1, 2))
        shift = matchProfiles(fixedProfile, movingProfile)
        translation[1] = self.fixed.ImagePositionPatient[1] - self.moving.ImagePositionPatient[1] + shift * \
                         self.deformed.PixelSpacing[1]

        # search shift in z
        fixedProfile = np.sum(self.fixed.Image, (0, 1))
        movingProfile = np.sum(self.deformed.Image, (0, 1))
        shift = matchProfiles(fixedProfile, movingProfile)
        translation[2] = self.fixed.ImagePositionPatient[2] - self.moving.ImagePositionPatient[2] + shift * \
                         self.deformed.PixelSpacing[2]

        translateOrigin(self.deformed, translation)

        return translation
