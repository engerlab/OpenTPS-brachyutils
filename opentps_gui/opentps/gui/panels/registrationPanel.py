from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QPushButton

from opentps.core.data.images import CTImage
from opentps.core.data._patient import Patient
from opentps.core.processing.registration.registrationMorphons import RegistrationMorphons
from opentps.core.processing.registration.registrationDemons import RegistrationDemons
from opentps.core.processing.registration.registrationRigid import RegistrationRigid

class RegistrationPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController
        self._ctImages = []
        self._selectedFixed = None
        self._selectedMoving = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._fixedLabel = QLabel('Fixed CT:')
        self.layout.addWidget(self._fixedLabel)
        self._fixedComboBox = QComboBox(self)
        self._fixedComboBox.currentIndexChanged.connect(self._handleFixedIndex)
        self.layout.addWidget(self._fixedComboBox)

        self._movingLabel = QLabel('Moving CT:')
        self.layout.addWidget(self._movingLabel)
        self._movingComboBox = QComboBox(self)
        self._movingComboBox.currentIndexChanged.connect(self._handleMovingIndex)
        self.layout.addWidget(self._movingComboBox)

        self._regLabel = QLabel('registration method:')
        self._methods = ['Morphons', 'Demons', 'Rigid']
        self.layout.addWidget(self._regLabel)
        self._regComboBox = QComboBox(self)
        self._regComboBox.currentIndexChanged.connect(self._handleRegIndex)
        self.layout.addWidget(self._regComboBox)
        for reg in self._methods:
            self._regComboBox.addItem(reg)

        self._runButton = QPushButton('Register')
        self._runButton.clicked.connect(self._run)
        self.layout.addWidget(self._runButton)

        self.layout.addStretch()

        self.setCurrentPatient(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

    def _handleFixedIndex(self, *args):
        self._selectedFixed = self._ctImages[self._fixedComboBox.currentIndex()]

    def _handleMovingIndex(self, *args):
        self._selectedMoving = self._ctImages[self._movingComboBox.currentIndex()]

    def _handleRegIndex(self, *args):
        self._selectedReg = self._methods[self._regComboBox.currentIndex()]

    def setCurrentPatient(self, patient:Patient):
        if not (self._patient is None):
            self._patient.imageAddedSignal.disconnect(self._handleImageAddedOrRemoved)
            self._patient.imageRemovedSignal.disconnect(self._handleImageAddedOrRemoved)

        self._patient = patient

        if self._patient is None:
            self._removeAllCTs()
        else:
            self._patient.imageAddedSignal.connect(self._handleImageAddedOrRemoved)
            self._patient.imageRemovedSignal.connect(self._handleImageAddedOrRemoved)

            self._updateCTComboBoxes()

    def _updateCTComboBoxes(self):
        self._removeAllCTs()

        self._ctImages = [ct for ct in self._patient.getPatientDataOfType(CTImage)]

        for ct in self._ctImages:
            self._addFixed(ct)
            self._addMoving(ct)

        try:
            currentIndex = self._ctImages.index(self._selectedFixed)
            self._fixedComboBox.setCurrentIndex(currentIndex)
        except:
            self._fixedComboBox.setCurrentIndex(0)
            if len(self._ctImages):
                self._selectedFixed = self._ctImages[0]

        try:
            currentIndex = self._ctImages.index(self._selectedMoving)
            self._movingComboBox.setCurrentIndex(currentIndex)
        except:
            self._movingComboBox.setCurrentIndex(0)
            if len(self._ctImages):
                self._selectedMoving = self._ctImages[0]

    def _removeAllCTs(self):
        for fixed in self._ctImages:
            self._removeFixed(fixed)
        for moving in self._ctImages:
            self._removeMoving(moving)

    def _addFixed(self, fixed:CTImage):
        self._fixedComboBox.addItem(fixed.name, fixed)
        fixed.nameChangedSignal.connect(self._handleFixedChanged)

    def _addMoving(self, moving:CTImage):
        self._movingComboBox.addItem(moving.name, moving)
        moving.nameChangedSignal.connect(self._handleMovingChanged)

    def _removeFixed(self, fixed:CTImage):
        if fixed==self._selectedFixed:
            self._selectedFixed = None

        fixed.nameChangedSignal.disconnect(self._handleFixedChanged)
        self._fixedComboBox.removeItem(self._fixedComboBox.findData(fixed))

    def _removeMoving(self, moving:CTImage):
        if moving==self._selectedMoving:
            self._selectedMoving = None

        moving.nameChangedSignal.disconnect(self._handleMovingChanged)
        self._movingComboBox.removeItem(self._movingComboBox.findData(moving))

    def _handleImageAddedOrRemoved(self, image):
        self._updateCTComboBoxes()

    def _handleFixedChanged(self, fixed):
        self._updateCTComboBoxes()

    def _handleMovingChanged(self, moving):
        self._updateCTComboBoxes()

    def _run(self):

        if self._selectedReg == 'Morphons':
            reg = RegistrationMorphons(self._selectedFixed, self._selectedMoving)
        elif self._selectedReg == 'Demons':
            reg = RegistrationDemons(self._selectedFixed, self._selectedMoving)
        elif self._selectedReg == 'Rigid':
            reg = RegistrationRigid(self._selectedFixed, self._selectedMoving)
        else:
            print('Not yet implemented')
        reg.compute()
        deformed = reg.deformed
        deformed.patient = self._selectedMoving.patient
