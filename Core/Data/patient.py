
from Core.Data.patientInfo import PatientInfo


class Patient:
    """
    A class Patient contains patient information and lists of patient data (images, plans, etc...)

    Parameters
    ----------
    patientInfo: PatientInfo object
        Object containing the patient information

    images: list
        List of images associated to patient of possibly different modalities

    plans: list:
        List of plans associated to patient

    rtStructs: list:
        List of structure sets associated to patient

    """
    def __init__(self, patientInfo=None):
        if(patientInfo == None):
            self.patientInfo = PatientInfo()
        else:
            self.patientInfo = patientInfo

        self.images = []
        self.plans = []
        self.rtStructs = []
        self.dynamic3DSequences = []
        self.dynamic3DModels = []


    def __str__(self):
        string = "Patient name: " + self.patientInfo.name + "\n"
        string += "  Images:\n"
        for img in self.images:
            string += "    " + img.name + "\n"
        string += "  Plans:\n"
        for plan in self.plans:
            string += "    " + plan.name + "\n"
        string += "  Structure sets:\n"
        for struct in self.rtStructs:
            string += "    " + struct.name + "\n"
        return string

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

    def appendRTStruct(self, struct):
        """
        Append RTStruct object to patient's RTStruct list

        Parameters
        ----------
        struct: RTStruct object
            Structure set to append

        """
        self.rtStructs.append(struct)

    def removeRTStruct(self, struct):
        """
        Remove RTStruct from patient's RTStruct list

        Parameters
        ----------
        struct: RTStruct object
            Structure set to remove

        """
        self.rtStructs.remove(struct)

    def appendDyn3DSeq(self, dyn3DSeq):
        """
        Append dynamic3DSequence object to patient's dynamic3DSequences list

        Parameters
        ----------
        dyn3DSeq: dynamic3DSequence object
            Dynamic 3D Sequence set to append

        """
        self.dynamic3DSequences.append(dyn3DSeq)

    def removeDyn3DSeq(self, dyn3DSeq):
        """
        Remove dynamic3DSequence from patient's dynamic3DSequences list

        Parameters
        ----------
        dyn3DSeq: dynamic3DSequence object
            Dynamic 3D Sequence set to remove

        """
        self.dynamic3DSequences.remove(dyn3DSeq)

    def appendDyn3DMod(self, dyn3DMod):
        """
        Append dynamic3DModel object to patient's dynamic3DModels list

        Parameters
        ----------
        dyn3DMod: dynamic3DModel object
            Dynamic 3D Model set to append

        """
        self.dynamic3DModels.append(dyn3DMod)

    def removeDyn3DMod(self, dyn3DMod):
        """
        Remove dynamic3DModel from patient's dynamic3DModels list

        Parameters
        ----------
        dyn3DMod: dynamic3DModel object
            Dynamic 3D Model set to remove

        """
        self.dynamic3DModels.remove(dyn3DMod)

