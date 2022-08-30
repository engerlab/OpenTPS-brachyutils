

from PyQt5 import QtCore
from PyQt5.QtCore import QDir, QMimeData, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QDrag, QFont, QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeView, QComboBox, QPushButton, QFileDialog, QDialog, \
    QStackedWidget, QListView, QLineEdit, QAbstractItemView, QHBoxLayout, QCheckBox

import Core.IO.dataLoader as dataLoader
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.image2D import Image2D
from Core.Data.DynamicData.dynamic3DSequence import Dynamic3DSequence
from Core.Data.DynamicData.dynamic2DSequence import Dynamic2DSequence
from Core.Data.DynamicData.dynamic3DModel import Dynamic3DModel
from Core.Data.Plan.rtPlan import RTPlan
from Core.IO.serializedObjectIO import saveDataStructure
from Core.event import Event
from GUI.Panels.patientDataMenu import PatientDataMenu
from GUI.Viewer.dataViewer import DroppedObject


class PatientDataPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        # Events
        self.patientAddedSignal = Event(object)
        self.patientRemovedSignal = Event(object)

        self._viewController = viewController

        self._viewController.patientAddedSignal.connect(self.patientAddedSignal.emit)
        self._viewController.patientAddedSignal.connect(self._handleNewPatient)

        self._viewController.patientRemovedSignal.connect(self.patientRemovedSignal.emit)
        self._viewController.patientRemovedSignal.connect(self._handleRemovedPatient)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.patientBox = PatientComboBox(self._viewController)
        self.layout.addWidget(self.patientBox)

        self.patientDataTree = PatientDataTree(self._viewController, self)
        self.layout.addWidget(self.patientDataTree)

        self.buttonLayout = QHBoxLayout()
        loadDataButton = QPushButton('Load Data')
        loadDataButton.clicked.connect(self.loadData)
        self.buttonLayout.addWidget(loadDataButton)
        saveDataButton = QPushButton('Save Data (Serialized)')
        saveDataButton.clicked.connect(self.saveData)
        self.buttonLayout.addWidget(saveDataButton)
        self.layout.addLayout(self.buttonLayout)

        self.dataPath = QDir.currentPath() # maybe not the ideal default data directory

    def _handleNewPatient(self, patient):
        if self._viewController.currentPatient is None:
            self._viewController.currentPatient = patient

    def _handleRemovedPatient(self, patient):
        if self._viewController.currentPatient == patient:
            self._viewController.currentPatient = None

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
class PatientComboBox(QComboBox):
    def __init__(self, viewController):
        QComboBox.__init__(self)

        self._viewController = viewController

        self._viewController.patientAddedSignal.connect(self._addPatient)
        self._viewController.patientRemovedSignal.connect(self._removePatient)

        if not (self._viewController.currentPatient is None):
            self._addPatient(self._viewController.currentPatient)

        self.currentIndexChanged.connect(self._setCurrentPatient)

    def _addPatient(self, patient):
        name = patient.name
        if name is None:
            name = 'None'

        self.addItem(name, patient)
        if self.count() == 1:
            self._viewController.currentPatient = patient

    def _removePatient(self, patient):
        self.removeItem(self.findData(patient))

    def _setCurrentPatient(self, index):
        self._viewController.currentPatient = self.currentData()


