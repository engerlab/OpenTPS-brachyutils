import scipy.signal
import logging

from Core.Processing.Registration.registration import Registration


class RegistrationTranslation(Registration):

    def __init__(self, fixed, moving, initialTranslation=[0.0, 0.0, 0.0]):

        Registration.__init__(self, fixed, moving)
        self.initialTranslation = initialTranslation

    def compute(self):
        print("\nStart rigid registration.\n")

        opt = scipy.optimize.minimize(self.translateAndComputeSSD, self.initialTranslation, method='Powell',
                                      options={'xtol': 0.01, 'ftol': 0.0001, 'maxiter': 25, 'maxfev': 75})

        if (self.roiBox == []):
            translation = opt.x
        else:
            start = self.roiBox[0]
            stop = self.roiBox[1]
            translation = opt.x

        return translation
