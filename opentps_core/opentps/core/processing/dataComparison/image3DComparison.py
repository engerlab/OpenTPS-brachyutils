from opentps.core.processing.registration.registrationRigid import RegistrationRigid


def getTranslationAndRotation(fixed, moving, transform=None):
    """
    Compute the translation and rotation between image1 and image2.

    Parameters
    ----------
    fixed : Image3D
        The fixed image
    moving : Image3D
        The moving image
    transform : Transform3D, optional
        The transform between the two images

    Returns
    -------
    T : array
        The translation in mm
    anglesArray : array
        The array of angles in radians
    """

    if transform==None:
        print("Compute rigid registration for the image comparison")
        reg = RegistrationRigid(fixed=fixed, moving=moving)
        transform = reg.compute()
    
    translation = transform.getTranslation()
    eulerAngles = transform.getRotationAngles()
    theta_x = eulerAngles[0]
    theta_y = eulerAngles[1]
    theta_z = eulerAngles[2]
    
    anglesArray = [theta_x, theta_y, theta_z]
    return translation, anglesArray

