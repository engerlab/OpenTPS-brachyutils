from PyQt5 import QtCore
from PyQt5.QtCore import QDir, QMimeData, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QDrag, QFont, QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeView, QComboBox, QPushButton, QFileDialog, QDialog, \
    QStackedWidget, QListView, QLineEdit, QAbstractItemView, QMenu, QAction, QInputDialog, QHBoxLayout, QCheckBox, \
    QMessageBox, QMainWindow

from pydicom.uid import generate_uid
import pickle  ## temporary to test something

from Controllers.api import API
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.image3D import Image3D
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from Core.Data.dynamic3DModel import Dynamic3DModel
from Core.IO.serializedObjectIO import saveDataStructure, saveSerializedObject
from Core.event import Event
from GUI.Viewer.Viewers.imageProperies import ImageProperties


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
        if len(filesOrFoldersList)<1:
            return

        splitPath = filesOrFoldersList[0].split('/')
        withoutLastElementPath = ''
        for element in splitPath[:-1]:
            withoutLastElementPath += element + '/'
        self.dataPath = withoutLastElementPath

        API.loadData(filesOrFoldersList)

    def saveData(self):
        fileDialog = SaveData_dialog()
        savingPath, compressedBool, splitPatientsBool = fileDialog.getSaveFileName(None, dir=self.dataPath)

        # patientList = self._viewController.activePatients
        patientList = [patient.dumpableCopy() for patient in self._viewController._patientList]
        saveDataStructure(patientList, savingPath, compressedBool=compressedBool, splitPatientsBool=splitPatientsBool)


