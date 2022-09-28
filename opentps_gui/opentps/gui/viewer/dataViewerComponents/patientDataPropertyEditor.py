import functools
import inspect
import typing

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMainWindow

from opentps.core.data.plan import PlanIonBeam
from opentps.core.data.plan import PlanIonLayer
from opentps.core.data.plan import PlanIonSpot
from opentps.core.data.plan import RangeShifter
from opentps.core.data import PatientData
from opentps.core import Event

class PatientDataPropertyEditor(QWidget):
    def __init__(self, image, parent=None):
        super().__init__(parent=parent)

        self._mainLayout = QVBoxLayout(self)
        self.setLayout(self._mainLayout)

        for property in inspect.getmembers(image):
            # to remove private and protected
            # functions
            if not property[0].startswith('_'):
                # To remove other methods that
                # does not start with an underscore
                if not inspect.ismethod(property[1]):
                    if not isinstance(property[1], Event):
                        self._mainLayout.addWidget(TwoRowElement(property, parent=self))


class TwoRowElement(QWidget):
    def __init__(self, property, parent=None):
        super().__init__(parent)

        self._mainLayout = QHBoxLayout(self)
        self.setLayout(self._mainLayout)

        self._txt = QLabel(self)
        self._txt.setText(property[0])

        self._mainLayout.addWidget(self._txt)

        val = property[1]

        if isinstance(val, self.supportedTypes()):
            val = [val]

        if isinstance(val, typing.Sequence) and len(val)>0 and isinstance(val[0], self.supportedTypes()):
            for valElement in val:
                patientDataButton = QPushButton(self)
                patientDataButton.setText(str(valElement.__class__.__name__))
                patientDataButton.clicked.connect(functools.partial(self._openPatientData, valElement))
                self._mainLayout.addWidget(patientDataButton)
        else:
            self._nameLineEdit = QLineEdit(self)
            self._nameLineEdit.setText(str(val))
            self._txt.setBuddy(self._nameLineEdit)
            self._mainLayout.addWidget(self._nameLineEdit)

        self._mainLayout.addStretch()

    def _openPatientData(self, patientData:PatientData):
        w = QMainWindow(self.parent().parent())
        w.setWindowTitle('Image info')
        w.resize(400, 400)
        w.setCentralWidget(PatientDataPropertyEditor(patientData, self.parent().parent()))
        w.show()

    def supportedTypes(self):
        return typing.Union[PatientData, PlanIonBeam, PlanIonLayer, PlanIonSpot, RangeShifter].__args__