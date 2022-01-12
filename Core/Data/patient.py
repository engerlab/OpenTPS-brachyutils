
from Core.Data.patientInfo import PatientInfo
from Core.event import Event


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
        self.imageAddedSignal = Event(object)
        self.imageRemovedSignal = Event(object)
        self.rtStructAddedSignal = Event(object)
        self.rtStructRemovedSignal = Event(object)
        self.planAddedSignal = Event(object)
        self.planRemovedSignal = Event(object)
        self.dyn3DSeqAddedSignal = Event(object)
        self.dyn3DSeqRemovedSignal = Event(object)
        self.dyn3DModAddedSignal = Event(object)
        self.dyn3DModRemovedSignal = Event(object)
        self.nameChangedSignal = Event(str)

        if(patientInfo == None):
            self.patientInfo = PatientInfo()
        else:
            self.patientInfo = patientInfo

        self._images = []
        self._plans = []
        self._rtStructs = []
        self._dynamic3DSequences = []
        self._dynamic3DModels = []


    def __str__(self):
        string = "Patient name: " + self.patientInfo.name + "\n"
        string += "  Images:\n"
        for img in self._images:
            string += "    " + img.name + "\n"
        string += "  Plans:\n"
        for plan in self._plans:
            string += "    " + plan.name + "\n"
        string += "  Structure sets:\n"
        for struct in self._rtStructs:
            string += "    " + struct.name + "\n"
        return string

    @property
    def images(self):
        # Doing this ensures that the user can't append directly to images
        return [image for image in self._images]

    def appendImage(self, image):
        """
        Append image to patient's image list

        Parameters
        ----------
        image: object
            image object

        """
        self._images.append(image)
        self.imageAddedSignal.emit(image)

    def hasImage(self, image):
        """
         Check if image is in patient's image list

        Parameters
        ----------
        image: object
             image object

        """
        return image in self._images

    def removeImage(self, image):
        """
        Remove image from patient's image list

        Parameters
        ----------
        image: object
            the image object to removed

        """
        self._images.remove(image)
        self.imageRemovedSignal.emit(image)

    @property
    def name(self):
        #TODO
        return None

    @property
    def plans(self):
        # Doing this ensures that the user can't append directly to plans
        return [plan for plan in self._plans]

    def appendPlan(self, plan):
        self._plans.append(plan)
        self.planAddedSignal.emit(plan)

    def removePlan(self, plan):
        self._plans.remove(plan)
        self.planRemovedSignal.emit(plan)

    @property
    def rtStructs(self):
        # Doing this ensures that the user can't append directly to rtStructs
        return [rtStruct for rtStruct in self._rtStructs]

    def appendRTStruct(self, struct):
        """
        Append RTStruct object to patient's RTStruct list

        Parameters
        ----------
        struct: RTStruct object
            Structure set to append

        """
        self._rtStructs.append(struct)
        self.rtStructAddedSignal.emit(struct)

    def removeRTStruct(self, struct):
        """
        Remove RTStruct from patient's RTStruct list

        Parameters
        ----------
        struct: RTStruct object
            Structure set to remove

        """
        self._rtStructs.remove(struct)
        self.rtStructRemovedSignal.emit(struct)

    @property
    def dynamic3DSequences(self):
        # Doing this ensures that the user can't append directly to dynamic3DSequences
        return [dynamic3DSequence for dynamic3DSequence in self._dynamic3DSequences]

    def appendDyn3DSeq(self, dyn3DSeq):
        """
        Append dynamic3DSequence object to patient's dynamic3DSequences list

        Parameters
        ----------
        dyn3DSeq: dynamic3DSequence object
            Dynamic 3D Sequence set to append

        """
        self._dynamic3DSequences.append(dyn3DSeq)
        self.dyn3DSeqAddedSignal.emit(dyn3DSeq)

    def removeDyn3DSeq(self, dyn3DSeq):
        """
        Remove dynamic3DSequence from patient's dynamic3DSequences list

        Parameters
        ----------
        dyn3DSeq: dynamic3DSequence object
            Dynamic 3D Sequence set to remove

        """
        self._dynamic3DSequences.remove(dyn3DSeq)
        self.dyn3DSeqRemovedSignal.emit(dyn3DSeq)

    @property
    def dynamic3DModels(self):
        # Doing this ensures that the user can't append directly to dynamic3DModels
        return [dynamic3DModel for dynamic3DModel in self._dynamic3DModels]

    def appendDyn3DMod(self, dyn3DMod):
        """
        Append dynamic3DModel object to patient's dynamic3DModels list

        Parameters
        ----------
        dyn3DMod: dynamic3DModel object
            Dynamic 3D Model set to append

        """
        self._dynamic3DModels.append(dyn3DMod)
        self.dyn3DModAddedSignal.emit(dyn3DMod)

    def removeDyn3DMod(self, dyn3DMod):
        """
        Remove dynamic3DModel from patient's dynamic3DModels list

        Parameters
        ----------
        dyn3DMod: dynamic3DModel object
            Dynamic 3D Model set to remove

        """
        self._dynamic3DModels.remove(dyn3DMod)
        self.dyn3DModRemovedSignal.emit(dyn3DMod)
