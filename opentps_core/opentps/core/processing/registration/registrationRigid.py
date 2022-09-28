import logging

from opentps.core.data._transform3D import Transform3D
from opentps.core.processing.registration.registration import Registration

logger = logging.getLogger(__name__)


class RegistrationRigid(Registration):

    def __init__(self, fixed, moving, multimodal = False):

        Registration.__init__(self, fixed, moving)
        self.multimodal = multimodal

    def compute(self):

        """Perform rigid registration between fixed and moving images.

            Returns
            -------
            Transform3D
                Transform from moving to fixed images.
            """

        try:
            from opentps.core.processing.imageProcessing import sitkImageProcessing
            tform, center, deformed = sitkImageProcessing.register(sitkImageProcessing.image3DToSITK(self.fixed), sitkImageProcessing.image3DToSITK(self.moving), multimodal=self.multimodal, fillValue=float(self.moving.min()))
            transform = Transform3D(tform=tform, center=center)
        except:
            logger.info('Failed to use SITK registration. Try translation only.')
            from opentps.core.processing.registration.registrationTranslation import RegistrationTranslation
            reg = RegistrationTranslation(self.fixed, self.moving)
            transform = reg.compute()

        self.deformed = transform.deformImage(self.moving, fillValue='closest')
        self.deformed.setName(self.moving.name + '_registered_to_' + self.fixed.name)
        return transform
