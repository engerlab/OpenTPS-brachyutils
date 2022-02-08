
from Core.Data.patientInfo import PatientInfo
from Core.api import API
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

        self._name = self.patientInfo.name
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
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name
        self.nameChangedSignal.emit(self._name)


    @property
    def images(self):
        # Doing this ensures that the user can't append directly to images
        return [image for image in self._images]

    @API.loggedViaAPI
    def appendImage(self, image):
        """
        Append image to patient's image list

        Parameters
        ----------
        image: object
            image object

        """
        if image in self._images:
            return

        self._images.append(image)
        image.patient = self
        self.imageAddedSignal.emit(image)

    def getImageIndex(self, _images):
        return self._images.index(_images)

    def hasImage(self, image):
        """
         Check if image is in patient's image list

        Parameters
        ----------
        image: object
             image object

        """
        return image in self._images

    @API.loggedViaAPI
    def removeImage(self, image):
        """
        Remove image from patient's image list

        Parameters
        ----------
        image: object
            the image object to removed

        """

        if not(image in self._images):
            return

        self._images.remove(image)
        self.imageRemovedSignal.emit(image)


    @property
    def plans(self):
        # Doing this ensures that the user can't append directly to plans
        return [plan for plan in self._plans]

    def appendPlan(self, plan):
        if plan in self._planss:
            return

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

        if struct in self._rtStructs:
            return

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
        if dyn3DSeq in self._dynamic3DSequences:
            return

        self._dynamic3DSequences.append(dyn3DSeq)
        dyn3DSeq.patient = self
        self.dyn3DSeqAddedSignal.emit(dyn3DSeq)

    def removeDyn3DSeq(self, dyn3DSeq):
        """
        Remove dynamic3DSequence from patient's dynamic3DSequences list

        Parameters
        ----------
        dyn3DSeq: dynamic3DSequence object
            Dynamic 3D Sequence set to remove

        """
        if not(dyn3DSeq in self._dynamic3DSequences):
            return

        self._dynamic3DSequences.remove(dyn3DSeq)
        dyn3DSeq.patient = None
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


    def hasPatientData(self, data):
        return (data in self._images) or (data in self._plans) or (data in self._dynamic3DModels) or (data in self._dynamic3DSequences) or (data in self._rtStructs)

    def appendPatienData(self, data):
        if isinstance(data, list):
            for d in data:
                self.appendPatienData(d)
            return

        if data in self._images:
            self.appendImage(data)

        if data in self._plans:
            self.appendPlan(data)

        if data in self._rtStructs:
            self.appendRTStruct(data)

        if data in self._dynamic3DSequences:
            self.appendDyn3DSeq(data)

        if data in self._dynamic3DModels:
            self.appendDyn3DMod(data)

    def removePatientData(self, data):
        if isinstance(data, list):
            for d in data:
                self.removePatientData(d)
            return

        if data in self._images:
            self.removeImage(data)

        if data in self._plans:
            self.removePlan(data)

        if data in self._rtStructs:
            self.removeRTStruct(data)

        if data in self._dynamic3DSequences:
            self.removeDyn3DSeq(data)

        if data in self._dynamic3DModels:
            self.removeDyn3DMod(data)


    def dumpableCopy(self):

        dumpablePatientCopy = Patient(patientInfo=self.patientInfo)
        for image in self._images:
            dumpablePatientCopy._images.append(image.dumpableCopy())

        for plan in self._plans:
            dumpablePatientCopy._plans.append(plan.dumpableCopy())

        for struct in self._rtStructs:
            dumpablePatientCopy._rtStructs.append(struct.dumpableCopy())

        for dynamic3DSequence in self._dynamic3DSequences:
            dumpablePatientCopy._dynamic3DSequences.append(dynamic3DSequence.dumpableCopy())

        for dynamic3DModel in self._dynamic3DModels:
            dumpablePatientCopy._dynamic3DModels.append(dynamic3DModel.dumpableCopy())

        return dumpablePatientCopy

    def setSelfInData(self):
        for image in self._images:
            image.patient = self

        for plan in self._plans:
            plan.patient = self

        for struct in self._rtStructs:
            struct.patient = self

        for dynamic3DSequence in self._dynamic3DSequences:
            dynamic3DSequence.patient = self

        for dynamic3DModel in self._dynamic3DModels:
            dynamic3DModel.patient = self

    def removeSelfFromData(self):
        for image in self._images:
            image.patient = None

        for plan in self._plans:
            plan.patient = None

        for struct in self._rtStructs:
            struct.patient = None

        for dynamic3DSequence in self._dynamic3DSequences:
            dynamic3DSequence.patient = None

        for dynamic3DModel in self._dynamic3DModels:
            dynamic3DModel.patient = None