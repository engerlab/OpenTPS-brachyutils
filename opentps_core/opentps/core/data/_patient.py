
__all__ = ['Patient']

from typing import Union, Sequence

from opentps.core.data.images._image3D import Image3D
from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data.plan._planDesign import PlanDesign
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data.dynamicData.dynamic2DSequence import Dynamic2DSequence
from opentps.core.data.dynamicData.dynamic3DModel import Dynamic3DModel
from opentps.core.data.dynamicData.dynamic3DSequence import Dynamic3DSequence
from opentps.core.data._patientData import PatientData
from opentps.core.data._rtStruct import RTStruct
from opentps.core import Event


class Patient:
    """
    A class Patient contains patient information and patient data
    """
    class TypeConditionalEvent(Event):
        def __init__(self, *args):
            super().__init__(*args)

        @classmethod
        def fromEvent(cls, event, newType):
            newEvent = cls(newType)
            event.connect(newEvent.emit)

            return newEvent

        def emit(self, data):
            if isinstance(data, self.objectType):
                super().emit(data)

    def __init__(self, name=None, id=None, birthDate=None, sex=None):
        self.patientDataAddedSignal = Event(object)
        self.patientDataRemovedSignal = Event(object)
        self.imageAddedSignal = self.TypeConditionalEvent.fromEvent(self.patientDataAddedSignal, Image3D)
        self.imageRemovedSignal = self.TypeConditionalEvent.fromEvent(self.patientDataRemovedSignal, Image3D)
        self.roiMaskAddedSignal = self.TypeConditionalEvent.fromEvent(self.patientDataAddedSignal, ROIMask)
        self.roiMaskRemovedSignal = self.TypeConditionalEvent.fromEvent(self.patientDataRemovedSignal, ROIMask)
        self.rtStructAddedSignal =self.TypeConditionalEvent.fromEvent(self.patientDataAddedSignal, RTStruct)
        self.rtStructRemovedSignal = self.TypeConditionalEvent.fromEvent(self.patientDataRemovedSignal, RTStruct)
        self.planAddedSignal = self.TypeConditionalEvent.fromEvent(self.patientDataAddedSignal, RTPlan)
        self.planRemovedSignal = self.TypeConditionalEvent.fromEvent(self.patientDataRemovedSignal, RTPlan)
        self.planStructureAddedSignal = self.TypeConditionalEvent.fromEvent(self.patientDataAddedSignal, PlanDesign)
        self.planStructureRemovedSignal = self.TypeConditionalEvent.fromEvent(self.patientDataRemovedSignal, PlanDesign)
        self.dyn3DSeqAddedSignal = self.TypeConditionalEvent.fromEvent(self.patientDataAddedSignal, Dynamic3DSequence)
        self.dyn3DSeqRemovedSignal = self.TypeConditionalEvent.fromEvent(self.patientDataRemovedSignal, Dynamic3DSequence)
        self.dyn3DModAddedSignal = self.TypeConditionalEvent.fromEvent(self.patientDataAddedSignal, Dynamic3DModel)
        self.dyn3DModRemovedSignal = self.TypeConditionalEvent.fromEvent(self.patientDataRemovedSignal, Dynamic3DModel)
        self.nameChangedSignal = Event(object)

        self._name = name
        self.id = id
        self.birthDate = birthDate
        self.sex = sex
        self._patientData = []
        self._images = []
        self._plans = []
        self._rtStructs = []
        self._dynamic3DSequences = []
        self._dynamic3DModels = []


    def __str__(self):
        string = "Patient name: " + self.name + "\n"
        string += "  images:\n"
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
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name:str):
        self._name = name
        self.nameChangedSignal.emit(self._name)

    @property
    def images(self) -> Sequence[Image3D]:
        return self.getPatientDataOfType(Image3D)

    @property
    def plans(self) -> Sequence[RTPlan]:
        return self.getPatientDataOfType(RTPlan)

    @property
    def roiMasks(self) -> Sequence[ROIMask]:
        return self.getPatientDataOfType(ROIMask)

    @property
    def rtStructs(self) -> Sequence[RTStruct]:
        return self.getPatientDataOfType(RTStruct)

    @property
    def dynamic3DSequences(self) -> Sequence[Dynamic3DSequence]:
        return self.getPatientDataOfType(Dynamic3DSequence)

    @property
    def dynamic3DModels(self) -> Sequence[Dynamic3DModel]:
        return self.getPatientDataOfType(Dynamic3DModel)

    @property
    def dynamic2DSequences(self) -> Sequence[Dynamic2DSequence]:
        return self.getPatientDataOfType(Dynamic2DSequence)

    @property
    def patientData(self) -> Sequence[PatientData]:
        return [data for data in self._patientData]

    def getPatientDataOfType(self, dataType):
        ## data type can be given as a str or the data type directly
        if isinstance(dataType, str):
            return [data for data in self._patientData if data.getTypeAsString() == dataType]
        else:
            return [data for data in self._patientData if isinstance(data, dataType)]

    def hasPatientData(self, data:PatientData):
        return (data in self._patientData)

    def appendPatientData(self, data:Union[Sequence[PatientData], PatientData]):
        if isinstance(data, list):
            self.appendPatientDataList(data)

        if not (data in self._patientData):
            self._patientData.append(data)
            data.patient = self
            self.patientDataAddedSignal.emit(data)

    def appendPatientDataList(self, dataList:Sequence[PatientData]):
        for data in dataList:
            self.appendPatientData(data)

    def removePatientData(self, data:Union[Sequence[PatientData], PatientData]):
        if isinstance(data, list):
            self.removePatientDataList(data)

        if data in self._patientData:
            self._patientData.remove(data)

            self.patientDataRemovedSignal.emit(data)

    def removePatientDataList(self, dataList:Sequence[PatientData]):
        for data in dataList:
            self.removePatientData(data)
        return

    def getTypeAsString(self) -> str:
        return self.__class__.__name__


    def dumpableCopy(self):
        """
        deprecated?
        """
        dumpablePatientCopy = Patient()
        for data in self._patientData:
            dumpablePatientCopy._patientData.append(data.dumpableCopy())

        return dumpablePatientCopy
