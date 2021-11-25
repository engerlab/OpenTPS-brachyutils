from PyQt5.QtCore import QDir
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeView, QComboBox, QPushButton, QFileDialog, QDialog, \
    QStackedWidget, QListView, QLineEdit

from Controllers.modelController import ModelController


class PatientDataPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._viewController = viewController

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        patientBox = PatientComboBox(self._viewController)
        self.layout.addWidget(patientBox)

        imageList = PatientImageList(self._viewController)
        self.layout.addWidget(imageList)

        loadDataButton = QPushButton('Load data')
        loadDataButton.clicked.connect(self.loadData)
        self.layout.addWidget(loadDataButton)

    def loadData(self):
        file = _getOpenFilesAndDirs(caption="Open patient data files or folders", directory=QDir.currentPath())
        ModelController().getAPI().readDicomImage(file)


class PatientComboBox(QComboBox):
    def __init__(self, viewController):
        QComboBox.__init__(self)

        self._viewController = viewController

        patientListController = self._viewController.getPatientListController()
        patientListController.patientAdded.connect(self._addPatient)
        patientListController.patientRemoved.connect(self._removePatient)

        self._setActivePatientController = lambda index: self._viewController.setActivePatientController(self.currentData())
        self.currentIndexChanged.connect(self._setActivePatientController)

    def __del__(self):
        self.currentIndexChanged.disconnect(self._setActivePatientController)

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

        self._viewController.currentPatientChangedSignal.connect(self.updateAll)

        self.updateAll(self._viewController.getActivePatientController())

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


def _getOpenFilesAndDirs(parent=None, caption='', directory='',
                          filter='', initialFilter='', options=None):
    def updateText():
      # update the contents of the line edit widget with the selected files
      selected = []
      for index in view.selectionModel().selectedRows():
        selected.append('"{}"'.format(index.data()))
      lineEdit.setText(' '.join(selected))

    dialog = QFileDialog(parent, windowTitle=caption)
    dialog.setFileMode(dialog.ExistingFiles)
    if options:
      dialog.setOptions(options)
    dialog.setOption(dialog.DontUseNativeDialog, True)
    if directory:
      dialog.setDirectory(directory)
    if filter:
      dialog.setNameFilter(filter)
      if initialFilter:
        dialog.selectNameFilter(initialFilter)

    # by default, if a directory is opened in file listing mode,
    # QFileDialog.accept() shows the contents of that directory, but we
    # need to be able to "open" directories as we can do with files, so we
    # just override accept() with the default QDialog implementation which
    # will just return exec_()
    dialog.accept = lambda: QDialog.accept(dialog)

    # there are many item views in a non-native dialog, but the ones displaying
    # the actual contents are created inside a QStackedWidget; they are a
    # QTreeView and a QListView, and the tree is only used when the
    # viewMode is set to QFileDialog.Details, which is not this case
    stackedWidget = dialog.findChild(QStackedWidget)
    view = stackedWidget.findChild(QListView)
    view.selectionModel().selectionChanged.connect(updateText)

    lineEdit = dialog.findChild(QLineEdit)
    # clear the line edit contents whenever the current directory changes
    dialog.directoryEntered.connect(lambda: lineEdit.setText(''))

    dialog.exec_()
    return dialog.selectedFiles()
