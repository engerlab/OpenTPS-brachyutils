from opentps.core.processing.registration.registrationRigid import RegistrationRigid


def getTranslationAndRotation(fixed, moving, transform=None):
    """Compute the translation and rotation between image1 and image2.

            Returns
            -------
            T: the translation in mm
            anglesArray: the array of angles in radians
            """

    if transform==None:
        print("Compute rigid registration for the models comparison")
        reg = RegistrationRigid(fixed=fixed, moving=moving)
        transform = reg.compute()
    
    translation = transform.getTranslation()
    eulerAngles = transform.getRotationAngles()
    theta_x = eulerAngles[0]
    theta_y = eulerAngles[1]
    theta_z = eulerAngles[2]
    
    anglesArray = [theta_x, theta_y, theta_z]
    return translation, anglesArray

   