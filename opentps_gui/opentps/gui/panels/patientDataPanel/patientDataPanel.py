
from PyQt5.QtCore import QDir
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QDialog, \
    QStackedWidget, QListView, QLineEdit, QHBoxLayout, QCheckBox

import opentps.core.io.dataLoader as dataLoader
from opentps.core.io.serializedObjectIO import saveDataStructure
from opentps.core import Event
from opentps.gui.panels.patientDataPanel.patientDataSelection import PatientDataSelection


class PatientDataPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        # Events
        self.patientAddedSignal = Event(object)
        self.patientRemovedSignal = Event(object)

        self._viewController = viewController

        self._viewController.patientAddedSignal.connect(self.patientAddedSignal.emit)

        self._viewController.patientRemovedSignal.connect(self.patientRemovedSignal.emit)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._patientDataSelection = PatientDataSelection(self._viewController)
        self.layout.addWidget(self._patientDataSelection)

        self.buttonLayout = QHBoxLayout()
        loadDataButton = QPushButton('Load data')
        loadDataButton.clicked.connect(self.loadData)
        self.buttonLayout.addWidget(loadDataButton)
        saveDataButton = QPushButton('Save data (Serialized)')
        saveDataButton.clicked.connect(self.saveData)
        self.buttonLayout.addWidget(saveDataButton)
        self.layout.addLayout(self.buttonLayout)

        self.dataPath = QDir.currentPath() # maybe not the ideal default data directory

    def loadData(self):
        filesOrFoldersList = _getOpenFilesAndDirs(caption="Open patient data files or folders", directory=QDir.currentPath())
        if len(filesOrFoldersList) < 1:
            return

        splitPath = filesOrFoldersList[0].split('/')
        withoutLastElementPath = ''
        for element in splitPath[:-1]:
            withoutLastElementPath += element + '/'
        self.dataPath = withoutLastElementPath

        dataLoader.loadData(self._viewController._patientList, filesOrFoldersList)

    def saveData(self):
        fileDialog = SaveData_dialog()
        savingPath, compressedBool, splitPatientsBool = fileDialog.getSaveFileName(None, dir=self.dataPath)

        patientList = self._viewController.activePatients
        # patientList = [patient.dumpableCopy() for patient in self._viewController._patientList]
        saveDataStructure(patientList, savingPath, compressedBool=compressedBool, splitPatientsBool=splitPatientsBool)

## ------------------------------------------------------------------------------------------
class SaveData_dialog(QFileDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.defaultName = "Patient"

    def getSaveFileName(self, parent=None,
                        caption="Select folder and file name to save data tree",
                        dir=".",
                        filter='',
                        initialFilter='',
                        defaultName="Patient",
                        options=None):

        self.setWindowTitle(caption)
        self.setDirectory(dir)
        self.selectFile(defaultName)
        self.setAcceptMode(QFileDialog.AcceptSave)  # bouton "Save"
        self.setOption(QFileDialog.DontUseNativeDialog, True)

        layout = self.layout()
        # checkBoxLayout = QHBoxLayout
        self.compressBox = QCheckBox("Compress data", self)
        self.compressBox.setToolTip('This will compress the data before saving them, it takes longer to save the data this way')
        layout.addWidget(self.compressBox, 4, 0)
        self.splitPatientsBox = QCheckBox("Split Patients", self)
        self.splitPatientsBox.setToolTip('This will split patients into multiple files if multiple patients data are loaded')
        layout.addWidget(self.splitPatientsBox, 4, 1)
        self.setLayout(layout)

        if self.exec_():
            return self.selectedFiles()[0], self.compressBox.isChecked(), self.splitPatientsBox.isChecked()
        else:
            return "", ""

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