## ------------------------------------------------------------------------------------------
class PatientComboBox(QComboBox):
    def __init__(self, viewController):
        QComboBox.__init__(self)

        self._viewController = viewController

        self._viewController.patientAddedSignal.connect(self._addPatient)
        self._viewController.patientRemovedSignal.connect(self._removePatient)

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
        rootItem = PatientDataItem(data)
        self.rootNode.appendRow(rootItem)

        if isinstance(data, Dynamic3DSequence):
            for image in data.dyn3DImageList:
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

    def mouseMoveEvent(self, event):
        drag = QDrag(self)
        mimeData = QMimeData()

        mimeData.setText('image')
        drag.setMimeData(mimeData)

        drag.exec_(QtCore.Qt.CopyAction)

    def buildDataTree(self, patient):
        """
        What if instead of trying to put in bold the shown data, with the issues of UID that must saved for each viewer etc ...
        We simply show the image, dose, dyn seq and plan name on the viewer or on a QTip that shown when the mouse is over it ?
        """

        # Disconnect signals
        if not(self._currentPatient is None):
            self._currentPatient.imageAddedSignal.disconnect(self._appendData)
            self._currentPatient.dyn3DSeqAddedSignal.disconnect(self._appendData)
            self._currentPatient.dyn3DSeqRemovedSignal.disconnect(self._removeData)
            self._currentPatient.imageRemovedSignal.disconnect(self._removeData)

        self.treeModel.clear()
        self.rootNode = self.treeModel.invisibleRootItem()
        font_b = QFont()
        font_b.setBold(True)

        self._currentPatient = patient

        if self._currentPatient is None:
            return

        self._currentPatient.imageAddedSignal.connect(self._appendData)
        self._currentPatient.imageRemovedSignal.connect(self._removeData)
        self._currentPatient.dyn3DSeqAddedSignal.connect(self._appendData)
        self._currentPatient.dyn3DSeqRemovedSignal.connect(self._removeData)
        #TODO: Same with other data

        #images
        images = self._currentPatient.images
        for image in images:
            self._appendData(image)

        if len(images) > 0:
            self._viewController.selectedImage = images[0]

        # dynamic sequences
        for dynSeq in patient.dynamic3DSequences:
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
        # self.patientController = self.patientDataPanel.getCurrentPatientController()  # not used for now
        # self._viewController.shownDataUIDsList.append(selectedDataController.data.seriesInstanceUID)  # not used for now

        if isinstance(selectedData, CTImage):
            self._viewController.mainImage = selectedData

        #from 4D branch
        # selected_type = self.model().itemFromIndex(selection).whatsThis()
        # print(selected_type)
        # selected_UID = selection.model().data(selection.model().index(selection.row(), 1, selection.parent()))
        # is_bold = selection.model().itemFromIndex(selection).font().bold()
        #
        # if is_bold and selected_type != 'CT':
        #     print('Unselected for display:', selected_UID)
        # else:
        #     print('Selected for display:', selected_UID)
        #
        # if selected_type == 'CT':
        #     self.Current_CT_changed.emit(selected_UID)
        #     self.ROI_list_changed.emit()
        #     return
        # elif selected_type == 'dose':
        #     if is_bold:
        #         self.Current_dose_changed.emit("")
        #     else:
        #         self.Current_dose_changed.emit(selected_UID)
        #     return
        # elif selected_type == 'plan':
        #     if is_bold:
        #         self.Current_plan_changed.emit("")
        #     else:
        #         self.Current_plan_changed.emit(selected_UID)
        #     return
        # elif selected_type == 'field':
        #     if is_bold:
        #         self.Current_field_changed.emit("")
        #     else:
        #         self.Current_field_changed.emit(selected_UID)
        #     return
        #
        # for seriesIndex, series in enumerate(self.Patients.list[0].Dyn4DSeqList):
        #     serieRoot = series.SOPInstanceUID
        #     if serieRoot == selected_UID:
        #         print("Series selected", serieRoot, "seriesIndex:", seriesIndex)
        #         self.DynamicImage_selected.emit([selected_UID, 'dyn4DSeq', seriesIndex])
        #         return
        #
        # for seriesIndex, series in enumerate(self.Patients.list[0].Dyn2DSeqList):
        #     serieRoot = series.SOPInstanceUID
        #     if serieRoot == selected_UID:
        #         print("Series selected", serieRoot, "seriesIndex:", seriesIndex)
        #         self.DynamicImage_selected.emit([selected_UID, 'dyn2DSeq', seriesIndex])
        #         return

    def _handleRightClick(self, pos):
        UIDs = []
        selectedDataTypeList = []
        pos = self.mapToGlobal(pos)
        selected = self.selectedIndexes()
        selectedData = [self.model().itemFromIndex(selectedData).data for selectedData in selected]

        dataClass = selectedData[0].__class__
        for data in selectedData:
            if data.__class__ != dataClass:
                dataClass = 'mixed'
                break

        print('Right click options class: ', dataClass)

        if (len(selected) > 0):
            self.context_menu = QMenu()

            # actions for 3D images
            if (dataClass == Image3D or issubclass(dataClass, Image3D)) and len(selected) == 1:
                self.rename_action = QAction("Rename")
                self.export_action = QAction("Export")
                self.superimpose_action = QAction("Superimpose")
                self.info_action = QAction("Info")
                self.rename_action.triggered.connect(lambda checked: openRenameDataDialog(self, selectedData[0]))
                self.export_action.triggered.connect(
                    lambda checked, data_type=dataClass, UIDs=UIDs: self.export_item(dataClass, UIDs))
                self.superimpose_action.triggered.connect(
                    lambda checked: self._setSecondaryImage(selectedData[0]))
                self.info_action.triggered.connect(
                    lambda checked: self._showImageInfo(selectedData[0]))
                self.context_menu.addAction(self.rename_action)
                self.context_menu.addAction(self.export_action)
                self.context_menu.addAction(self.superimpose_action)
                self.context_menu.addAction(self.info_action)

            if dataClass == 'mixed':
                self.no_action = QAction("No action available for this group of data")
                self.context_menu.addAction(self.no_action)

            # actions for group of 3DImage
            if (dataClass == CTImage or issubclass(dataClass, CTImage)) and len(selected) > 1:  # to generalize to other modalities eventually
                self.make_series_action = QAction("Make dynamic 3D sequence")
                self.make_series_action.triggered.connect(
                    lambda checked: self.createDynamic3DSequence(selectedData))
                self.context_menu.addAction(self.make_series_action)

            # actions for any 3DImage
            # if (dataClass == 'CTImage'):
            #     self.crop_action = QAction("Crop")
            #     self.crop_action.triggered.connect(
            #         lambda checked, data_type=dataClass, UIDs=UIDs: self.crop_image(UIDs[0]))
            #     self.context_menu.addAction(self.crop_action)

            # actions specific to an image selected with deformation fields
            # if (dataClass == 'mixed' and len(UIDs) > 1 and selectedDataTypeList[0] == 'CTImage'):
            #     fields_only = True
            #     for i in range(len(selectedDataTypeList) - 1):
            #         if selectedDataTypeList[i + 1] != 'field':
            #             fields_only = False
            #     if fields_only:
            #         self.make_4d_model_action = QAction("Make 4D model (MidP)")
            #         self.make_4d_model_action.triggered.connect(
            #             lambda checked, data_types=selectedDataTypeList, UIDs=UIDs: self.make_4d_model(data_types, UIDs))
            #         self.context_menu.saddAction(self.make_4d_model_action)

            # actions for single Dynamic3DSequence
            if (dataClass == Dynamic3DSequence and len(selected) == 1):# or dataClass == 'Dynamic2DSequence'):
                self.compute3DModelAction = QAction("Compute 4D model (MidP)")
                self.compute3DModelAction.triggered.connect(
                    lambda checked, selected3DSequence=selectedData[0]: self.computeDynamic3DModel(selected3DSequence))
                self.context_menu.addAction(self.compute3DModelAction)

            # # actions for plans
            # if (dataClass == 'plan' and len(UIDs) == 1):
            #     plan = self.Patients.find_plan(UIDs[0])
            #     if (plan.ScanMode == 'LINE'):
            #         self.convert_action = QAction("Convert line scanning to PBS plan")
            #         self.convert_action.triggered.connect(lambda checked: plan.convert_LineScanning_to_PBS())
            #         self.context_menu.addAction(self.convert_action)
            #
            #     self.display_spot_action = []
            #     self.display_spot_action.append(QAction("Display spots (full plan)"))
            #     self.display_spot_action[0].triggered.connect(
            #         lambda checked, beam=-1: self.Viewer_display_spots.emit(beam))
            #     self.context_menu.addAction(self.display_spot_action[0])
            #     for b in range(len(plan.Beams)):
            #         self.display_spot_action.append(QAction("Display spots (Beam " + str(b + 1) + ")"))
            #         self.display_spot_action[b + 1].triggered.connect(
            #             lambda checked, beam=b: self.Viewer_display_spots.emit(beam))
            #         self.context_menu.addAction(self.display_spot_action[b + 1])
            #
            #     self.remove_spot_action = QAction("Remove displayed spots")
            #     self.remove_spot_action.triggered.connect(self.Viewer_clear_spots.emit)
            #     self.context_menu.addAction(self.remove_spot_action)
            #
            #     self.print_plan_action = QAction("Print plan info")
            #     self.print_plan_action.triggered.connect(plan.print_plan_stat)
            #     self.context_menu.addAction(self.print_plan_action)

            self.delete_action = QAction("Delete")
            self.delete_action.triggered.connect(lambda checked : openDeleteDataDialog(self, selectedData, self._currentPatient))
            self.context_menu.addAction(self.delete_action)

            self.export_action = QAction("Export serialized")
            self.export_action.triggered.connect(
                lambda checked, selectedData=selectedData: self.exportSerializedData(selectedData))
            self.context_menu.addAction(self.export_action)

            self.context_menu.popup(pos)


    def _showImageInfo(self, image):
        w = QMainWindow(self)
        w.setWindowTitle('Image info')
        w.resize(400, 400)
        w.setCentralWidget(ImageProperties(image, self))
        w.show()

    def _setSecondaryImage(self, image):
        self._viewController.secondaryImage = image

    def createDynamic3DSequence(self, selectedImages):
        newName, okPressed = QInputDialog.getText(self, "Set series name", "Series name:", QLineEdit.Normal, "4DCT")

        if (okPressed):
            API.createDynamic3DSequence(selectedImages, newName)

    def computeDynamic3DModel(self, selected3DSequence):
        newName, okPressed = QInputDialog.getText(self, "Set dynamic 3D model name", "3D model name:", QLineEdit.Normal, "MidP")

        print(type(selected3DSequence))
        if (okPressed):
            newMod = Dynamic3DModel()
            newMod.name = newName
            newMod.seriesInstanceUID = generate_uid()
            newMod.computeMidPositionImage(selected3DSequence)
            self._viewController.currentPatient.appendDyn3DMod(newMod)

            # Should not be necessary because data tree listens to imageAdded/imageRemoved, etc.
            self.buildDataTree(self._viewController.currentPatient)

    def exportSerializedData(self, selectedData):

        print('Export data as serialized objects')
        print(type(selectedData))
        print(type(selectedData[0]))

        fileDialog = SaveData_dialog()
        savingPath, compressedBool, splitPatientsBool = fileDialog.getSaveFileName(None, dir=self.patientDataPanel.dataPath)

        # item = selectedData[0]
        # print(item.__class__)

        # testItem = item.dumpableCopy()
        dataList = [data.dumpableCopy() for data in selectedData]

        # max_bytes = 2 ** 31 - 1
        # bytes_out = pickle.dumps(testItem)
        # with open(savingPath + ".p", 'wb') as f_out:
        #     for idx in range(0, len(bytes_out), max_bytes):
        #         f_out.write(bytes_out[idx:idx + max_bytes])

        saveSerializedObject(dataList, savingPath, compressedBool=compressedBool)


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

    def __del__(self):
        self.data.nameChangedSignal.disconnect(self.setName)

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

def openRenameDataDialog(widget, data):
    text, ok = QInputDialog.getText(widget, 'Rename data', 'New name:')
    if ok:
        data.name = str(text)

def openDeleteDataDialog(widget, data, patient):
    msgBox = QMessageBox()
    msgBox.setIcon(QMessageBox.Information)
    msgBox.setText("Delete data")
    msgBox.setWindowTitle("Delete selected data?")
    msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

    if msgBox.exec() == QMessageBox.Ok:
        patient.removePatientData(data)