
class Patient:
    """
    A class Patient contains patient information and lists of patient data (images, plans, etc...)

    Parameters
    ----------
    age: int
        Patient's age

    name: str
        Patient's name

    patientID: int
        ID of the patient

    sex: str
        sex of the patient

    images: list
        List of images associated to patient of possibly different modalities

    plans: list:
        List of plans associated to patient

    """
    def __init__(self):
        self.age = 0
        self.name = None
        self.patientID = None
        self.sex = None
        self.images = []
        self.plans = []

    def appendImage(self, image):
        """
        Append image to patient's image list

        Parameters
        ----------
        image: object
            image object

        """
        self.images.append(image)

    def hasImage(self, image):
        """
         Check if image is in patient's image list

        Parameters
        ----------
        image: object
             image object

        """
        return image in self.images

    def removeImage(self, image):
        """
        Remove image from patient's image list

        Parameters
        ----------
        image: object
            the image object to removed

        """
        self.images.remove(image)