## ------------------------------------------------------------------------------------------
class PatientDataTree(QTreeView):
    def __init__(self, viewController, patientDataPanel):
        QTreeView.__init__(self)

        self._currentPatient = None
        self.patientDataPanel = patientDataPanel
        self._viewController = viewController

        self.setHeaderHidden(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.viewport().installEventFilter(self)
        self.customContextMenuRequested.connect(self._handleRightClick)
        self.resizeColumnToContents(0)
        self.doubleClicked.connect(self._handleDoubleClick)
        self.treeModel = QStandardItemModel()
        self.setModel(self.treeModel)
        self.setColumnHidden(1, True)
        self.expandAll()

        self.buildDataTree(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.buildDataTree)


        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)

    def _appendData(self, data):
        if isinstance(data, Image3D) or isinstance(data, RTPlan) or isinstance(data, Dynamic3DSequence) or isinstance(data, Dynamic2DSequence):
            rootItem = PatientDataItem(data)
            self.rootNode.appendRow(rootItem)

            if isinstance(data, Dynamic3DSequence):
                for image in data.dyn3DImageList:
                    item = PatientDataItem(image)
                    rootItem.appendRow(item)
                self.rootNode.appendRow(rootItem)

            if isinstance(data, Dynamic2DSequence):
                for image in data.dyn2DImageList:
                    item = PatientDataItem(image)
                    rootItem.appendRow(item)
                self.rootNode.appendRow(rootItem)

    def _removeData(self, data):
        items = []

        for row in range(self.model().rowCount()):
            item = self.model().itemFromIndex(self.model().index(row, 0))
            items.append(item)

        for item in items:
            if item.data == data:
                self.rootNode.removeRow(item.row())
                item.disconnectAll() #Do this explicitely to be sure signals are disconnected

    def mouseMoveEvent(self, event):
        drag = QDrag(self)
        mimeData = QMimeData()

        mimeData.setText(DroppedObject.DropTypes.IMAGE)
        drag.setMimeData(mimeData)

        drag.exec_(QtCore.Qt.CopyAction)

    def buildDataTree(self, patient):
        # Disconnect signals
        if not(self._currentPatient is None):
            self._currentPatient.patientDataAddedSignal.disconnect(self._appendData)
            self._currentPatient.patientDataRemovedSignal.disconnect(self._removeData)

        # Do this explicitely to be sure signals are disconnected
        for row in range(self.model().rowCount()):
            item = self.model().itemFromIndex(self.model().index(row, 0))
            if isinstance(item, PatientDataItem):
                item.disconnectAll()
        self.treeModel.clear()
        self.rootNode = self.treeModel.invisibleRootItem()
        font_b = QFont()
        font_b.setBold(True)

        self._currentPatient = patient

        if self._currentPatient is None:
            return

        self._currentPatient.patientDataAddedSignal.connect(self._appendData)
        self._currentPatient.patientDataRemovedSignal.connect(self._removeData)

        #TODO: Same with other data

        #images
        images = self._currentPatient.images
        for image in images:
            self._appendData(image)

        if len(images) > 0:
            self._viewController.selectedImage = images[0]

        for plan in patient.plans:
            self._appendData(plan)

        # dynamic sequences
        for dynSeq in patient.dynamic3DSequences:
            self._appendData(dynSeq)

        for dynSeq in patient.dynamic2DSequences:
            self._appendData(dynSeq)

        # dynamic models
        for model in self._currentPatient.dynamic3DModels:
            serieRoot = PatientDataItem(model)
            for field in model.deformationList:
                item = PatientDataItem(field)
                serieRoot.appendRow(item)
            self.rootNode.appendRow(serieRoot)

    def dragEnterEvent(self, event):
        selection = self.selectionModel().selectedIndexes()[0]
        self._viewController.selectedImage = self.model().itemFromIndex(selection).data

    def _handleDoubleClick(self, selection):
        selectedData = self.model().itemFromIndex(selection).data

        if isinstance(selectedData, CTImage) or isinstance(selectedData, Dynamic3DSequence) or isinstance(selectedData, Dynamic2DSequence) or isinstance(selectedData, Image2D):
            self._viewController.mainImage = selectedData
        if isinstance(selectedData, RTPlan):
            self._viewController.plan = selectedData
        elif isinstance(selectedData, Dynamic3DModel):
            self._viewController.mainImage = selectedData.midp
        elif isinstance(selectedData, DoseImage):
            self._viewController.secondaryImage = selectedData

    def _handleRightClick(self, pos):
        pos = self.mapToGlobal(pos)

        selected = self.selectedIndexes()
        selectedData = [self.model().itemFromIndex(selectedData).data for selectedData in selected]

        dataMenu = PatientDataMenu(self._viewController, self)
        dataMenu.selectedData = selectedData
        dataMenu.asContextMenu().popup(pos)



## ------------------------------------------------------------------------------------------
class PatientDataItem(QStandardItem):
    def __init__(self, data, txt="", type="", color=QColor(125, 125, 125)):
        QStandardItem.__init__(self)

        self.data = data
        self.data.nameChangedSignal.connect(self.setName)

        self.setName(self.data.name)

        self.setEditable(False)
        # self.setForeground(color)
        # self.setText(txt)
        # self.setWhatsThis(type)

    def disconnectAll(self):
        self.data.nameChangedSignal.disconnect(self.setName)

    # No effect: it seems that C destructor of QStandardItem does not trigger __del__
    def __del__(self):
        self.disconnectAll()

    def setName(self, name):
        self.setText(name)


## ------------------------------------------------------------------------------------------
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
        self.compressBox = QCheckBox("Compress Data", self)
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
