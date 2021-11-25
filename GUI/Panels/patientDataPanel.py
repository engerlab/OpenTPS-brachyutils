from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeView, QComboBox


class PatientDataPanel(QWidget):
    def __init__(self, controller):
        QWidget.__init__(self)

        self._controller = controller

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)


class PatientComboBox(QComboBox):
    def __init__(self, controller):
        QComboBox.__init__(self)

        self._controller = controller

        patientListController = self._controller.getPatientListController()
        patientListController.patientAdded.connect(self._addPatient)
        patientListController.patientRemoved.connect(self._removePatient)

    def _addPatient(self, patientController):
        name = patientController.getName()
        if name is None:
            name = 'None'

        self.addItem(name, patientController)

    def _removePatient(self, patientController):
        self.removeItem(self.findData(patientController))


class PatientImageList(QTreeView):
    def __init__(self, viewController):
        QTreeView.__init__(self)

        self._viewController = viewController

        self.treeModel = QStandardItemModel()
        self.setModel(self.treeModel)
        self.setColumnHidden(1, True)
        self.expandAll()

        self._viewController.getCurrentPatientChanged().connect(self.updateAll)

        self.updateAll(self._viewController.getCurrentPatientController())

    def updateAll(self, patientController):
        self.treeModel.clear()
        self.rootNode = self.treeModel.invisibleRootItem()

        if patientController is None:
            return

        imageControllers = patientController.getImageControllers()
        for imageController in imageControllers:
            item = PatientImageItem(imageController)
            self.rootNode.appendRow(item)


class PatientImageItem(QStandardItem):
    def __init__(self, imageController):
        QStandardItem.__init__(self)

        self._imageController = imageController
        self._imageController.nameChangedSignal.connect(self.setName)

        self.setName(self._imageController.getName())

    def setName(self, name):
        self.setText(name)
