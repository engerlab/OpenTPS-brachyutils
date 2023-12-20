import numpy as np
import scipy.signal
import logging

from opentps.core.data._transform3D import Transform3D
from opentps.core.processing.registration.registration import Registration

logger = logging.getLogger(__name__)


class RegistrationTranslation(Registration):
    """
    Perform translation registration between fixed and moving images. inherited from Registration class.

    Attributes
    ----------
    fixed : Image3D
        Fixed image.
    moving : Image3D
        Moving image.
    initialTranslation : list
        Initial translation guess.
    """
    def __init__(self, fixed, moving, initialTranslation=[0.0, 0.0, 0.0]):

        Registration.__init__(self, fixed, moving)
        self.initialTranslation = initialTranslation

    def compute(self):

        """Perform registration between fixed and moving images.

            Returns
            -------
            Transform3D
                Translation from moving to fixed images.
            """

        logger.info("\nStart rigid registration.\n")

        opt = scipy.optimize.minimize(self.translateAndComputeSSD, self.initialTranslation, method='Powell',
                                      options={'xtol': 0.01, 'ftol': 0.0001, 'maxiter': 25, 'maxfev': 75})

        if (self.roiBox == []):
            translation = opt.x
        else:
            start = self.roiBox[0]
            stop = self.roiBox[1]
            translation = opt.x

        tformMatrix = np.zeros((4, 4))
        tformMatrix[0:-1, -1] = translation
        tformMatrix[0:-1, 0:-1] = np.eye(3)

        transform = Transform3D(tformMatrix=tformMatrix)
        self.deformed = transform.deformImage(self.moving, fillValue='closest')
        self.deformed.setName(self.moving.name + '_registered_to_' + self.fixed.name)
        return transform
